"""Read-only PDF diagnostics powered by QPDF through pikepdf.

The analyzer inspects only the PDF representation. It never rewrites the input,
and reports unavailable measurements as Unknown instead of treating them as a
successful check.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
import math
from pathlib import Path
from typing import Any

import pikepdf
from ppview.core.document import DocumentError, inspect_file, validate_rendering


class Status(str, Enum):
    PASSED = "passed"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PreflightSettings:
    target_image_ppi: int = 300
    minimum_bleed_mm: float = 3.0

    def __post_init__(self):
        if self.target_image_ppi not in (150, 200, 300):
            raise ValueError("target_image_ppi must be 150, 200, or 300")
        if self.minimum_bleed_mm not in (0, 2, 3, 5):
            raise ValueError("minimum_bleed_mm must be 0, 2, 3, or 5")


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    category: str
    status: Status
    message_id: str
    details: dict[str, Any] = field(default_factory=dict)
    page: int | None = None
    object_ref: str | None = None
    bounding_box_pt: tuple[float, float, float, float] | None = None
    measurements: dict[str, float | int | str] = field(default_factory=dict)
    severity: str = "info"


@dataclass(frozen=True)
class PreflightReport:
    results: tuple[CheckResult, ...]
    page_count: int | None
    image_count: int | None
    font_count: int | None
    image_placement_count: int | None = None


_MAX_IMAGE_PIXELS = 8_000_000
_MAX_IMAGE_STREAM_BYTES = 64 * 1024 * 1024
_MAX_DECODED_IMAGE_BYTES = 64 * 1024 * 1024


def _obj_ref(obj: Any) -> str | None:
    try:
        number, generation = obj.objgen
    except (AttributeError, TypeError, ValueError):
        return None
    return f"{number} {generation} R" if number else None


def _inherited(page_obj, key: str):
    node = page_obj
    seen = set()
    while node is not None:
        identity = _obj_ref(node) or id(node)
        if identity in seen:
            break
        seen.add(identity)
        if key in node:
            return node[key]
        node = node.get("/Parent")
    return None


def _numbers(value) -> tuple[float, ...] | None:
    try:
        values = tuple(float(item) for item in value)
        if len(values) != 4 or not all(math.isfinite(item) for item in values):
            return None
        x0, y0, x1, y1 = values
        if x1 <= x0 or y1 <= y0:
            return None
        return values
    except (TypeError, ValueError, OverflowError):
        return None


def _space_name(value, resources) -> str:
    """Return a conservative normalized name for a PDF color-space object."""
    try:
        name = str(value)
        if not name.startswith("/"):
            return "unknown"
        color_spaces = resources.get("/ColorSpace", {})
        if name not in ("/DeviceGray", "/G", "/DeviceRGB", "/RGB", "/DeviceCMYK", "/CMYK"):
            value = color_spaces.get(name, value)
            if isinstance(value, pikepdf.Array) and len(value):
                family = str(value[0])
                if family == "/ICCBased":
                    return "ICCBased"
                if family in ("/CalGray", "/CalRGB", "/Lab"):
                    return family.lstrip("/")
                if family == "/Indexed":
                    return "Indexed"
                if family == "/Separation":
                    return "Separation"
                if family == "/DeviceN":
                    return "DeviceN"
                return family.lstrip("/")
            name = str(value)
        aliases = {"/G": "DeviceGray", "/RGB": "DeviceRGB", "/CMYK": "DeviceCMYK"}
        return aliases.get(name, name.lstrip("/"))
    except Exception:
        return "unknown"


def _font_embedding(font) -> tuple[str, str, Status]:
    subtype = str(font.get("/Subtype", "/Unknown")).lstrip("/")
    name = str(font.get("/BaseFont", font.get("/Name", "/Unknown"))).lstrip("/")
    if "+" in name and len(name.split("+", 1)[0]) == 6:
        name = name.split("+", 1)[1]
    if subtype == "Type3":
        return name, subtype, Status.UNKNOWN
    candidates = [font]
    try:
        descendants = list(font.get("/DescendantFonts", []))
        if subtype == "Type0" and not descendants:
            return name, subtype, Status.UNKNOWN
        candidates.extend(descendants)
    except Exception:
        if subtype == "Type0":
            return name, subtype, Status.UNKNOWN
    found_descriptor = False
    for candidate in candidates:
        descriptor = candidate.get("/FontDescriptor")
        if descriptor:
            found_descriptor = True
            if any(key in descriptor for key in ("/FontFile", "/FontFile2", "/FontFile3")):
                return name, subtype, Status.PASSED
    if found_descriptor:
        return name, subtype, Status.WARNING
    standard_14 = {"Times-Roman", "Times-Bold", "Times-Italic", "Times-BoldItalic",
                   "Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Helvetica-BoldOblique",
                   "Courier", "Courier-Bold", "Courier-Oblique", "Courier-BoldOblique",
                   "Symbol", "ZapfDingbats"}
    if name in standard_14:
        return name, subtype, Status.WARNING
    return name, subtype, Status.UNKNOWN


def _compose(left, right):
    """Compose PDF affine transforms in [a,b,c,d,e,f] representation."""
    a, b, c, d, e, f = left
    g, h, i, j, k, ell = right
    return (a*g + c*h, b*g + d*h, a*i + c*j, b*i + d*j,
            a*k + c*ell + e, b*k + d*ell + f)


def _transformed_bounds(matrix):
    a, b, c, d, e, f = matrix
    points = ((e, f), (a + e, b + f), (c + e, d + f), (a + c + e, b + d + f))
    xs, ys = zip(*points)
    bounds = (min(xs), min(ys), max(xs), max(ys))
    return bounds if all(math.isfinite(v) for v in bounds) else None


def _preview_bounds(matrix, crop, user_unit, rotation):
    """Normalize the placed image bounds to the rotated CropBox view.

    Bounds are approximate placement bounds: PDF clipping paths are not
    resolved. The returned tuple is (left, top, right, bottom), each 0..1.
    """
    if not crop or user_unit <= 0 or rotation not in (0, 90, 180, 270):
        return None
    bounds = _transformed_bounds(matrix)
    if not bounds:
        return None
    x0, y0, x1, y1 = (value * user_unit for value in crop)
    bx0, by0, bx1, by1 = (value * user_unit for value in bounds)
    corners = ((bx0, by0), (bx0, by1), (bx1, by0), (bx1, by1))
    if rotation == 0:
        points = [(x - x0, y1 - y) for x, y in corners]
        width, height = x1 - x0, y1 - y0
    elif rotation == 90:
        points = [(y - y0, x - x0) for x, y in corners]
        width, height = y1 - y0, x1 - x0
    elif rotation == 180:
        points = [(x1 - x, y - y0) for x, y in corners]
        width, height = x1 - x0, y1 - y0
    else:
        points = [(y1 - y, x1 - x) for x, y in corners]
        width, height = y1 - y0, x1 - x0
    if width <= 0 or height <= 0:
        return None
    left = min(x for x, _ in points) / width
    top = min(y for _, y in points) / height
    right = max(x for x, _ in points) / width
    bottom = max(y for _, y in points) / height
    if not all(math.isfinite(value) for value in (left, top, right, bottom)):
        return None
    if right <= left or bottom <= top:
        return None
    return left, top, right, bottom


def _image_stream_state(stream, width, height, bits, color, *, external=False):
    """Inspect stream availability and decoding without retaining image data."""
    try:
        declared_length = int(stream.get("/Length", 0) or 0)
    except Exception:
        declared_length = 0
    if declared_length > _MAX_IMAGE_STREAM_BYTES:
        return "unknown", "skipped", None, None
    try:
        raw = stream.read_raw_bytes()
    except Exception as exc:
        return "inaccessible", "not_checked", None, type(exc).__name__
    raw_length = len(raw)
    del raw
    if raw_length > _MAX_IMAGE_STREAM_BYTES:
        return "unknown", "skipped", raw_length, None
    if raw_length <= 0:
        return "unavailable", "not_checked", 0, None
    # An external-file reference is tracked independently. The bytes in this
    # PDF stream may still be present, but decoding through the PDF library
    # does not verify the external dependency itself.
    if external:
        return "available", "not_checked", raw_length, None

    components = {"DeviceGray": 1, "CalGray": 1, "DeviceRGB": 3,
                  "CalRGB": 3, "DeviceCMYK": 4, "ICCBased": 4}.get(color, 4)
    decoded_estimate = (width * height * components * bits + 7) // 8
    if (width <= 0 or height <= 0 or bits <= 0 or width * height > _MAX_IMAGE_PIXELS
            or decoded_estimate > _MAX_DECODED_IMAGE_BYTES):
        return "available", "skipped", raw_length, None
    try:
        decoded = stream.read_bytes()
        del decoded
        return "available", "decoded", raw_length, None
    except Exception as exc:
        return "available", "failed", raw_length, type(exc).__name__


def analyze_pdf(path: str | Path, settings: PreflightSettings = PreflightSettings()) -> PreflightReport:
    """Inspect accessible PDF structures and return language-neutral findings."""
    path = Path(path)
    results: list[CheckResult] = []
    image_count = font_count = None
    page_count = None

    def add(check_id, category, status, message_id, *, page=None, obj=None, box=None,
            measurements=None, details=None, severity="info"):
        results.append(CheckResult(check_id, category, Status(status), message_id,
                                   details or {}, page, _obj_ref(obj) if obj is not None else None,
                                   box, measurements or {}, severity))

    try:
        pdf = pikepdf.open(str(path), attempt_recovery=True)
    except Exception as exc:
        add("document.open", "document", Status.ERROR, "document.unreadable",
            details={"error_type": type(exc).__name__}, severity="error")
        for category, key in (("images", "images.unavailable"), ("fonts", "fonts.unavailable"),
                              ("geometry", "geometry.unavailable"), ("colors", "colors.unavailable")):
            add(f"{category}.inspection", category, Status.UNKNOWN, key)
        return PreflightReport(tuple(results), None, None, None)

    add("document.open", "document", Status.PASSED, "document.readable")
    image_index = font_index = 0
    unique_image_keys: set[str] = set()
    image_reuse_counts: dict[str, int] = {}
    image_stream_cache: dict[str, tuple[str, str, int | None, str | None]] = {}
    document_font_refs: set[str] = set()
    try:
        page_count = len(pdf.pages)
        if page_count < 1:
            add("document.pages", "document", Status.ERROR, "document.no_pages", severity="error")
            return PreflightReport(tuple(results), page_count, 0, 0, 0)
        add("document.pages", "document", Status.PASSED, "document.page_count",
            measurements={"count": page_count})

        for page_number, page in enumerate(pdf.pages, 1):
            page_obj = page.obj
            user_unit = 1.0
            unit_valid = True
            try:
                user_unit = float(_inherited(page_obj, "/UserUnit") or 1)
                if not math.isfinite(user_unit) or user_unit <= 0:
                    raise ValueError("invalid UserUnit")
            except Exception:
                unit_valid = False
                user_unit = 1.0
                add(f"geometry.user_unit.{page_number}", "geometry", Status.UNKNOWN,
                    "geometry.user_unit_unknown", page=page_number)
            try:
                rotation = int(_inherited(page_obj, "/Rotate") or 0) % 360
                rotation_valid = rotation in (0, 90, 180, 270)
            except (TypeError, ValueError, OverflowError):
                rotation_valid = False
                rotation = 0
                add(f"geometry.rotation.{page_number}", "geometry", Status.UNKNOWN,
                    "geometry.rotation_unknown", page=page_number)
            media = _numbers(_inherited(page_obj, "/MediaBox"))
            crop_value = _inherited(page_obj, "/CropBox")
            crop = _numbers(crop_value) if crop_value is not None else media
            if crop and media:
                crop = (max(crop[0], media[0]), max(crop[1], media[1]),
                        min(crop[2], media[2]), min(crop[3], media[3]))
                if crop[2] <= crop[0] or crop[3] <= crop[1]:
                    crop = None
            trim_explicit = "/TrimBox" in page_obj
            bleed_explicit = "/BleedBox" in page_obj
            trim = _numbers(page_obj.get("/TrimBox")) if trim_explicit else None
            bleed = _numbers(page_obj.get("/BleedBox")) if bleed_explicit else None
            art_value = page_obj.get("/ArtBox")
            art = _numbers(art_value) if art_value is not None else crop
            if not media or not crop:
                add(f"geometry.boxes.{page_number}", "geometry", Status.ERROR,
                    "geometry.invalid_page_box", page=page_number, obj=page_obj,
                    severity="error")
            else:
                width_pt = (media[2] - media[0]) * user_unit
                height_pt = (media[3] - media[1]) * user_unit
                crop_width_pt = (crop[2] - crop[0]) * user_unit
                crop_height_pt = (crop[3] - crop[1]) * user_unit
                if rotation in (90, 270):
                    width_pt, height_pt = height_pt, width_pt
                    crop_width_pt, crop_height_pt = crop_height_pt, crop_width_pt
                geometry_status = Status.PASSED if unit_valid and rotation_valid else Status.UNKNOWN
                measurements = {"rotation": rotation, "user_unit": user_unit}
                if geometry_status is Status.PASSED:
                    measurements.update({"media_width_mm": width_pt * 25.4 / 72,
                                         "media_height_mm": height_pt * 25.4 / 72,
                                         "crop_width_mm": crop_width_pt * 25.4 / 72,
                                         "crop_height_mm": crop_height_pt * 25.4 / 72})
                    for label, box in (("media", media), ("crop", crop), ("trim", trim),
                                       ("bleed", bleed), ("art", art)):
                        if box:
                            scaled_box = tuple(value * user_unit for value in box)
                            measurements[f"{label}_x0_pt"], measurements[f"{label}_y0_pt"], measurements[f"{label}_x1_pt"], measurements[f"{label}_y1_pt"] = scaled_box
                            box_width_pt = (box[2] - box[0]) * user_unit
                            box_height_pt = (box[3] - box[1]) * user_unit
                            if rotation in (90, 270):
                                box_width_pt, box_height_pt = box_height_pt, box_width_pt
                            measurements[f"{label}_width_mm"] = box_width_pt * 25.4 / 72
                            measurements[f"{label}_height_mm"] = box_height_pt * 25.4 / 72
                geometry_message = "geometry.page_boxes" if geometry_status is Status.PASSED else (
                    "geometry.user_unit_unknown" if not unit_valid else "geometry.rotation_unknown")
                add(f"geometry.boxes.{page_number}", "geometry", geometry_status,
                    geometry_message, page=page_number, obj=page_obj,
                    box=media if geometry_status is Status.PASSED else None,
                    measurements=measurements,
                    details={"trim_explicit": trim_explicit, "bleed_explicit": bleed_explicit,
                             "crop_uses_media_default": crop_value is None})
            if trim_explicit and bleed_explicit and trim and bleed and unit_valid and rotation_valid:
                x_min, y_min = trim[0] - bleed[0], trim[1] - bleed[1]
                x_max, y_max = bleed[2] - trim[2], bleed[3] - trim[3]
                margins = {0: (x_min, y_min, x_max, y_max),
                           90: (y_min, x_max, y_max, x_min),
                           180: (x_max, y_max, x_min, y_min),
                           270: (y_max, x_min, y_min, x_max)}.get(rotation % 360,
                                                                  (x_min, y_min, x_max, y_max))
                if all(m >= -0.01 for m in margins):
                    margins_mm = tuple(max(0.0, m) * user_unit * 25.4 / 72 for m in margins)
                    minimum = min(margins_mm)
                    status = Status.PASSED if minimum + 0.01 >= settings.minimum_bleed_mm else Status.WARNING
                    message = "geometry.bleed_meets" if status is Status.PASSED else "geometry.bleed_below"
                    add(f"geometry.bleed.{page_number}", "geometry", status, message,
                        page=page_number, obj=page_obj,
                        measurements={"left_mm": margins_mm[0], "bottom_mm": margins_mm[1],
                                      "right_mm": margins_mm[2], "top_mm": margins_mm[3],
                                      "minimum_mm": minimum, "target_mm": settings.minimum_bleed_mm})
                else:
                    add(f"geometry.bleed.{page_number}", "geometry", Status.UNKNOWN,
                        "geometry.bleed_ambiguous", page=page_number, obj=page_obj)
            elif trim_explicit and bleed_explicit:
                add(f"geometry.bleed.{page_number}", "geometry", Status.UNKNOWN,
                    "geometry.bleed_ambiguous", page=page_number, obj=page_obj)
            else:
                add(f"geometry.bleed.{page_number}", "geometry", Status.UNKNOWN,
                    "geometry.bleed_boxes_missing", page=page_number,
                    details={"trim_explicit": trim_explicit, "bleed_explicit": bleed_explicit})

            # Walk actual Do placements, including nested Form XObjects. Image
            # resolution is based on transformed unit-square dimensions.
            page_images = 0
            page_fonts: dict[str, tuple[Any, str, str, Status]] = {}
            page_colors: set[str] = set()
            content_error = None

            def inspect_image(stream, image_dict, width, height, bits, color, matrix,
                              *, image_obj=None, inline=False):
                nonlocal page_images, image_index
                page_images += 1
                image_index += 1
                placement_index = image_index
                object_ref = _obj_ref(image_obj) if image_obj is not None else None
                identity = object_ref or f"inline:{page_number}:{placement_index}"
                unique_image_keys.add(identity)
                image_reuse_counts[identity] = image_reuse_counts.get(identity, 0) + 1
                external = not inline and any(key in image_dict for key in ("/F", "/FFilter"))
                if identity not in image_stream_cache:
                    image_stream_cache[identity] = _image_stream_state(
                        stream, width, height, bits, color, external=external)
                data_state, decode_state, stream_length, decode_error = image_stream_cache[identity]

                a, b, c, d, _e, _f = matrix
                scale_x = math.hypot(a, b) * user_unit
                scale_y = math.hypot(c, d) * user_unit
                placement_width_mm = scale_x * 25.4 / 72 if math.isfinite(scale_x) else None
                placement_height_mm = scale_y * 25.4 / 72 if math.isfinite(scale_y) else None
                ppi_x = width * 72 / scale_x if unit_valid and width > 0 and scale_x > 1e-9 else None
                ppi_y = height * 72 / scale_y if unit_valid and height > 0 and scale_y > 1e-9 else None
                effective_ppi = None
                if unit_valid and width > 0 and height > 0:
                    # The largest singular scale is conservative under shear.
                    u = (a * user_unit / width, b * user_unit / width)
                    v = (c * user_unit / height, d * user_unit / height)
                    g11 = u[0] * u[0] + u[1] * u[1]
                    g22 = v[0] * v[0] + v[1] * v[1]
                    g12 = u[0] * v[0] + u[1] * v[1]
                    largest = math.sqrt(max(0.0, (g11 + g22
                                                    + math.sqrt((g11-g22)**2 + 4*g12*g12)) / 2))
                    if largest > 1e-9:
                        effective_ppi = 72 / largest

                box = _transformed_bounds(matrix)
                if box and unit_valid:
                    box = tuple(value * user_unit for value in box)
                elif not unit_valid:
                    box = None
                preview_box = _preview_bounds(matrix, crop, user_unit, rotation) if rotation_valid else None
                measurements = {
                    "placement_index": placement_index, "width_px": width, "height_px": height,
                    "bits_per_component": bits, "color_space": color,
                    "ppi_x": ppi_x, "ppi_y": ppi_y, "effective_ppi": effective_ppi,
                    "placement_width_mm": placement_width_mm,
                    "placement_height_mm": placement_height_mm,
                    "target_ppi": settings.target_image_ppi,
                }
                if stream_length is not None:
                    measurements["stream_bytes"] = stream_length
                if effective_ppi is not None and math.isfinite(effective_ppi):
                    if effective_ppi >= settings.target_image_ppi:
                        resolution_status, resolution_message, severity = (
                            Status.PASSED, "image.resolution_meets", "info")
                    elif effective_ppi < 150:
                        resolution_status, resolution_message, severity = (
                            Status.WARNING, "image.resolution_low", "high")
                    else:
                        resolution_status, resolution_message, severity = (
                            Status.WARNING, "image.resolution_below_target", "warning")
                else:
                    resolution_status, resolution_message, severity = (
                        Status.UNKNOWN, "image.resolution_unknown", "unknown")

                parent_id = f"image.placement.{page_number}.{placement_index}"
                details = {
                    "_image_identity": identity, "placement_index": placement_index,
                    "image_kind": "inline" if inline else "xobject",
                    "pdf_presence": "present", "data_availability": data_state,
                    "decode_status": decode_state, "external_reference": external,
                    "reuse_status": "pending", "reuse_count": 0,
                    "preview_box": preview_box,
                    "preview_quality": "approximate" if preview_box else "unavailable",
                    "visible_boundary_verified": False,
                    "native_illustrator_incorporation": (
                        "unverified" if path.suffix.lower() == ".ai" else "not_applicable"),
                    "decode_error_type": decode_error,
                    "placement_clipping_analyzed": False,
                }
                add(parent_id, "images", resolution_status, resolution_message,
                    page=page_number, obj=image_obj, box=box, measurements=measurements,
                    details=details, severity=severity)
                linked_details = {
                    "parent_id": parent_id, "preview_box": preview_box,
                    "preview_quality": "approximate" if preview_box else "unavailable",
                }
                add(f"image.presence.{page_number}.{placement_index}", "images",
                    Status.PASSED, "image.present", page=page_number, obj=image_obj,
                    measurements={"placement_index": placement_index},
                    details=linked_details)
                data_status, data_message = {
                    "available": (Status.PASSED, "image.data_available"),
                    "external": (Status.WARNING, "image.external_dependency"),
                    "unknown": (Status.UNKNOWN, "image.data_unknown"),
                    "unavailable": (Status.UNKNOWN, "image.data_unavailable"),
                    "inaccessible": (Status.UNKNOWN, "image.data_inaccessible"),
                }[data_state]
                add(f"image.data.{page_number}.{placement_index}", "images",
                    data_status, data_message, page=page_number, obj=image_obj,
                    measurements={"placement_index": placement_index},
                    details=linked_details | {"data_availability": data_state,
                             "external_reference": external})
                if external:
                    add(f"image.external.{page_number}.{placement_index}", "images",
                        Status.WARNING, "image.external_dependency", page=page_number,
                        obj=image_obj, measurements={"placement_index": placement_index},
                        details=linked_details | {"external_reference": True}, severity="warning")
                decode_status, decode_message = {
                    "decoded": (Status.PASSED, "image.decode_success"),
                    "failed": (Status.WARNING, "image.decode_failed"),
                    "skipped": (Status.UNKNOWN, "image.decode_skipped_large"),
                    "not_checked": (Status.UNKNOWN, "image.decode_not_checked"),
                }[decode_state]
                add(f"image.decode.{page_number}.{placement_index}", "images",
                    decode_status, decode_message, page=page_number, obj=image_obj,
                    measurements={"placement_index": placement_index},
                    details=linked_details | {"decode_status": decode_state,
                             "error_type": decode_error})
                if preview_box is None:
                    add(f"image.geometry.{page_number}.{placement_index}", "images",
                        Status.UNKNOWN, "image.geometry_unknown", page=page_number,
                        obj=image_obj, box=box,
                        measurements={"placement_index": placement_index},
                        details=linked_details, severity="unknown")

            def add_fonts(resources):
                fonts = resources.get("/Font", {})
                try:
                    for font in fonts.values():
                        ref = _obj_ref(font)
                        key = ref or f"direct:{str(font.get('/BaseFont', 'unknown'))}"
                        if key in page_fonts:
                            continue
                        name, subtype, embedding_status = _font_embedding(font)
                        page_fonts[key] = (font, name, subtype, embedding_status)
                except Exception:
                    pass

            def walk(content, resources, matrix=(1, 0, 0, 1, 0, 0), depth=0, form_stack=()):
                nonlocal page_images, image_index, content_error
                if depth > 16:
                    raise ValueError("form nesting limit exceeded")
                add_fonts(resources)
                local_matrix = matrix
                stack = []
                for instruction in pikepdf.parse_content_stream(content):
                    op = str(instruction.operator)
                    operands = list(instruction.operands)
                    if op == "q":
                        stack.append(local_matrix)
                    elif op == "Q":
                        if stack:
                            local_matrix = stack.pop()
                    elif op == "cm" and len(operands) == 6:
                        vals = tuple(float(v) for v in operands)
                        local_matrix = _compose(local_matrix, vals)
                    elif op in ("g", "G"):
                        page_colors.add("DeviceGray")
                    elif op in ("rg", "RG"):
                        page_colors.add("DeviceRGB")
                    elif op in ("k", "K"):
                        page_colors.add("DeviceCMYK")
                    elif op in ("cs", "CS") and operands:
                        page_colors.add(_space_name(operands[0], resources))
                    elif op == "sh" and operands:
                        shading = resources.get("/Shading", {}).get(str(operands[0]))
                        if shading is not None:
                            page_colors.add(_space_name(shading.get("/ColorSpace", "unknown"), resources))
                    elif op == "Do" and operands:
                        xobjects = resources.get("/XObject", {})
                        xobj = xobjects.get(str(operands[0]))
                        if xobj is None:
                            continue
                        subtype = str(xobj.get("/Subtype", ""))
                        ref = _obj_ref(xobj)
                        if subtype == "/Form":
                            identity = ref or str(id(xobj))
                            if identity in form_stack:
                                continue
                            form_matrix = tuple(float(v) for v in xobj.get("/Matrix", (1, 0, 0, 1, 0, 0)))
                            child_resources = xobj.get("/Resources", resources)
                            walk(xobj, child_resources, _compose(local_matrix, form_matrix),
                                 depth + 1, form_stack + (identity,))
                        elif subtype == "/Image":
                            width = int(xobj.get("/Width", 0) or 0)
                            height = int(xobj.get("/Height", 0) or 0)
                            color = _space_name(xobj.get("/ColorSpace", "unknown"), resources)
                            page_colors.add(color)
                            bits = int(xobj.get("/BitsPerComponent", 0) or 0)
                            inspect_image(xobj, xobj, width, height, bits, color, local_matrix,
                                          image_obj=xobj)
                    elif op == "INLINE IMAGE":
                        inline = instruction.iimage
                        image_obj = inline.obj
                        width, height = int(inline.width), int(inline.height)
                        bits = int(inline.bits_per_component or 0)
                        color = _space_name(image_obj.get("/ColorSpace", "unknown"), resources)
                        page_colors.add(color)
                        inspect_image(inline, image_obj, width, height, bits, color, local_matrix,
                                      inline=True)

            try:
                walk(page, page.resources)
                add(f"document.content.{page_number}", "document", Status.PASSED,
                    "document.content_readable", page=page_number, obj=page_obj)
            except Exception as exc:
                content_error = exc
                add(f"document.content.{page_number}", "document", Status.ERROR,
                    "document.content_unreadable", page=page_number, obj=page_obj,
                    details={"error_type": type(exc).__name__}, severity="error")
                for category in ("images", "fonts", "colors"):
                    add(f"{category}.scan_incomplete.{page_number}", category, Status.UNKNOWN,
                        f"{category}.scan_incomplete", page=page_number, obj=page_obj,
                        severity="unknown")

            if page_images == 0 and content_error is None:
                add(f"images.none.{page_number}", "images", Status.PASSED,
                    "images.none_detected", page=page_number)
            for font_key, (font, name, subtype, embedding_status) in page_fonts.items():
                font_index += 1
                document_font_refs.add(font_key)
                status = embedding_status
                message = ("fonts.type3_unknown" if subtype == "Type3" else
                           {Status.PASSED: "fonts.embedded", Status.WARNING: "fonts.not_embedded",
                            Status.UNKNOWN: "fonts.embedding_unknown"}[status])
                add(f"font.embedding.{page_number}.{font_index}", "fonts", status, message,
                    page=page_number, obj=font, measurements={"name": name, "subtype": subtype},
                    details={"resource_key": font_key},
                    severity="warning" if status is Status.WARNING else "unknown" if status is Status.UNKNOWN else "info")
            if not page_fonts and content_error is None:
                add(f"fonts.none.{page_number}", "fonts", Status.PASSED,
                    "fonts.none_detected", page=page_number)
            if not page_colors and content_error is None:
                add(f"colors.none.{page_number}", "colors", Status.UNKNOWN,
                    "colors.none_detected", page=page_number, severity="unknown")
            else:
                for color in sorted(page_colors):
                    if color in ("DeviceGray", "DeviceRGB", "DeviceCMYK", "ICCBased"):
                        status = Status.PASSED
                    else:
                        status = Status.UNKNOWN
                    add(f"colors.space.{page_number}.{color}", "colors", status,
                        "colors.detected" if status is Status.PASSED else "colors.unsupported",
                        page=page_number, measurements={"color_space": color},
                        severity="info" if status is Status.PASSED else "unknown")
    finally:
        pdf.close()

    if path.suffix.lower() == ".ai":
        add("image.ai_native_unverified", "images", Status.UNKNOWN,
            "image.ai_native_unverified",
            details={"native_illustrator_incorporation": "unverified"})

    finalized = []
    for result in results:
        identity = result.details.get("_image_identity")
        if identity is not None:
            details = dict(result.details)
            details.pop("_image_identity", None)
            reuse_count = image_reuse_counts.get(identity, 1)
            details["reuse_count"] = reuse_count
            details["reuse_status"] = "reused" if reuse_count > 1 else "single"
            result = replace(result, details=details)
        finalized.append(result)
    return PreflightReport(tuple(finalized), page_count, len(unique_image_keys),
                           len(document_font_refs), image_index)


def run_preflight(path: str | Path, settings: PreflightSettings = PreflightSettings()) -> PreflightReport:
    """Run structural checks and the existing read-only PDFium render check."""
    report = analyze_pdf(path, settings)
    try:
        render_info = inspect_file(path)
        validate_rendering(path, len(render_info.pages))
        rendering = CheckResult("document.render", "document", Status.PASSED,
                                "document.render_success")
    except DocumentError as exc:
        rendering = CheckResult("document.render", "document", Status.ERROR,
                                "document.render_failed", {"reason": str(exc)}, severity="error")
    except Exception as exc:
        rendering = CheckResult("document.render", "document", Status.ERROR,
                                "document.render_failed", {"error_type": type(exc).__name__},
                                severity="error")
    return PreflightReport((rendering, *report.results), report.page_count,
                           report.image_count, report.font_count, report.image_placement_count)


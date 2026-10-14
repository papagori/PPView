import pytest

from preflight_fixtures import create_pdf, make_bad_image_pdf, make_inline_image_pdf
from ppview.validation import CheckResult, PreflightSettings, Status, analyze_pdf, run_preflight


def finding(report, message_id):
    return next(result for result in report.results if result.message_id == message_id)


def test_scaled_and_rotated_image_resolution_uses_placement_matrix(tmp_path):
    normal = create_pdf(tmp_path / "normal.pdf", image_placements=[(144, 0, 0, 144, 20, 30)])
    rotated = create_pdf(tmp_path / "rotated.pdf", rotate=90,
                         image_placements=[(0, 144, -144, 0, 200, 30)])
    normal_image = next(r for r in analyze_pdf(normal).results if r.category == "images")
    rotated_image = next(r for r in analyze_pdf(rotated).results if r.category == "images")
    assert normal_image.measurements["effective_ppi"] == pytest.approx(300)
    assert rotated_image.measurements["effective_ppi"] == pytest.approx(300)
    assert rotated_image.bounding_box_pt == pytest.approx((56, 30, 200, 174))


def test_scaled_image_resolution_thresholds_are_configurable(tmp_path):
    path = create_pdf(tmp_path / "scaled.pdf", image_placements=[(216, 0, 0, 216, 0, 0)])
    result = next(r for r in analyze_pdf(path).results if r.category == "images")
    assert result.measurements["effective_ppi"] == pytest.approx(200)
    assert result.status is Status.WARNING
    relaxed = next(r for r in analyze_pdf(path, PreflightSettings(150, 3)).results if r.category == "images")
    assert relaxed.status is Status.PASSED
    low = create_pdf(tmp_path / "low.pdf", image_placements=[(432, 0, 0, 432, 0, 0)])
    assert next(r for r in analyze_pdf(low).results if r.category == "images").severity == "high"


def test_reused_image_resource_has_each_placement_and_form_placements_are_walked(tmp_path):
    reused = create_pdf(tmp_path / "reused.pdf", image_placements=[
        (144, 0, 0, 144, 0, 0), (216, 0, 0, 216, 200, 300)])
    report = analyze_pdf(reused)
    placements = [r for r in report.results if r.category == "images" and r.check_id.startswith("image.resolution")]
    assert report.image_count == 2
    assert [r.measurements["effective_ppi"] for r in placements] == pytest.approx([300, 200])
    assert all(r.object_ref for r in placements)
    form = create_pdf(tmp_path / "form.pdf", form_image=True,
                      image_placements=[(144, 0, 0, 144, 20, 30)])
    form_report = analyze_pdf(form)
    form_image = next(r for r in form_report.results if r.category == "images")
    assert form_image.measurements["effective_ppi"] == pytest.approx(300)
    assert form_image.page == 1


def test_image_free_and_vector_documents_are_not_defects(tmp_path):
    path = create_pdf(tmp_path / "vector.pdf", color_ops="0 0 1 rg 0 0 20 20 re f")
    report = analyze_pdf(path)
    assert report.image_count == 0
    assert finding(report, "images.none_detected").status is Status.PASSED
    assert finding(report, "fonts.none_detected").status is Status.PASSED
    assert finding(report, "colors.detected").measurements["color_space"] == "DeviceRGB"


def test_bad_image_stream_is_not_reported_as_passed(tmp_path):
    report = analyze_pdf(make_bad_image_pdf(tmp_path / "bad-image.pdf"))
    assert finding(report, "image.decode_failed").status is Status.UNKNOWN
    resolution = next(r for r in report.results if r.check_id.startswith("image.resolution"))
    assert resolution.status is Status.WARNING


def test_inline_image_reports_effective_ppi_but_decode_as_unknown(tmp_path):
    report = analyze_pdf(make_inline_image_pdf(tmp_path / "inline.pdf"))
    resolution = next(r for r in report.results if r.check_id.startswith("image.resolution"))
    assert resolution.measurements["effective_ppi"] == pytest.approx(300)
    assert resolution.status is Status.PASSED
    assert finding(report, "image.inline_decode_unknown").status is Status.UNKNOWN


def test_font_embedding_and_japanese_cid_resources(tmp_path):
    path = create_pdf(tmp_path / "fonts.pdf", font_modes=["embedded", "missing", "cid-embedded", "type3"])
    report = analyze_pdf(path)
    fonts = [r for r in report.results if r.category == "fonts" and r.message_id.startswith("fonts.")]
    by_name = {r.measurements["name"]: r for r in fonts}
    assert by_name["TestFont0"].status is Status.PASSED
    assert by_name["TestFont1"].status is Status.WARNING
    assert by_name["TestFont2"].status is Status.PASSED
    assert by_name["TestFont2"].measurements["subtype"] == "Type0"
    assert by_name["TestFont3"].status is Status.UNKNOWN
    assert by_name["TestFont3"].message_id == "fonts.type3_unknown"


def test_page_boxes_dimensions_origin_rotation_and_bleed(tmp_path):
    mm3 = 3 * 72 / 25.4
    boxes = {"TrimBox": [20, 30, 592, 762],
             "BleedBox": [20-mm3, 30-mm3, 592+mm3, 762+mm3],
             "ArtBox": [25, 35, 587, 757]}
    path = create_pdf(tmp_path / "boxes.pdf", page_boxes=boxes, rotate=90, color_ops="")
    report = analyze_pdf(path)
    geometry = finding(report, "geometry.page_boxes")
    assert geometry.measurements["media_width_mm"] == pytest.approx(279.4)
    assert geometry.measurements["media_height_mm"] == pytest.approx(215.9)
    assert geometry.measurements["media_x0_pt"] == 0
    bleed = finding(report, "geometry.bleed_meets")
    assert bleed.measurements["minimum_mm"] == pytest.approx(3)
    assert bleed.page == 1


def test_missing_bleed_metadata_is_unknown_not_error(tmp_path):
    path = create_pdf(tmp_path / "no-bleed.pdf", color_ops="")
    report = analyze_pdf(path)
    assert finding(report, "geometry.bleed_boxes_missing").status is Status.UNKNOWN
    assert all(r.status is not Status.PASSED for r in report.results if r.message_id == "geometry.bleed_boxes_missing")


@pytest.mark.parametrize("color_ops,expected", [
    ("0 0 0 rg", "DeviceRGB"), ("0 0 0 1 k", "DeviceCMYK"), ("0 g", "DeviceGray")])
def test_basic_color_spaces_are_reported_without_print_accuracy_claims(tmp_path, color_ops, expected):
    path = create_pdf(tmp_path / "color.pdf", color_ops=color_ops)
    report = analyze_pdf(path)
    assert any(r.status is Status.PASSED and r.measurements.get("color_space") == expected
               for r in report.results if r.category == "colors")


def test_malformed_pdf_keeps_unavailable_categories_unknown(tmp_path):
    path = tmp_path / "malformed.pdf"; path.write_bytes(b"%PDF-1.7\nnot a PDF structure")
    report = analyze_pdf(path)
    assert finding(report, "document.unreadable").status is Status.ERROR
    for category in ("images", "fonts", "geometry", "colors"):
        result = next(r for r in report.results if r.category == category)
        assert result.status is Status.UNKNOWN


def test_run_report_includes_pdfium_render_check(pdf_file):
    report = run_preflight(pdf_file)
    assert finding(report, "document.render_success").status is Status.PASSED


def test_preflight_settings_reject_unlisted_thresholds():
    with pytest.raises(ValueError): PreflightSettings(250, 3)
    with pytest.raises(ValueError): PreflightSettings(300, 4)

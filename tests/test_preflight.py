import pytest

from preflight_fixtures import (create_pdf, make_bad_image_pdf, make_empty_image_pdf,
                                make_external_image_pdf, make_inline_image_pdf,
                                make_large_image_pdf)
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
    placements = [r for r in report.results if r.check_id.startswith("image.placement")]
    assert report.image_count == 1
    assert report.image_placement_count == 2
    assert [r.measurements["effective_ppi"] for r in placements] == pytest.approx([300, 200])
    assert all(r.object_ref for r in placements)
    assert all(r.details["reuse_status"] == "reused" and r.details["reuse_count"] == 2
               for r in placements)
    form = create_pdf(tmp_path / "form.pdf", form_image=True,
                      image_placements=[(144, 0, 0, 144, 20, 30)])
    form_report = analyze_pdf(form)
    form_image = next(r for r in form_report.results if r.category == "images")
    assert form_image.measurements["effective_ppi"] == pytest.approx(300)
    assert form_image.page == 1


def test_nested_forms_and_shear_use_full_transformation_for_effective_ppi(tmp_path):
    nested = create_pdf(tmp_path / "nested-shear.pdf", form_image=True, form_depth=3,
                        image_placements=[(144, 0, 72, 144, 20, 30)])
    report = analyze_pdf(nested)
    placements = [r for r in report.results if r.check_id.startswith("image.placement")]
    assert report.image_count == report.image_placement_count == 1
    assert placements[0].measurements["ppi_x"] == pytest.approx(300)
    assert placements[0].measurements["ppi_y"] == pytest.approx(72 * 600 / (72**2 + 144**2) ** 0.5)
    assert 200 < placements[0].measurements["effective_ppi"] < 300
    assert placements[0].details["preview_quality"] == "approximate"
    assert placements[0].details["placement_clipping_analyzed"] is False


def test_analysis_keeps_page_specific_findings_for_mixed_page_sizes(tmp_path):
    import pikepdf

    path = create_pdf(tmp_path / "mixed-pages.pdf",
                      image_placements=[(144, 0, 0, 144, 20, 30)])
    with pikepdf.open(path, allow_overwriting_input=True) as pdf:
        pdf.add_blank_page(page_size=(300, 400))
        pdf.save(path)
    report = analyze_pdf(path)
    geometry = [r for r in report.results if r.check_id.startswith("geometry.boxes.")]
    assert report.page_count == 2
    assert [r.page for r in geometry] == [1, 2]
    assert geometry[0].measurements["media_width_mm"] != geometry[1].measurements["media_width_mm"]
    assert [r.page for r in report.results if r.check_id.startswith("image.placement.")] == [1]


def test_unresolved_do_resource_makes_image_absence_and_counts_unknown(tmp_path):
    import pikepdf

    path = create_pdf(tmp_path / "missing-xobject.pdf", color_ops="")
    with pikepdf.open(path, allow_overwriting_input=True) as pdf:
        pdf.pages[0].Contents = pdf.make_stream(b"/Missing Do")
        pdf.save(path)
    report = analyze_pdf(path)
    assert report.image_count is None
    assert report.image_placement_count is None
    assert finding(report, "images.scan_incomplete").status is Status.UNKNOWN
    assert all(r.message_id != "images.none_detected" for r in report.results)


def test_malformed_font_resource_does_not_report_no_fonts_as_passed(tmp_path):
    import pikepdf

    path = create_pdf(tmp_path / "malformed-font-resource.pdf", color_ops="")
    with pikepdf.open(path, allow_overwriting_input=True) as pdf:
        pdf.pages[0].Resources.Font = pikepdf.String("not-a-font-dictionary")
        pdf.save(path)
    report = analyze_pdf(path)
    assert report.font_count is None
    assert finding(report, "fonts.scan_incomplete").status is Status.UNKNOWN
    assert all(r.message_id != "fonts.none_detected" for r in report.results)


def test_image_free_and_vector_documents_are_not_defects(tmp_path):
    path = create_pdf(tmp_path / "vector.pdf", color_ops="0 0 1 rg 0 0 20 20 re f")
    report = analyze_pdf(path)
    assert report.image_count == 0
    assert finding(report, "images.none_detected").status is Status.PASSED
    assert finding(report, "fonts.none_detected").status is Status.PASSED
    assert finding(report, "colors.detected").measurements["color_space"] == "DeviceRGB"


def test_outlined_glyph_like_paths_do_not_require_a_pdf_font_resource(tmp_path):
    path = create_pdf(tmp_path / "outlined-text.pdf",
                      color_ops="0 g 10 10 m 10 30 l 20 30 l 20 10 h f")
    report = analyze_pdf(path)
    assert report.font_count == 0
    assert finding(report, "fonts.none_detected").status is Status.PASSED


def test_raster_placement_and_mixed_rgb_cmyk_vector_resources_coexist(tmp_path):
    path = create_pdf(tmp_path / "mixed-artwork.pdf",
                      image_placements=[(144, 0, 0, 144, 20, 30)],
                      color_ops="0 0 1 rg 10 10 30 30 re f 0 0 0 1 k 50 50 30 30 re f")
    report = analyze_pdf(path)
    assert report.image_count == report.image_placement_count == 1
    color_spaces = {r.measurements.get("color_space") for r in report.results
                    if r.category == "colors" and r.status is Status.PASSED}
    assert {"DeviceRGB", "DeviceCMYK"} <= color_spaces


def test_bad_image_stream_is_reported_as_present_but_decode_failure(tmp_path):
    report = analyze_pdf(make_bad_image_pdf(tmp_path / "bad-image.pdf"))
    assert report.image_count == report.image_placement_count == 1
    assert finding(report, "image.present").status is Status.PASSED
    assert finding(report, "image.data_available").status is Status.PASSED
    assert finding(report, "image.decode_failed").status is Status.WARNING
    resolution = next(r for r in report.results if r.check_id.startswith("image.placement"))
    assert resolution.status is Status.WARNING


def test_inline_image_reports_effective_ppi_and_decode_status(tmp_path):
    report = analyze_pdf(make_inline_image_pdf(tmp_path / "inline.pdf"))
    resolution = next(r for r in report.results if r.check_id.startswith("image.placement"))
    assert resolution.measurements["effective_ppi"] == pytest.approx(300)
    assert resolution.status is Status.PASSED
    assert resolution.details["image_kind"] == "inline"
    assert resolution.details["data_availability"] == "available"
    assert resolution.details["decode_status"] == "decoded"
    assert finding(report, "image.decode_success").status is Status.PASSED


def test_image_measurements_and_crop_rotation_preview_coordinates(tmp_path):
    boxes = {"CropBox": [50, 100, 500, 700]}
    path = create_pdf(tmp_path / "crop-rotate.pdf", page_boxes=boxes, rotate=90,
                      image_placements=[(100, 0, 0, 50, 100, 200)])
    report = analyze_pdf(path)
    image = next(r for r in report.results if r.check_id.startswith("image.placement"))
    assert image.measurements["ppi_x"] == pytest.approx(432)
    assert image.measurements["ppi_y"] == pytest.approx(864)
    assert image.measurements["placement_width_mm"] == pytest.approx(100 * 25.4 / 72)
    assert image.measurements["placement_height_mm"] == pytest.approx(50 * 25.4 / 72)
    assert image.details["preview_box"] == pytest.approx((1/6, 1/9, 1/4, 1/3))
    assert image.details["preview_quality"] == "approximate"
    assert image.details["visible_boundary_verified"] is False


def test_large_image_decode_is_skipped_and_not_marked_verified(tmp_path):
    report = analyze_pdf(make_large_image_pdf(tmp_path / "large-image.pdf"))
    image = next(r for r in report.results if r.check_id.startswith("image.placement"))
    assert image.details["data_availability"] == "available"
    assert image.details["decode_status"] == "skipped"
    assert finding(report, "image.decode_skipped_large").status is Status.UNKNOWN


def test_external_and_missing_image_data_are_not_claimed_as_internal(tmp_path):
    external = analyze_pdf(make_external_image_pdf(tmp_path / "external.pdf"))
    external_image = next(r for r in external.results if r.check_id.startswith("image.placement"))
    assert external_image.details["data_availability"] == "available"
    assert external_image.details["external_reference"] is True
    assert finding(external, "image.external_dependency").status is Status.WARNING
    assert finding(external, "image.data_available").status is Status.PASSED
    empty = analyze_pdf(make_empty_image_pdf(tmp_path / "empty-image.pdf"))
    empty_image = next(r for r in empty.results if r.check_id.startswith("image.placement"))
    assert empty_image.details["data_availability"] == "unavailable"
    assert finding(empty, "image.data_unavailable").status is Status.UNKNOWN


def test_invalid_placement_geometry_is_unknown_not_low_resolution(tmp_path):
    path = create_pdf(tmp_path / "zero-placement.pdf", image_placements=[(0, 0, 0, 0, 10, 10)])
    report = analyze_pdf(path)
    image = next(r for r in report.results if r.check_id.startswith("image.placement"))
    assert image.status is Status.UNKNOWN
    assert image.measurements["effective_ppi"] is None
    assert image.details["preview_box"] is None
    assert finding(report, "image.geometry_unknown").status is Status.UNKNOWN


def test_ai_pdf_image_does_not_claim_native_illustrator_embedding(tmp_path):
    path = create_pdf(tmp_path / "representation.ai", image_placements=[(72, 0, 0, 72, 0, 0)])
    report = analyze_pdf(path)
    image = next(r for r in report.results if r.check_id.startswith("image.placement"))
    assert image.details["native_illustrator_incorporation"] == "unverified"
    assert finding(report, "image.ai_native_unverified").status is Status.UNKNOWN


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

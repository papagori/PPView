"""Small genuine PDF structures for repeatable preflight tests."""
from __future__ import annotations

import zlib
import pikepdf


def create_pdf(path, *, image_placements=(), form_image=False, font_modes=(),
               page_boxes=None, rotate=0, color_ops="0 0 1 rg 0 0 10 10 re f"):
    pdf = pikepdf.Pdf.new()
    page = pdf.add_blank_page(page_size=(612, 792))
    if rotate:
        page.obj["/Rotate"] = rotate
    if page_boxes:
        for name, values in page_boxes.items():
            page.obj[f"/{name}"] = pikepdf.Array(values)

    resources = pikepdf.Dictionary()
    xobjects = pikepdf.Dictionary()
    commands = []
    image = None
    if image_placements:
        width = height = 600
        image = pdf.make_stream(bytes([0x35, 0x9A, 0xD4]) * width * height)
        image.Type = pikepdf.Name.XObject
        image.Subtype = pikepdf.Name.Image
        image.Width = width
        image.Height = height
        image.ColorSpace = pikepdf.Name.DeviceRGB
        image.BitsPerComponent = 8
        if form_image:
            form_resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im0=image))
            form = pdf.make_stream(b"/Im0 Do")
            form.Type = pikepdf.Name.XObject
            form.Subtype = pikepdf.Name.Form
            form.BBox = pikepdf.Array([0, 0, 1, 1])
            form.Matrix = pikepdf.Array([1, 0, 0, 1, 0, 0])
            form.Resources = form_resources
            xobjects["/Fm0"] = form
            for matrix in image_placements:
                commands.append("q " + " ".join(map(str, matrix)) + " cm /Fm0 Do Q")
        else:
            xobjects["/Im0"] = image
            for matrix in image_placements:
                commands.append("q " + " ".join(map(str, matrix)) + " cm /Im0 Do Q")

    if xobjects:
        resources.XObject = xobjects

    font_resources = pikepdf.Dictionary()
    for index, mode in enumerate(font_modes):
        base_name = pikepdf.Name(f"/ABCDEF+TestFont{index}")
        if mode == "cid-embedded":
            descriptor = pikepdf.Dictionary(Type=pikepdf.Name.FontDescriptor,
                                            FontName=base_name, Flags=4, FontBBox=[0, 0, 500, 700],
                                            ItalicAngle=0, Ascent=700, Descent=-200,
                                            CapHeight=600, StemV=80)
            descriptor.FontFile2 = pdf.make_stream(b"synthetic-tff")
            descendant = pdf.make_indirect(pikepdf.Dictionary(
                Type=pikepdf.Name.Font, Subtype=pikepdf.Name.CIDFontType2,
                BaseFont=base_name, CIDSystemInfo=pikepdf.Dictionary(Registry="Adobe", Ordering="Japan1", Supplement=7),
                FontDescriptor=descriptor, DW=1000))
            font = pdf.make_indirect(pikepdf.Dictionary(
                Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type0, BaseFont=base_name,
                Encoding=pikepdf.Name.IdentityH, DescendantFonts=[descendant]))
        elif mode == "type3":
            font = pdf.make_indirect(pikepdf.Dictionary(
                Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type3, Name=base_name,
                FontBBox=[0, 0, 500, 700], FontMatrix=[0.001, 0, 0, 0.001, 0, 0],
                CharProcs=pikepdf.Dictionary(), Encoding=pikepdf.Dictionary(
                    Type=pikepdf.Name.Encoding, Differences=[]), FirstChar=32, LastChar=32,
                Widths=[500], Resources=pikepdf.Dictionary()))
        else:
            font_dict = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1,
                                           BaseFont=base_name)
            if mode in ("embedded", "missing"):
                descriptor = pikepdf.Dictionary(Type=pikepdf.Name.FontDescriptor, FontName=base_name,
                                                Flags=4, FontBBox=[0, 0, 500, 700], ItalicAngle=0,
                                                Ascent=700, Descent=-200, CapHeight=600, StemV=80)
                if mode == "embedded":
                    descriptor.FontFile = pdf.make_stream(b"synthetic-font")
                font_dict.FontDescriptor = descriptor
            font = pdf.make_indirect(font_dict)
        font_resources[f"/F{index}"] = font
        commands.append(f"BT /F{index} 12 Tf 10 20 Td (sample) Tj ET")
    if font_resources:
        resources.Font = font_resources

    if color_ops:
        commands.insert(0, color_ops)
    page.Resources = resources
    page.Contents = pdf.make_stream("\n".join(commands).encode("ascii"))
    pdf.save(path)
    pdf.close()
    return path


def make_bad_image_pdf(path):
    pdf = pikepdf.Pdf.new()
    page = pdf.add_blank_page(page_size=(612, 792))
    image = pdf.make_stream(b"not a valid flate stream")
    image.Type = pikepdf.Name.XObject; image.Subtype = pikepdf.Name.Image
    image.Width = 2; image.Height = 2; image.ColorSpace = pikepdf.Name.DeviceRGB
    image.BitsPerComponent = 8; image.Filter = pikepdf.Name.FlateDecode
    page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im0=image))
    page.Contents = pdf.make_stream(b"2 0 0 2 0 0 cm /Im0 Do")
    pdf.save(path); pdf.close()
    return path


def make_inline_image_pdf(path):
    pdf = pikepdf.Pdf.new()
    page = pdf.add_blank_page(page_size=(612, 792))
    raw = bytes([0x35, 0x9A, 0xD4]) * 60 * 60
    page.Contents = pdf.make_stream(b"q 14.4 0 0 14.4 10 20 cm BI /W 60 /H 60 /CS /RGB /BPC 8 ID "
                                    + raw + b" EI Q")
    pdf.save(path); pdf.close()
    return path


def make_large_image_pdf(path):
    pdf = pikepdf.Pdf.new()
    page = pdf.add_blank_page(page_size=(612, 792))
    width = height = 3000
    image = pdf.make_stream(zlib.compress(bytes(width * height)))
    image.Type = pikepdf.Name.XObject; image.Subtype = pikepdf.Name.Image
    image.Width = width; image.Height = height
    image.ColorSpace = pikepdf.Name.DeviceGray; image.BitsPerComponent = 8
    image.Filter = pikepdf.Name.FlateDecode
    page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im0=image))
    page.Contents = pdf.make_stream(b"300 0 0 300 20 30 cm /Im0 Do")
    pdf.save(path); pdf.close()
    return path


def make_external_image_pdf(path):
    pdf = create_pdf(path, image_placements=[(72, 0, 0, 72, 20, 30)])
    with pikepdf.open(pdf, allow_overwriting_input=True) as document:
        image = next(iter(document.pages[0].Resources.XObject.values()))
        image["/F"] = pikepdf.String("linked-image.jpg")
        document.save(pdf)
    return path


def make_empty_image_pdf(path):
    pdf = pikepdf.Pdf.new()
    page = pdf.add_blank_page(page_size=(612, 792))
    image = pdf.make_stream(b"")
    image.Type = pikepdf.Name.XObject; image.Subtype = pikepdf.Name.Image
    image.Width = 2; image.Height = 2; image.ColorSpace = pikepdf.Name.DeviceRGB
    image.BitsPerComponent = 8
    page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im0=image))
    page.Contents = pdf.make_stream(b"2 0 0 2 10 20 cm /Im0 Do")
    pdf.save(path); pdf.close()
    return path

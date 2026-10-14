from pathlib import Path
import pytest

def make_pdf(pages=1):
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>"]
    kids = " ".join(f"{3 + i*2} 0 R" for i in range(pages))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {pages} >>".encode())
    for i in range(pages):
        page_id = 3 + i*2
        content_id = page_id + 1
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {612+i*10} 792] /Resources << >> /Contents {content_id} 0 R >>".encode())
        stream = b"0 0 1 rg 72 600 300 100 re f BT /F1 12 Tf 72 720 Td (PPView fixture) Tj ET"
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(out)); out.extend(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(out); out.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]: out.extend(f"{offset:010} 00000 n \n".encode())
    out.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(out)

@pytest.fixture
def pdf_file(tmp_path):
    path = tmp_path / "valid.pdf"; path.write_bytes(make_pdf()); return path

@pytest.fixture
def multi_pdf(tmp_path):
    path = tmp_path / "multi.pdf"; path.write_bytes(make_pdf(3)); return path

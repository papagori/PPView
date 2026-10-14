"""Render PPView's SVG logo assets and build the multi-size Windows ICO."""
from __future__ import annotations

from pathlib import Path
import struct

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


ROOT = Path(__file__).resolve().parents[1]
LOGO = ROOT / "assets" / "logo"
SIZES = (16, 24, 32, 48, 64, 128, 256)


def render_png(svg_path: Path, size: QSize, output: Path, background: str | None = None) -> bytes:
    renderer = QSvgRenderer(str(svg_path))
    if not renderer.isValid():
        raise RuntimeError(f"Invalid SVG: {svg_path}")
    image = QImage(size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent if background is None else background)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    if not image.save(str(output), "PNG"):
        raise RuntimeError(f"Could not save {output}")
    return output.read_bytes()


def make_ico(entries: list[tuple[int, bytes]], path: Path) -> None:
    header = struct.pack("<HHH", 0, 1, len(entries))
    directory = bytearray()
    offset = 6 + 16 * len(entries)
    for size, payload in entries:
        dimension = 0 if size == 256 else size
        directory.extend(struct.pack("<BBBBHHII", dimension, dimension, 0, 0, 1, 32,
                                     len(payload), offset))
        offset += len(payload)
    path.write_bytes(header + directory + b"".join(payload for _, payload in entries))


def main() -> None:
    QGuiApplication([])
    icon_svg = LOGO / "ppview-icon.svg"
    entries = []
    for size in SIZES:
        preview = LOGO / f".ppview-icon-{size}.png"
        payload = render_png(icon_svg, QSize(size, size), preview)
        entries.append((size, payload))
        preview.unlink()
    make_ico(entries, LOGO / "ppview.ico")
    render_png(LOGO / "ppview-logo-main.svg", QSize(1440, 296), LOGO / "ppview-logo-main-preview.png")
    render_png(icon_svg, QSize(512, 512), LOGO / "ppview-icon-preview.png", "#0b1424")
    render_png(LOGO / "ppview-splash.svg", QSize(960, 780), LOGO / "ppview-splash-preview.png")
    print(f"Generated {LOGO / 'ppview.ico'} with sizes: {', '.join(map(str, SIZES))}")


if __name__ == "__main__":
    main()

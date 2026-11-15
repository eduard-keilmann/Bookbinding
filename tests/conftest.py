"""Generate explicitly synthetic numbered pages with an independent PDF engine."""

from pathlib import Path

import pymupdf
import pytest
from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.generic import RectangleObject


@pytest.fixture
def pdf_factory(tmp_path):
    def create(
        count: int,
        name: str = "input.pdf",
        *,
        rotation: int = 0,
        cropped: bool = False,
        media_offset: bool = False,
    ) -> Path:
        path = tmp_path / name
        left, top = (30, 20) if cropped else (0, 0)
        with pymupdf.open() as document:
            for index in range(1, count + 1):
                page = document.new_page(
                    width=260 if cropped else 200, height=360 if cropped else 300
                )
                page.draw_rect(
                    pymupdf.Rect(left + 2, top + 2, left + 198, top + 298),
                    color=(0.05, 0.3, 0.45),
                    fill=(0.8, 0.95, 1),
                    width=2,
                )
                page.draw_rect(
                    pymupdf.Rect(left + 5, top + 5, left + 55, top + 25), color=None, fill=(1, 0, 0)
                )
                page.draw_rect(
                    pymupdf.Rect(left + 165, top + 265, left + 195, top + 295),
                    color=None,
                    fill=(0, 0, 0),
                )
                page.insert_text((left + 35, top + 70), f"PAGE{index:03d}", fontsize=23)
                page.insert_text((left + 35, top + 110), "SYNTHETIC TEST", fontsize=11)
                page.insert_text((left + 35, top + 250), "BOTTOM", fontsize=13)
                if cropped:
                    # A black bar just outside the crop must not leak into output.
                    page.draw_rect(pymupdf.Rect(0, 0, 260, 15), color=None, fill=(0, 0, 0))
                    page.set_cropbox(pymupdf.Rect(30, 20, 230, 320))
                page.set_rotation(rotation)
            document.save(path)
        if media_offset:
            writer = PdfWriter()
            with PdfReader(path) as reader:
                for source_page in reader.pages:
                    page = writer.add_page(source_page)
                    old_crop = list(page.cropbox)
                    old_media = list(page.mediabox)
                    page.add_transformation(Transformation().translate(40, 60))
                    page.mediabox = RectangleObject(
                        [
                            value + (40 if index % 2 == 0 else 60)
                            for index, value in enumerate(old_media)
                        ]
                    )
                    page.cropbox = RectangleObject(
                        [
                            value + (40 if index % 2 == 0 else 60)
                            for index, value in enumerate(old_crop)
                        ]
                    )
                shifted = tmp_path / f"shifted-{name}"
                writer.write(shifted)
            shifted.replace(path)
            writer.close()
        return path

    return create

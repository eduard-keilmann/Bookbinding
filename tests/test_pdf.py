"""Check actual output with a PDF renderer independent of pypdf."""

import hashlib
import json

import pymupdf
import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.errors import FileNotDecryptedError, PyPdfError
from pypdf.generic import RectangleObject

from bookbinding.pdf import POINTS_PER_MM, impose_pdf, inspect_pdf


@pytest.mark.parametrize("rotate_backs", [False, True])
def test_duplex_places_the_eight_book_pages_in_the_correct_halves(
    pdf_factory, tmp_path, rotate_backs
):
    source = pdf_factory(8)
    source_hash = hashlib.sha256(source.read_bytes()).digest()
    result = impose_pdf(source, tmp_path / "out", sheets_per_signature=2, rotate_backs=rotate_backs)
    assert len(result.files) == 1
    with pymupdf.open(result.files[0]) as document:
        assert len(document) == 4
        for index, (left, right) in enumerate([(8, 1), (2, 7), (6, 3), (4, 5)]):
            page = document[index]
            words = {word[4]: pymupdf.Rect(word[:4]) for word in page.get_text("words")}
            assert {word for word in words if word.startswith("PAGE")} == {
                f"PAGE{left:03d}",
                f"PAGE{right:03d}",
            }
            left_box, right_box = words[f"PAGE{left:03d}"], words[f"PAGE{right:03d}"]
            if index % 2 and rotate_backs:
                assert right_box.y1 < page.rect.height / 2 < left_box.y0
                expected_direction = (0, -1)
            else:
                assert left_box.y1 < page.rect.height / 2 < right_box.y0
                expected_direction = (0, 1)
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    if any(span["text"].startswith("PAGE") for span in line["spans"]):
                        assert line["dir"] == pytest.approx(expected_direction, abs=1e-6)
            assert page.rect.width / POINTS_PER_MM == pytest.approx(210, abs=1e-3)
            assert page.rect.height / POINTS_PER_MM == pytest.approx(297, abs=1e-3)
    assert hashlib.sha256(source.read_bytes()).digest() == source_hash
    manifest = json.loads((result.output_directory / "druckplan.json").read_text())
    assert manifest["jobs"][0]["sides"] == [
        {"left": 8, "right": 1, "back": False},
        {"left": 2, "right": 7, "back": True},
        {"left": 6, "right": 3, "back": False},
        {"left": 4, "right": 5, "back": True},
    ]


@pytest.mark.parametrize("rotate_backs", [False, True])
def test_manual_streams_follow_outside_to_inside_sheet_order(pdf_factory, tmp_path, rotate_backs):
    source = pdf_factory(8)
    duplex = impose_pdf(source, tmp_path / "duplex", rotate_backs=rotate_backs)
    manual = impose_pdf(source, tmp_path / "manual", duplex=False, rotate_backs=rotate_backs)
    assert [path.name for path in manual.files] == [
        "lage-001-vorderseiten.pdf",
        "lage-001-rueckseiten.pdf",
    ]
    with pymupdf.open(duplex.files[0]) as both:
        for stream_index, path in enumerate(manual.files):
            with pymupdf.open(path) as stream:
                assert len(stream) == 2
                for index, page in enumerate(stream):
                    assert (
                        page.get_pixmap().samples
                        == both[2 * index + stream_index].get_pixmap().samples
                    )


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
@pytest.mark.parametrize("media_offset", [False, True])
def test_rotated_offset_cropbox_renders_like_the_visible_source(
    pdf_factory, tmp_path, rotation, media_offset
):
    source = pdf_factory(4, rotation=rotation, cropped=True, media_offset=media_offset)
    with pymupdf.open(source) as source_document:
        width, height = source_document[3].rect.width, source_document[3].rect.height
        expected = source_document[3].get_pixmap()
    info = inspect_pdf(source)
    assert info.width_mm == pytest.approx(width / POINTS_PER_MM, abs=1e-5)
    assert info.height_mm == pytest.approx(height / POINTS_PER_MM, abs=1e-5)
    result = impose_pdf(
        source,
        tmp_path / "out",
        paper_size="LETTER",
        book_size_mm=(width / POINTS_PER_MM, height / POINTS_PER_MM),
    )
    # With a 1:1 book format the top half contains a rotated copy of source page 4.
    # Render that exact rectangle upright, then compare against the source render.
    with pymupdf.open(result.files[0]) as output:
        x = (612 - height) / 2
        clip = pymupdf.Rect(x, 396 - width, x + height, 396)
        actual = output[0].get_pixmap(matrix=pymupdf.Matrix(1, 1).prerotate(-90), clip=clip)
    assert (actual.width, actual.height) == (expected.width, expected.height)
    # Allow small font/edge antialiasing differences from re-rendering a transform.
    differences = [abs(a - b) for a, b in zip(actual.samples, expected.samples, strict=True)]
    assert sum(differences) / len(differences) < 1
    assert sum(difference > 40 for difference in differences) / len(differences) < 0.01


def test_padding_can_produce_fully_blank_sheet_sides(pdf_factory, tmp_path):
    source = pdf_factory(1)
    result = impose_pdf(source, tmp_path / "out", signature_sizes=[1, 1])
    assert result.plan.blank_page_count == 7
    with pymupdf.open(result.files[0]) as first, pymupdf.open(result.files[1]) as second:
        assert len(first) == len(second) == 2
        assert "PAGE001" in first[0].get_text()
        assert first[1].get_text() == ""
        assert all(page.get_text() == "" for page in second)
        assert all(set(page.get_pixmap().samples) == {255} for page in second)


@pytest.mark.parametrize(
    "mode,name,pages",
    [
        ("booklet", "einzelheft-duplex.pdf", 6),
        ("perfect-bound", "klebebindung-duplex.pdf", 6),
        ("automatic", "lage-001-duplex.pdf", 6),
    ],
)
def test_binding_modes_export_expected_files(pdf_factory, tmp_path, mode, name, pages):
    result = impose_pdf(pdf_factory(12), tmp_path / "out", mode=mode)
    assert [path.name for path in result.files] == [name]
    with pymupdf.open(result.files[0]) as document:
        assert len(document) == pages
        assert sorted(
            word[4]
            for page in document
            for word in page.get_text("words")
            if word[4].startswith("PAGE")
        ) == [f"PAGE{index:03d}" for index in range(1, 13)]


def test_custom_export_reports_sizes_and_preserves_source_filename(pdf_factory, tmp_path):
    source = pdf_factory(19, "Buch mit Leerzeichen ü.pdf")
    result = impose_pdf(source, signature_sizes=[2, 3], flyleaf=False)
    assert result.output_directory == tmp_path / "Buch mit Leerzeichen ü-files"
    manifest = json.loads((result.output_directory / "druckplan.json").read_text())
    assert manifest["sheets_per_signature"] == [2, 3]
    assert manifest["source"] == source.name
    assert manifest["blank_book_pages"] == 1
    assert (result.output_directory / "Druckhinweise.txt").is_file()


@pytest.mark.parametrize(
    "book_size",
    [(0, 100), (-1, 100), (100, float("nan")), (100, float("inf")), (200, 200), (100, 300)],
)
def test_invalid_book_size_creates_no_output(pdf_factory, tmp_path, book_size):
    destination = tmp_path / "out"
    with pytest.raises(ValueError):
        impose_pdf(pdf_factory(4), destination, book_size_mm=book_size)
    assert not destination.exists()


def test_stretching_changes_the_page_shape_but_keeps_its_content(pdf_factory, tmp_path):
    source = pdf_factory(4)
    normal = impose_pdf(source, tmp_path / "normal", book_size_mm=(100, 200))
    stretched = impose_pdf(
        source, tmp_path / "stretch", book_size_mm=(100, 200), keep_proportions=False
    )
    with pymupdf.open(normal.files[0]) as a, pymupdf.open(stretched.files[0]) as b:
        box_a = next(word for word in a[0].get_text("words") if word[4] == "PAGE004")
        box_b = next(word for word in b[0].get_text("words") if word[4] == "PAGE004")
        assert box_b[2] - box_b[0] > (box_a[2] - box_a[0]) * 1.3
        assert box_b[3] - box_b[1] == pytest.approx(box_a[3] - box_a[1], abs=0.01)


def test_existing_destination_and_source_are_never_overwritten(pdf_factory, tmp_path):
    source = pdf_factory(4)
    destination = tmp_path / "out"
    destination.mkdir()
    sentinel = destination / "keep.txt"
    sentinel.write_text("unchanged")
    with pytest.raises(FileExistsError):
        impose_pdf(source, destination)
    with pytest.raises(FileExistsError):
        impose_pdf(source, source)
    assert sentinel.read_text() == "unchanged"
    with pymupdf.open(source) as document:
        assert len(document) == 4


def test_insufficient_lagenfolge_never_creates_a_partial_export(pdf_factory, tmp_path):
    destination = tmp_path / "out"
    with pytest.raises(ValueError, match="zu klein"):
        impose_pdf(pdf_factory(17), destination, signature_sizes=[4])
    assert not destination.exists()


def test_failure_in_later_signature_cleans_up_all_temporary_files(pdf_factory, tmp_path):
    source = pdf_factory(8)
    malformed = tmp_path / "malformed.pdf"
    with PdfReader(source) as reader, PdfWriter() as writer:
        writer.append(reader)
        writer.pages[4].cropbox = RectangleObject((0, 0, 0, 100))
        writer.write(malformed)
    with pytest.raises(ValueError, match="Seitenbox"):
        impose_pdf(malformed, tmp_path / "out", sheets_per_signature=1)
    assert not (tmp_path / "out").exists()
    assert not list(tmp_path.glob(".bookbinding-*"))


def test_password_is_required_and_not_recorded_in_print_plan(pdf_factory, tmp_path):
    source = pdf_factory(4)
    encrypted = tmp_path / "encrypted.pdf"
    with PdfReader(source) as reader, PdfWriter() as writer:
        writer.append(reader)
        writer.encrypt("test-password", algorithm="AES-256")
        writer.write(encrypted)
    for password in (None, "wrong"):
        with pytest.raises(FileNotDecryptedError):
            impose_pdf(encrypted, tmp_path / "out", password=password)
        assert not (tmp_path / "out").exists()
    assert inspect_pdf(encrypted, password="test-password").page_count == 4
    result = impose_pdf(encrypted, tmp_path / "out", password="test-password")
    assert "test-password" not in (result.output_directory / "druckplan.json").read_text()
    with PdfReader(result.files[0]) as reader:
        assert not reader.is_encrypted


def test_malformed_or_empty_pdf_and_missing_input_are_rejected(tmp_path):
    malformed = tmp_path / "invalid.pdf"
    malformed.write_bytes(b"not a pdf")
    with pytest.raises(PyPdfError):
        impose_pdf(malformed, tmp_path / "out")
    empty = tmp_path / "empty.pdf"
    with PdfWriter() as writer:
        writer.write(empty)
    with pytest.raises(ValueError, match="keine Seiten"):
        impose_pdf(empty, tmp_path / "out")
    with pytest.raises(FileNotFoundError):
        impose_pdf(tmp_path / "missing.pdf", tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_unknown_paper_size_is_rejected(pdf_factory, tmp_path):
    with pytest.raises(ValueError, match="Unbekanntes Papierformat"):
        impose_pdf(pdf_factory(4), tmp_path / "out", paper_size="unknown")

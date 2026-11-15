"""Vector-preserving two-up PDF output, isolated from the page-ordering rules."""

import json
import math
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from pypdf import PageObject, PdfReader, PdfWriter, Transformation
from pypdf.errors import FileNotDecryptedError
from pypdf.generic import RectangleObject

from .errors import InputError, OutputExistsError
from .layout import BindingMode, ImpositionPlan, SheetSide, make_plan

POINTS_PER_MM = 72 / 25.4

# ISO dimensions in mm; additional paper formats use dimensions in points.
PAPER_SIZES: dict[str, tuple[float, float]] = {
    name: (width * POINTS_PER_MM, height * POINTS_PER_MM)
    for name, (width, height) in {
        "A0": (841, 1189),
        "A1": (594, 841),
        "A2": (420, 594),
        "A3": (297, 420),
        "A4": (210, 297),
        "A5": (148, 210),
        "A6": (105, 148),
        "A7": (74, 105),
        "A8": (52, 74),
        "A9": (37, 52),
        "B0": (1000, 1414),
        "B1": (707, 1000),
        "B2": (500, 707),
        "B3": (353, 500),
        "B4": (250, 353),
        "B5": (176, 250),
        "B6": (125, 176),
        "B7": (88, 125),
        "B8": (62, 88),
        "B9": (44, 62),
        "B10": (31, 44),
    }.items()
}
PAPER_SIZES.update(
    {
        "LETTER": (612, 792),
        "NOTE": (540, 720),
        "LEGAL": (612, 1008),
        "TABLOID": (792, 1224),
        "EXECUTIVE": (522, 756),
        "POSTCARD": (283, 416),
        "ARCH_E": (2592, 3456),
        "ARCH_C": (1296, 1728),
        "ARCH_B": (864, 1296),
        "ARCH_A": (648, 864),
        "FLSA": (612, 936),
        "FLSE": (648, 936),
        "HALFLETTER": (396, 612),
        "_11X17": (792, 1224),
        "ID_1": (242.65, 153),
        "ID_2": (297, 210),
        "ID_3": (354, 249),
        "LEDGER": (1224, 792),
        "CROWN_QUARTO": (535, 697),
        "LARGE_CROWN_QUARTO": (569, 731),
        "DEMY_QUARTO": (620, 782),
        "ROYAL_QUARTO": (671, 884),
        "CROWN_OCTAVO": (348, 527),
        "LARGE_CROWN_OCTAVO": (365, 561),
        "DEMY_OCTAVO": (391, 612),
        "ROYAL_OCTAVO": (442, 663),
        "SMALL_PAPERBACK": (314, 504),
        "PENGUIN_SMALL_PAPERBACK": (314, 513),
        "PENGUIN_LARGE_PAPERBACK": (365, 561),
    }
)


@dataclass(frozen=True)
class PdfInfo:
    """Input metadata used by the desktop preview."""

    page_count: int
    width_mm: float
    height_mm: float


@dataclass(frozen=True)
class ExportResult:
    """Completed export; files lists printable PDFs, excluding the sidecar files."""

    output_directory: Path
    files: tuple[Path, ...]
    plan: ImpositionPlan


@contextmanager
def _open_pdf(source: Path, password: str | None) -> Iterator[PdfReader]:
    with source.open("rb") as stream, PdfReader(stream) as reader:
        if reader.is_encrypted and not reader.decrypt(password if password is not None else ""):
            raise FileNotDecryptedError("Die PDF benötigt ein gültiges Passwort.")
        if not reader.pages:
            raise InputError("Die PDF enthält keine Seiten.")
        yield reader


def _visible_box(page: PageObject) -> RectangleObject:
    """Intersect CropBox with MediaBox, matching the visible printed page."""
    media, crop = page.mediabox, page.cropbox
    coordinates = [float(value) for value in (*media, *crop)]
    if not all(math.isfinite(value) for value in coordinates):
        raise InputError("PDF-Seitenboxen müssen endliche Koordinaten haben.")
    box = RectangleObject(
        (
            max(media.left, crop.left),
            max(media.bottom, crop.bottom),
            min(media.right, crop.right),
            min(media.top, crop.top),
        )
    )
    if box.width <= 0 or box.height <= 0:
        raise InputError("Die PDF enthält eine leere oder ungültige Seitenbox.")
    if page.rotation % 360 not in (0, 90, 180, 270):
        raise InputError("Die PDF-Seitendrehung muss ein Vielfaches von 90 Grad sein.")
    return box


def inspect_pdf(source: str | Path, *, password: str | None = None) -> PdfInfo:
    """Read page count and the visible, rotated size of the first page."""
    with _open_pdf(Path(source), password) as reader:
        page = reader.pages[0]
        box = _visible_box(page)
        width, height = float(box.width), float(box.height)
        if page.rotation % 180:
            width, height = height, width
        unit = float(page.user_unit)
        return PdfInfo(
            len(reader.pages), width * unit / POINTS_PER_MM, height * unit / POINTS_PER_MM
        )


def _merge_book_page(
    destination: PageObject,
    source: PageObject,
    *,
    normalizer: PdfWriter,
    left: bool,
    book_size: tuple[float, float],
    keep_proportions: bool,
) -> None:
    # pypdf 7 requires writer-owned pages for content transformations. A separate
    # writer also prevents crop/rotation changes from mutating the source reader.
    page = normalizer.add_page(source, excluded_keys=["/Annots", "/B"])
    page.cropbox = _visible_box(page)
    page.transfer_rotation_to_content()
    crop = page.cropbox
    page_width, page_height = float(crop.width), float(crop.height)
    scale_x, scale_y = book_size[0] / page_width, book_size[1] / page_height
    if keep_proportions:
        scale_x = scale_y = min(scale_x, scale_y)
    imposed_width, imposed_height = page_width * scale_x, page_height * scale_y
    sheet_width, sheet_height = (
        float(destination.mediabox.width),
        float(destination.mediabox.height),
    )
    baseline = (sheet_width - imposed_height) / 2
    # Both book pages meet at the fold; extra width stays at the outside edge.
    top = sheet_height / 2 + imposed_width if left else sheet_height / 2
    transform = Transformation(
        (
            0,
            -scale_x,
            scale_y,
            0,
            baseline - float(crop.bottom) * scale_y,
            top + float(crop.left) * scale_x,
        )
    )
    destination.merge_transformed_page(page, transform)


def _write_pdf(
    path: Path,
    sides: Sequence[SheetSide],
    reader: PdfReader,
    *,
    paper: tuple[float, float],
    book_size: tuple[float, float],
    keep_proportions: bool,
    rotate_backs: bool,
) -> None:
    with PdfWriter() as writer, PdfWriter() as normalizer:
        writer.add_metadata({"/Title": path.stem, "/Creator": "Bookbinding Python"})
        for side in sides:
            output_page = writer.add_blank_page(width=paper[0], height=paper[1])
            for number, left in ((side.left, True), (side.right, False)):
                if number is not None:
                    _merge_book_page(
                        output_page,
                        reader.pages[number - 1],
                        normalizer=normalizer,
                        left=left,
                        book_size=book_size,
                        keep_proportions=keep_proportions,
                    )
            if side.is_back and rotate_backs:
                output_page.add_transformation(Transformation((-1, 0, 0, -1, *paper)))
        with path.open("wb") as stream:
            writer.write(stream)


def impose_pdf(
    source: str | Path,
    output_directory: str | Path | None = None,
    *,
    sheets_per_signature: int = 8,
    signature_sizes: Sequence[int] | None = None,
    mode: BindingMode = "signatures",
    flyleaf: bool = False,
    paper_size: str = "A4",
    book_size_mm: tuple[float, float] | None = None,
    keep_proportions: bool = True,
    duplex: bool = True,
    rotate_backs: bool = True,
    password: str | None = None,
) -> ExportResult:
    """Write imposed PDFs into a new directory, publishing only a complete export.

    Paper dimensions describe the sheet before the 90-degree book-page rotation.
    A custom book_size_mm is (width, height) of one upright book page. Backs in
    manual mode follow the outside-to-inside sheet order.
    """
    source = Path(source).expanduser().resolve(strict=True)
    destination = (
        Path(output_directory).expanduser().absolute()
        if output_directory is not None
        else source.with_name(f"{source.stem}-files")
    )
    if destination.exists() or destination.is_symlink():
        raise OutputExistsError("Zielordner existiert bereits: {path}", path=destination)
    if paper_size not in PAPER_SIZES:
        raise InputError("Unbekanntes Papierformat: {paper}", paper=paper_size)
    paper = PAPER_SIZES[paper_size]
    book_size = (paper[1] / 2, paper[0])
    if book_size_mm is not None:
        if len(book_size_mm) != 2 or any(
            not math.isfinite(value) or value <= 0 for value in book_size_mm
        ):
            raise InputError("Buchseitenbreite und -höhe müssen positive, endliche Maße sein.")
        book_size = (book_size_mm[0] * POINTS_PER_MM, book_size_mm[1] * POINTS_PER_MM)
        if book_size[0] > paper[1] / 2 + 1e-8 or book_size[1] > paper[0] + 1e-8:
            raise InputError("Das Buchseitenformat passt nicht auf einen halben Druckbogen.")

    with _open_pdf(source, password) as reader:
        plan = make_plan(
            len(reader.pages),
            sheets_per_signature=sheets_per_signature,
            signature_sizes=signature_sizes,
            mode=mode,
            flyleaf=flyleaf,
        )
        if mode in ("booklet", "perfect-bound"):
            sides = tuple(side for signature in plan.signatures for side in signature.sides)
            jobs = [("einzelheft" if mode == "booklet" else "klebebindung", sides)]
        else:
            jobs = [
                (f"lage-{index:03d}", signature.sides)
                for index, signature in enumerate(plan.signatures, 1)
            ]

        with tempfile.TemporaryDirectory(
            prefix=".bookbinding-", dir=destination.parent
        ) as temporary:
            staging = Path(temporary) / "complete"
            staging.mkdir()
            file_names = []
            print_jobs = []
            for name, sides in jobs:
                streams = (
                    [("duplex", sides)]
                    if duplex
                    else [
                        ("vorderseiten", sides[::2]),
                        ("rueckseiten", sides[1::2]),
                    ]
                )
                for suffix, stream in streams:
                    file_name = f"{name}-{suffix}.pdf"
                    _write_pdf(
                        staging / file_name,
                        stream,
                        reader,
                        paper=paper,
                        book_size=book_size,
                        keep_proportions=keep_proportions,
                        rotate_backs=rotate_backs,
                    )
                    file_names.append(file_name)
                    print_jobs.append(
                        {
                            "file": file_name,
                            "sides": [
                                {"left": side.left, "right": side.right, "back": side.is_back}
                                for side in stream
                            ],
                        }
                    )

            manifest = {
                "source": source.name,
                "source_pages": plan.source_page_count,
                "mode": mode,
                "paper_size": paper_size,
                "paper_size_mm": [dimension / POINTS_PER_MM for dimension in paper],
                "book_size_mm": [dimension / POINTS_PER_MM for dimension in book_size],
                "keep_proportions": keep_proportions,
                "duplex": duplex,
                "rotate_backs": rotate_backs,
                "flyleaf": flyleaf,
                "sheets_per_signature": [signature.sheet_count for signature in plan.signatures],
                "total_sheets": plan.sheet_count,
                "blank_book_pages": plan.blank_page_count,
                "jobs": print_jobs,
            }
            (staging / "druckplan.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            edge = "lange Kante" if rotate_backs else "kurze Kante"
            instructions = (
                f"Bookbinding: {source.name}\n"
                f"{len(plan.signatures)} Lagen / {plan.sheet_count} Bögen / "
                f"{plan.blank_page_count} zusätzliche Leerseiten\n\n"
                "Eine PDF-Seite pro Blattseite, tatsächliche Größe / 100 %.\n"
                "Broschürendruck und Zwei-Seiten-Druck im Druckdialog ausschalten.\n"
            )
            if duplex:
                instructions += (
                    f"Duplex: Bei unveränderter Bogenausrichtung normalerweise {edge}.\n"
                    "PDF-Seiten in der vorgegebenen Reihenfolge drucken.\n"
                )
            else:
                instructions += (
                    "Je Lage zuerst die Vorderseitendatei drucken, dann denselben Stapel\n"
                    "passend wenden/einlegen und die Rückseitendatei drucken.\n"
                    "Beide Dateien sind von außen nach innen geordnet. Abhängig vom\n"
                    "Papierweg die Rückseitendatei ggf. in umgekehrter Reihenfolge drucken.\n"
                )
            instructions += (
                "\nZuerst ein kleines Heft zur Prüfung von Papierweg und Drehung drucken.\n"
                "Jede Lage separat falten; anschließend in Lagenreihenfolge zusammentragen.\n"
                "Der Druckplan zählt die Quellseiten ab 1; null steht für eine Leerseite.\n"
            )
            (staging / "Druckhinweise.txt").write_text(instructions, encoding="utf-8")
            if destination.exists() or destination.is_symlink():
                raise OutputExistsError(
                    "Zielordner wurde inzwischen angelegt: {path}", path=destination
                )
            staging.rename(destination)

    return ExportResult(destination, tuple(destination / name for name in file_names), plan)

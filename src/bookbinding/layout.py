"""Page ordering without PDF, GUI, or filesystem dependencies.

Page numbers are one-based. None represents an intentionally blank book page.
Signature sizes count physical sheets: one sheet carries four book pages.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from .errors import InputError

BindingMode = Literal["signatures", "automatic", "booklet", "perfect-bound"]

AUTOMATIC_SIGNATURES = (
    (1,),
    (1,),
    (2,),
    (3,),
    (4,),
    (5,),
    (6,),
    (7,),
    (8,),
    (9,),
    (10,),
    (11,),
    (12,),
    (13,),
    (14,),
    (15,),
    (16,),
    (9, 8),
    (9, 9),
    (10, 9),
    (10, 10),
    (7, 7, 7),
    (8, 7, 7),
    (8, 8, 7),
    (8, 8, 8),
    (9, 8, 8),
    (9, 9, 8),
    (9, 9, 9),
    (7, 7, 7, 7),
    (8, 7, 7, 7),
    (8, 8, 7, 7),
    (8, 8, 8, 7),
    (8, 8, 8, 8),
    (9, 8, 8, 8),
    (9, 9, 8, 8),
    (7, 7, 7, 7, 7),
    (8, 7, 7, 7, 7),
    (8, 8, 7, 7, 7),
    (8, 8, 8, 7, 7),
    (8, 8, 8, 8, 7),
    (8, 8, 8, 8, 8),
    (9, 8, 8, 8, 8),
    (7, 7, 7, 7, 7, 7),
    (8, 7, 7, 7, 7, 7),
    (8, 8, 7, 7, 7, 7),
    (8, 8, 8, 7, 7, 7),
    (8, 8, 8, 8, 7, 7),
    (8, 8, 8, 8, 8, 7),
    (8, 8, 8, 8, 8, 8),
)


@dataclass(frozen=True)
class SheetSide:
    """Two book pages on a sheet side, viewed with the text upright."""

    left: int | None
    right: int | None
    is_back: bool


@dataclass(frozen=True)
class Signature:
    """A consecutive reading-order section, folded from outer to inner sheet."""

    pages: tuple[int | None, ...]

    @property
    def sheet_count(self) -> int:
        return len(self.pages) // 4

    @property
    def sides(self) -> tuple[SheetSide, ...]:
        result = []
        for sheet in range(self.sheet_count):
            first = 2 * sheet
            last = len(self.pages) - 1 - first
            result.append(SheetSide(self.pages[last], self.pages[first], False))
            result.append(SheetSide(self.pages[first + 1], self.pages[last - 1], True))
        return tuple(result)


@dataclass(frozen=True)
class ImpositionPlan:
    """Complete print layout including padding and optional flyleaves."""

    source_page_count: int
    signatures: tuple[Signature, ...]
    mode: BindingMode

    @property
    def sheet_count(self) -> int:
        return sum(signature.sheet_count for signature in self.signatures)

    @property
    def blank_page_count(self) -> int:
        return self.sheet_count * 4 - self.source_page_count


def make_plan(
    page_count: int,
    *,
    sheets_per_signature: int = 8,
    signature_sizes: Sequence[int] | None = None,
    mode: BindingMode = "signatures",
    flyleaf: bool = False,
) -> ImpositionPlan:
    """Plan sheets without dropping pages or altering the source.

    In signatures mode, the last signature may be shorter than the requested
    maximum. Explicit signature_sizes may add blanks but must fit every page.
    Automatic mode uses a lookup table up to 192 pages and a target of
    eight sheets per signature for longer documents.
    """
    if type(page_count) is not int or page_count < 1:
        raise InputError("Die PDF muss mindestens eine Seite enthalten.")
    if type(sheets_per_signature) is not int or sheets_per_signature < 1:
        raise InputError("Bögen je Lage muss eine positive ganze Zahl sein.")
    if mode not in ("signatures", "automatic", "booklet", "perfect-bound"):
        raise InputError("Unbekanntes Bindeverfahren: {method}", method=mode)
    if signature_sizes is not None and mode != "signatures":
        raise InputError("Eigene Lagenfolgen sind nur im Lagenmodus möglich.")
    if mode == "automatic" and sheets_per_signature != 8:
        raise InputError("Die Automatik verwendet eine Vorgabe von acht Bögen.")

    pages: list[int | None] = list(range(1, page_count + 1))
    if flyleaf:
        pages = [None, None, *pages, None, None]
    pages.extend([None] * (-len(pages) % 4))
    sheet_count = len(pages) // 4

    if signature_sizes is not None:
        sizes = tuple(signature_sizes)
        if not sizes or any(type(size) is not int or size < 1 for size in sizes):
            raise InputError("Jede Lage muss eine positive ganze Bogenzahl haben.")
        if sum(sizes) < sheet_count:
            raise InputError(
                (
                    "Lagenfolge zu klein: {capacity} Plätze für {pages} "
                    "Buchseiten einschließlich Vorsatz und Auffüllseiten. Es "
                    "werden keine Seiten abgeschnitten."
                ),
                capacity=sum(sizes) * 4,
                pages=len(pages),
            )
        pages.extend([None] * (sum(sizes) * 4 - len(pages)))
    elif mode == "booklet":
        sizes = (sheet_count,)
    elif mode == "perfect-bound":
        sizes = (1,) * sheet_count
    elif mode == "automatic":
        if sheet_count <= 48:
            sizes = AUTOMATIC_SIGNATURES[sheet_count]
        else:
            count, remainder = divmod(sheet_count, 8)
            if remainder == 0:
                sizes = (8,) * count
            else:
                count += 1
                full_count = count - 8 + remainder
                sizes = (8,) * full_count + (7,) * (count - full_count)
    else:
        full_count, remainder = divmod(sheet_count, sheets_per_signature)
        sizes = (sheets_per_signature,) * full_count
        if remainder:
            sizes += (remainder,)

    signatures = []
    start = 0
    for size in sizes:
        end = start + size * 4
        signatures.append(Signature(tuple(pages[start:end])))
        start = end
    return ImpositionPlan(page_count, tuple(signatures), mode)

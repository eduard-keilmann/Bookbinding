# Bookbinding

Arrange PDF pages into folded signatures for sewn bookbinding.
A Python 3 desktop application with English and German interfaces.

## Interface language

The interface starts in English. Click **Deutsch** to switch to German or
**English** to switch back. Your settings, loaded PDF and any running export
are preserved. The language choice applies to the current window.

Translations are stored in `src/bookbinding/i18n.py`. German messages serve
as catalog keys, with English translations alongside them. Selected options
use language-independent IDs. Errors carry their values separately; the
interface translates and formats them for display. Every new message needs
a catalog entry. Missing translations raise an error rather than silently
falling back to another language.

The language switch applies to the interface. Output filenames and the JSON
print-plan format stay the same; generated printing instructions remain in
German. Messages from third-party libraries are displayed as provided.

## Running the application

The application is developed and tested on macOS. A Linux launcher is also
included, but a full Linux desktop test has not yet been performed.
Windows is not supported.

### macOS

Double-click `Bookbinding starten.command`. The launcher uses the existing
project environment or creates one with uv if needed.
You need Python 3.11 or later with Tkinter and [uv](https://docs.astral.sh/uv/).

You can also run these commands from the project directory:

```sh
uv sync --locked --no-dev
uv run --locked --no-dev python -m bookbinding
```

Tkinter must be available in the Python installation used by the project.
The tested macOS setup uses Python 3.11 with Tkinter; the local Homebrew
Python 3.12 installation does not include `_tkinter`. The macOS launcher
therefore prefers the configured project environment.

### Linux

You need Python 3.11 or later with Tkinter, uv and a graphical desktop session.
Install Tkinter through your distribution's package manager if needed.
Run `python3 -m tkinter` to check that it can open a window
([Python documentation](https://docs.python.org/3/library/tkinter.html)).

From the project directory, run:

```sh
./bookbinding-linux.sh
```

The launcher uses an existing `.venv`. Otherwise, uv creates the environment
with the detected system Python. Automatic Python downloads are disabled so
that the interpreter with Tkinter is used
([uv documentation](https://docs.astral.sh/uv/concepts/python-versions/)).
The initial setup needs network access to download the project dependencies.
Create the environment on Linux; do not copy a macOS `.venv` across.

**Open output folder** uses `xdg-open`, or `gio open` if `xdg-open` is unavailable.
If neither program is installed, a message shows the output path.
These code paths have automated tests, but have not been tested on a Linux desktop.

## Sheets, signatures and settings

A **sheet** is one physical piece of paper, printed on both sides and folded
once. It carries **four book pages**. Several sheets nested inside one another
form a **signature**. A four-sheet signature therefore contains 16 book pages.

| Binding method | Behaviour |
| --- | --- |
| Signatures with a sheet limit | Choose the maximum sheets per signature. The last signature may be smaller. |
| Custom signatures | For example, `4, 4, 3` gives signatures of 16, 16 and 12 book pages. Extra capacity is filled with blanks. Insufficient capacity is rejected. |
| Automatic signatures | Uses a lookup table up to 192 pages, then distributes sheets with a target of eight sheets per signature. Short documents may form one large signature. |
| Single booklet | The entire document forms one signature. |
| Perfect binding | Each sheet carries four consecutive book pages, arranged as 4–1 on the front and 2–3 on the back. |

You can add two blank pages at the front and two at the back. Further blank
pages are added at the end if needed to reach a multiple of four. The preview
shows the number of signatures, sheets and added blank pages before export.

Two book pages are placed on each PDF output page. The output sheet is in
portrait orientation, with the book pages rotated by 90 degrees. When viewed
with the text upright, the outer sheet of an eight-page booklet has page 8
on the left and page 1 on the right, with pages 2 and 7 on the back.

You can choose the paper size, book page size, proportional scaling or
stretch-to-fit, and whether to rotate the backs. Dimensions are in millimetres.
**Use half the sheet** uses the full area of a folded half-sheet.
The application accounts for PDF crop boxes, offset page boxes and existing
page rotation. Text and vector graphics remain PDF content rather than
being rasterized.

## Output and printing

The source PDF is not modified. Choose a **new output folder**; existing
folders are not overwritten. The default is `<PDF-name>-files`. If that name
is already taken, the interface suggests an unused name with a numeric suffix.

- Duplex output: `lage-001-duplex.pdf`, with alternating fronts and backs.
- Manual duplex: `lage-001-vorderseiten.pdf` and `lage-001-rueckseiten.pdf`.
  Both files follow the sheet order from the outside to the inside.
- Single booklet and perfect binding produce one combined file, or a pair
  of files for manual duplex printing.
- `druckplan.json` records source page numbers, blanks and export settings.
- `Druckhinweise.txt` contains printing instructions for the selected mode.

In the print dialog, select **one PDF page per sheet side** and
**100% / actual size**. The pages are already arranged for folding, so do not
apply another booklet or two-pages-per-sheet setting.

For portrait output without automatic orientation changes, **flip on the
long edge** normally matches the enabled back-rotation option; **flip on the
short edge** matches disabled back rotation. Printer drivers and manual paper
feeding can differ. Print and fold a numbered two-sheet booklet first to
check orientation and reading order. For manual duplex, the required order
of the backs depends on the paper path. Use reverse order in the print dialog
for the back-side file if needed.

A synthetic eight-page test booklet is included:
[`examples/probeheft.pdf`](examples/probeheft.pdf) is the source, and
[`examples/probeheft-druck/lage-001-duplex.pdf`](examples/probeheft-druck/lage-001-duplex.pdf)
is the imposed version for two A4 sheets with back rotation enabled.
Use it to check your print settings before printing a whole book.

## Python usage

```python
from bookbinding import make_plan
from bookbinding.pdf import impose_pdf

plan = make_plan(35, sheets_per_signature=4)
print([signature.sheet_count for signature in plan.signatures])  # [4, 4, 1]

result = impose_pdf(
    "book.pdf",
    "book-print",  # Must not already exist.
    signature_sizes=[4, 4, 3],
    paper_size="A4",
    duplex=True,
    rotate_backs=True,
)
print(result.files)
```

`None` in a page plan represents a blank book page. Source pages are numbered
from 1, regardless of printed page numbers or PDF page labels.
Password-protected PDFs can be opened with their password. Output files are
unencrypted print copies; passwords are not recorded in the print plan.
Interactive forms, comments, links, bookmarks and digital signatures are not
preserved. The output contains static page content for printing. Export form
values to a static PDF before using the application.

The PDF implementation follows the official pypdf documentation on
[transformations](https://pypdf.readthedocs.io/en/stable/user/cropping-and-transforming.html)
and [encryption](https://pypdf.readthedocs.io/en/stable/user/encryption-decryption.html).

## Development and checks

```sh
uv sync --locked --group dev
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
```

To enable tests with real Tk widgets in a desktop session:

```sh
BOOKBINDING_GUI_TESTS=1 uv run --locked pytest tests/test_gui.py
```

Tests cover worked page-ordering examples, reading order after folding,
page completeness, signature capacity, blank pages and invalid inputs.
PDF integration tests use synthetic numbered pages to check export, placement,
rotation, cropping, encryption and file protection. PyMuPDF is used only for
development and independent rendering checks. Printer paper handling must
be checked on the actual device.
See [docs/verification.md](docs/verification.md) for recorded results and limitations.

The layout assumes left-bound books read from left to right, with four book
pages per folded sheet. Paper thickness and creep are not compensated for.

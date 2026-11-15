# Bookbinding

Prepare PDFs for printing, folding and sewing into a book. Bookbinding arranges
pages into **signatures**: groups of folded sheets that you sew together along
the spine. It exports print-ready PDFs for automatic or manual duplex printing.

For example, an eight-page PDF becomes four printed sides on two sheets.
Nest the sheets and fold them together to read pages 1 through 8 in order.
The source PDF is left unchanged.

## What you can do

- Choose the maximum number of sheets per signature, or enter a sequence such
  as `4, 4, 3` for signatures containing 16, 16 and 12 book pages.
- Make a single booklet or arrange sheets for perfect binding.
- Set the paper size, book page size and scaling.
- Add blank pages at the front and back; remaining sheet space is filled
  with blanks automatically.
- Export alternating fronts and backs for a duplex printer, or separate
  front-side and back-side files for manual printing.

Text and vector graphics remain PDF content rather than being converted to
images. The interface is available in English and German.

## Get started

The application is developed and tested on **macOS**. A Linux launcher is
included; full Linux desktop testing is still pending. Windows is not supported.

You need:

- Python **3.11 or later**, with Tkinter.
- [uv](https://docs.astral.sh/uv/) to install the project dependencies.
- A graphical desktop session.

Download and extract this repository, or clone it:

```sh
git clone https://github.com/eduard-keilmann/Bookbinding.git
cd Bookbinding
```

### macOS

Double-click **`Bookbinding starten.command`** in the project folder. It creates
the project environment on first launch if one has not been configured.
The initial setup needs an internet connection to download dependencies.

To set up and run the application from a terminal instead:

```sh
python3 -m tkinter
uv sync --locked --no-dev --no-python-downloads --python "$(command -v python3)"
.venv/bin/python -m bookbinding
```

The first command should open a small test window. If it fails, use a Python
installation with Tkinter before creating the project environment.

### Linux

Install Python with Tkinter through your distribution's package manager,
then run the launcher from the project folder:

```sh
./bookbinding-linux.sh
```

It checks Python and Tkinter, then uses or creates the project environment.
Create a separate environment on each system; do not copy a macOS `.venv`
to Linux. Opening the output folder requires `xdg-open` or `gio`.

## Prepare your first PDF

1. Click **Open PDF** and select your document.
2. Choose a binding method. For a sewn book, start with **Signatures with
   a sheet limit** and set the maximum sheets per signature.
3. Select your paper size and book page size. Review the signature and
   blank-page counts in the preview.
4. Choose a **new output folder**, then click **Create print PDFs**.
5. When the export finishes, click **Open output folder**.

One sheet of paper, printed on both sides and folded once, holds **four book
pages**. Four sheets per signature therefore means 16 book pages per signature.
The last signature may be smaller than the selected limit.

The available binding methods are:

| Method | Use it for |
| --- | --- |
| Signatures with a sheet limit | A sewn book with a chosen maximum number of sheets per signature. |
| Custom signatures | A specific sequence of sheet counts, such as `4, 4, 3`. Extra capacity becomes blank pages; insufficient capacity is rejected. |
| Automatic signatures | Suggested groups based on document length. Up to 192 pages, sizes come from a table; longer documents use an eight-sheet target. |
| Single booklet | One signature containing the whole document. |
| Perfect binding | Individual folded sheets arranged as 4–1 on the front and 2–3 on the back. |

**Use half the sheet** fills the available half-sheet area while keeping page
proportions by default. For A4 paper, the folded page area is 148.5 × 210 mm.
Book pages are rotated by 90° within the portrait output PDF.

The interface starts in English. Use **Deutsch** or **English** to switch
languages without losing your settings. The choice applies to the current
window. Output filenames stay the same in both languages, and the generated
printing instructions are currently in German.

## Print and fold

**Print a small test booklet before printing a whole book.** A sample is included:

- [Eight-page source PDF](examples/probeheft.pdf)
- [Print-ready PDF for two A4 sheets](examples/probeheft-druck/lage-001-duplex.pdf)

Use these print settings for the sample and for default A4 output:

- **A4, portrait, actual size / 100%.** Match the paper size to your export
  when using another format.
- **One PDF page per sheet side.** Leave booklet printing and additional
  two-pages-per-sheet settings off.
- With **Rotate backs by 180°** enabled, use **flip on the long edge**.
  With it disabled, use **flip on the short edge**. Keep the output orientation
  unchanged; check the result on your printer.

For manual duplex printing, print the front-side file, reinsert the same
stack and print the back-side file. Both files list sheets from the outside
to the inside. Your printer's paper path determines whether you need to
print the backs in reverse order.

Nest the sheets of each signature, fold them together, then gather the
signatures in order for sewing. For an eight-page signature, the two sheets
have these page pairs when viewed with the text upright:

| Sheet | Front | Back |
| --- | --- | --- |
| Outer | 8 · 1 | 2 · 7 |
| Inner | 6 · 3 | 4 · 5 |

## Output files

Each signature gets its own print PDF, or a pair of files for manual duplex.
Single booklet and perfect binding produce combined output instead.

| File | Contents |
| --- | --- |
| `lage-001-duplex.pdf` | Alternating fronts and backs for signature 1. |
| `lage-001-vorderseiten.pdf` | Fronts only, for manual duplex. |
| `lage-001-rueckseiten.pdf` | Backs only, for manual duplex. |
| `druckplan.json` | Source page numbers, blank-page positions and export settings. |
| `Druckhinweise.txt` | Printing instructions for the selected settings, in German. |

The default output folder is `<PDF-name>-files`. Existing folders are not
overwritten; the interface suggests another name if the default is taken.
Page numbers in the print plan refer to the source PDF starting at 1, not to
printed page numbers. `null` in the JSON plan means a blank book page.

## Limitations

- Layouts assume left-bound books read from left to right, with one fold per sheet.
- Paper thickness and creep are not compensated for. Check your printer's
  printable margins and duplex alignment with a test print.
- The output is intended for static page content. Interactive forms,
  annotations, links, bookmarks and digital signatures are not preserved.
  Export completed forms as a static PDF first.
- Password-protected PDFs require their password. The exported print copies
  are unencrypted; the password is not saved in the print plan.

## Python usage

You can also use the page planner and PDF exporter from Python:

```python
from bookbinding import make_plan
from bookbinding.pdf import impose_pdf

plan = make_plan(35, sheets_per_signature=4)
print([signature.sheet_count for signature in plan.signatures])  # [4, 4, 1]

result = impose_pdf(
    "book.pdf",
    "book-print",  # A new directory.
    sheets_per_signature=4,
    paper_size="A4",
)
print(result.files)
```

## Development

```sh
uv sync --locked --group dev
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
```

GUI tests require a desktop session and must be enabled explicitly:

```sh
BOOKBINDING_GUI_TESTS=1 uv run --locked pytest tests/test_gui.py
```

Translations live in `src/bookbinding/i18n.py`; selected options use
language-independent IDs. PDF processing uses pypdf. PyMuPDF is used only
for testing and independent rendering checks.
See [verification results](docs/verification.md) for the checks performed
and what remains untested.

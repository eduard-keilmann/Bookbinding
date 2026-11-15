# Verification

This document records completed checks and their limits. Translating this
record does not constitute a new test run.

## Environment

The checks below used:

- macOS, Python 3.11.0 and Tk 8.6.12
- pypdf 7.1.0 and cryptography 50.0.2
- PyMuPDF 1.28.2 as an independent PDF renderer
- pytest 9.2.0 and Ruff 0.17.5
- An isolated uv project environment; the existing Python environment was not modified

## Checks on 14 November 2026

All automated test documents were synthetic. Personal book PDFs were not
modified or included as test fixtures.

`BOOKBINDING_GUI_TESTS=1 .venv/bin/pytest --tb=short`:
**103 passed**. These comprised 65 page-planning tests, 30 PDF integration
tests, two tests with real Tk widgets and a background export, and six tests
of desktop integration and the Linux launcher.
The GUI tests ran outside the execution sandbox because Tk requires access
to the macOS desktop session.

`ruff check .` and `ruff format --check .`: passed.

The tests cover:

- The eight-page booklet arrangement: 8–1 / 2–7 / 6–3 / 4–5.
- Recovery of consecutive reading order through simulated folding.
- Every source page appearing exactly once, including a shorter final signature.
- Custom signatures, added blanks, padding and completely blank sheet sides.
- Identical rendered images for corresponding duplex and manual output pages.
- Page rotations of 0°, 90°, 180° and 270°, with offset crop and media boxes.
- Render comparisons between the visible source area and its imposed counterpart.
- Scaling with and without preserved proportions.
- AES-encrypted input, incorrect passwords and unencrypted print output.
- Protection of existing files and cleanup after an error in a later signature.

An initial pypdf 7 incompatibility was corrected by applying transformations
to pages owned by a separate writer. The PDF tests failed with
`DeprecationError` before the correction and passed afterwards.
The assertions were not weakened to obtain a pass.

All four pages of the included test booklet's print PDF were rendered to PNG
and inspected visually. Page numbers, borders, orientation and spacing were
present without clipping. The main controls were also checked for overflow
in a real Tk session.

## Language switch: 15 November 2026

The interface starts in English and switches between English and German.
The full suite ran with real macOS Tk widgets: **107 tests passed**.
After a final wording correction, the six GUI and translation tests were
run again and passed. They cover preserved inputs and selections, translated
validation messages, and language changes during and after an export.
The main test for the new feature was first run against the previous code
and failed because that version started in German.

Ruff and formatting checks passed. The new `i18n.py` and `errors.py` modules
passed mypy checks. A full type check of the existing application was not
performed. No dependencies were added.

Code standards and requirements were reviewed separately. Findings about
option mappings, type annotations and count wording were addressed.
The main controls were checked for overflow in both languages in a real
Tk session. No screenshot test of the interface was performed.

## Limitations

- The application was tested on macOS. Linux folder-opening commands were
  tested with simulated program availability. The POSIX launcher was tested
  with a test interpreter, a different working directory and a project path
  containing spaces. A full Linux desktop test has not been performed.
  Windows is not supported.
- No physical test print was performed as part of these checks. Paper paths,
  duplex settings and manual refeeding must be checked on the actual printer.
- Widget states, layout bounds and a real GUI export were tested automatically;
  the complete Tk interface has no visual screenshot test.
- The tests do not cover every malformed PDF, printer driver or large
  image-heavy document. Interactive forms and annotations are outside the
  supported print-content model.
- PyMuPDF emitted five deprecation warnings from its SWIG bindings. The tests
  passed, and the warnings were not filtered out.

The layout assumes left-bound books read from left to right, with four book
pages per folded sheet. Paper thickness is not compensated for.

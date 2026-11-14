"""Small German desktop interface; PDF work runs outside the Tk event loop."""

import re
import shutil
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from tkinter import filedialog, messagebox, simpledialog, ttk

from pypdf.errors import FileNotDecryptedError, PyPdfError

from .layout import make_plan
from .pdf import PAPER_SIZES, ExportResult, PdfInfo, impose_pdf, inspect_pdf

MODES = {
    "Lagen mit fester Obergrenze": "signatures",
    "Eigene Lagenfolge": "signatures",
    "Automatik": "automatic",
    "Einzelheft": "booklet",
    "Klebebindung": "perfect-bound",
}
BOOK_FORMATS = {
    "Volle halbe Bogenfläche": None,
    "120 × 180 mm": (120, 180),
    "150 × 205 mm": (150, 205),
    "Eigene Maße": None,
}


class BookbindingApp:
    """Own UI state and translate user choices into library parameters."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.source: Path | None = None
        self.password: str | None = None
        self.info: PdfInfo | None = None
        self.last_output: Path | None = None
        self.busy = False
        self.results: Queue[ExportResult | Exception] = Queue()

        self.file_name = tk.StringVar(value="Noch keine PDF ausgewählt")
        self.file_info = tk.StringVar(value="")
        self.destination = tk.StringVar()
        self.mode = tk.StringVar(value=next(iter(MODES)))
        self.sheets = tk.StringVar(value="8")
        self.custom = tk.StringVar(value="4, 4, 3")
        self.flyleaf = tk.BooleanVar(value=False)
        self.paper = tk.StringVar(value="A4")
        self.book_format = tk.StringVar(value=next(iter(BOOK_FORMATS)))
        self.book_width = tk.StringVar()
        self.book_height = tk.StringVar()
        self.proportions = tk.BooleanVar(value=True)
        self.duplex = tk.BooleanVar(value=True)
        self.rotate_backs = tk.BooleanVar(value=True)
        self.preview = tk.StringVar(value="PDF öffnen, um die Lagen zu berechnen.")
        self.status = tk.StringVar(value="Bereit")

        root.title("Bookbinding · PDF-Lagen für die Fadenheftung")
        root.minsize(780, 660)
        root.protocol("WM_DELETE_WINDOW", self._close)
        outer = ttk.Frame(root, padding=18)
        outer.grid(sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        ttk.Label(
            outer, text="PDF für die Buchbindung vorbereiten", font=("TkDefaultFont", 18, "bold")
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))
        source_frame = ttk.LabelFrame(outer, text="Quelldatei", padding=10)
        source_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        source_frame.columnconfigure(0, weight=1)
        ttk.Label(source_frame, textvariable=self.file_name, wraplength=570).grid(
            row=0, column=0, sticky="w"
        )
        self.open_button = ttk.Button(source_frame, text="PDF öffnen …", command=self._choose_pdf)
        self.open_button.grid(row=0, column=1, padx=(12, 0))
        ttk.Label(source_frame, textvariable=self.file_info).grid(row=1, column=0, sticky="w")

        notebook = ttk.Notebook(outer)
        notebook.grid(row=2, column=0, sticky="nsew")
        layout = ttk.Frame(notebook, padding=12)
        format_frame = ttk.Frame(notebook, padding=12)
        notebook.add(layout, text="Lagen und Druck")
        notebook.add(format_frame, text="Papier und Buchformat")
        layout.columnconfigure(1, weight=1)
        format_frame.columnconfigure(1, weight=1)

        ttk.Label(layout, text="Bindeverfahren").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Combobox(
            layout, textvariable=self.mode, values=list(MODES), state="readonly", width=38
        ).grid(row=0, column=1, sticky="ew", padx=(12, 0), pady=5)
        ttk.Label(layout, text="Bögen je Lage (max.)").grid(row=1, column=0, sticky="w", pady=5)
        self.sheet_input = ttk.Spinbox(layout, from_=1, to=64, textvariable=self.sheets, width=8)
        self.sheet_input.grid(row=1, column=1, sticky="w", padx=(12, 0), pady=5)
        ttk.Label(layout, text="Eigene Lagenfolge").grid(row=2, column=0, sticky="w", pady=5)
        self.custom_input = ttk.Entry(layout, textvariable=self.custom)
        self.custom_input.grid(row=2, column=1, sticky="ew", padx=(12, 0), pady=5)
        ttk.Label(layout, text="1 Bogen = 4 Buchseiten · z. B. 4, 4, 3 = 16 + 16 + 12 Seiten").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(2, 8)
        )
        ttk.Checkbutton(
            layout, text="Vorsatz: je zwei Leerseiten vorne und hinten", variable=self.flyleaf
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Separator(layout).grid(row=5, column=0, columnspan=2, sticky="ew", pady=8)
        ttk.Checkbutton(
            layout, text="Automatischer Duplexdruck (sonst getrennte Dateien)", variable=self.duplex
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Checkbutton(layout, text="Rückseiten um 180° drehen", variable=self.rotate_backs).grid(
            row=7, column=0, columnspan=2, sticky="w", pady=4
        )

        ttk.Label(format_frame, text="Druckpapier").grid(row=0, column=0, sticky="w", pady=6)
        papers = ["A4", "A3", "A5", "LETTER", "LEGAL", "TABLOID"]
        papers.extend(sorted(set(PAPER_SIZES) - set(papers)))
        ttk.Combobox(
            format_frame, textvariable=self.paper, values=papers, state="readonly", width=30
        ).grid(row=0, column=1, sticky="ew", padx=(12, 0), pady=6)
        ttk.Label(format_frame, text="Buchseitenformat").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Combobox(
            format_frame, textvariable=self.book_format, values=list(BOOK_FORMATS), state="readonly"
        ).grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=6)
        dimensions = ttk.Frame(format_frame)
        dimensions.grid(row=2, column=1, sticky="w", padx=(12, 0), pady=6)
        self.width_input = ttk.Entry(dimensions, textvariable=self.book_width, width=8)
        self.width_input.grid(row=0, column=0)
        ttk.Label(dimensions, text=" × ").grid(row=0, column=1)
        self.height_input = ttk.Entry(dimensions, textvariable=self.book_height, width=8)
        self.height_input.grid(row=0, column=2)
        ttk.Label(dimensions, text=" mm (Breite × Höhe)").grid(row=0, column=3)
        ttk.Checkbutton(
            format_frame,
            text="Seitenverhältnis erhalten (sonst auf Zielformat strecken)",
            variable=self.proportions,
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=12)
        ttk.Label(
            format_frame,
            text="Buchseiten stehen um 90° gedreht auf dem Bogen.\n"
            "Die volle halbe Bogenfläche ergibt bei A4 ein Buchformat von 148,5 × 210 mm.",
            wraplength=650,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=8)

        preview_frame = ttk.LabelFrame(outer, text="Lagenvorschau", padding=10)
        preview_frame.grid(row=3, column=0, sticky="ew", pady=10)
        ttk.Label(preview_frame, textvariable=self.preview, wraplength=690).grid(
            row=0, column=0, sticky="w"
        )
        target_frame = ttk.LabelFrame(outer, text="Neuer Ausgabeordner", padding=10)
        target_frame.grid(row=4, column=0, sticky="ew")
        target_frame.columnconfigure(0, weight=1)
        ttk.Entry(target_frame, textvariable=self.destination).grid(row=0, column=0, sticky="ew")
        self.target_button = ttk.Button(
            target_frame, text="Ziel wählen …", command=self._choose_target
        )
        self.target_button.grid(row=0, column=1, padx=(12, 0))
        actions = ttk.Frame(outer)
        actions.grid(row=5, column=0, sticky="ew", pady=(12, 4))
        actions.columnconfigure(0, weight=1)
        ttk.Label(actions, textvariable=self.status, wraplength=440).grid(
            row=0, column=0, sticky="w"
        )
        self.folder_button = ttk.Button(
            actions, text="Ausgabe öffnen", command=self._open_output, state="disabled"
        )
        self.folder_button.grid(row=0, column=1, padx=8)
        self.export_button = ttk.Button(
            actions, text="Druck-PDFs erstellen", command=self._start_export, state="disabled"
        )
        self.export_button.grid(row=0, column=2)
        ttk.Label(
            outer,
            text="Druckdialog: 1 PDF-Seite pro Blattseite · tatsächliche Größe · "
            "zuerst Probeheft drucken",
            wraplength=700,
        ).grid(row=6, column=0, sticky="w", pady=(8, 0))

        for variable in (self.mode, self.sheets, self.custom, self.flyleaf, self.book_format):
            variable.trace_add("write", self._refresh_preview)
        self._refresh_preview()

    def _layout_options(self) -> dict:
        mode_label = self.mode.get()
        sizes = None
        if mode_label == "Eigene Lagenfolge":
            text = self.custom.get().strip()
            if not re.fullmatch(r"[0-9]+(?:[\s,;]+[0-9]+)*", text):
                raise ValueError(
                    "Lagenfolge: positive Bogenzahlen durch Komma oder Leerzeichen trennen."
                )
            sizes = [int(number) for number in re.split(r"[\s,;]+", text)]
        try:
            sheets = int(self.sheets.get()) if mode_label == "Lagen mit fester Obergrenze" else 8
        except ValueError as error:
            raise ValueError("Bögen je Lage muss eine positive ganze Zahl sein.") from error
        return {
            "mode": MODES[mode_label],
            "sheets_per_signature": sheets,
            "signature_sizes": sizes,
            "flyleaf": self.flyleaf.get(),
        }

    def _pdf_options(self) -> dict:
        book_size = BOOK_FORMATS[self.book_format.get()]
        if self.book_format.get() == "Eigene Maße":
            try:
                book_size = (
                    float(self.book_width.get().replace(",", ".")),
                    float(self.book_height.get().replace(",", ".")),
                )
            except ValueError as error:
                raise ValueError("Breite und Höhe der Buchseite in mm eingeben.") from error
        return {
            "paper_size": self.paper.get(),
            "book_size_mm": book_size,
            "keep_proportions": self.proportions.get(),
            "duplex": self.duplex.get(),
            "rotate_backs": self.rotate_backs.get(),
        }

    def _refresh_preview(self, *_: str) -> None:
        self.sheet_input.configure(
            state="normal" if self.mode.get() == "Lagen mit fester Obergrenze" else "disabled"
        )
        self.custom_input.configure(
            state="normal" if self.mode.get() == "Eigene Lagenfolge" else "disabled"
        )
        dimension_state = "normal" if self.book_format.get() == "Eigene Maße" else "disabled"
        self.width_input.configure(state=dimension_state)
        self.height_input.configure(state=dimension_state)
        if self.info is None:
            return
        try:
            plan = make_plan(self.info.page_count, **self._layout_options())
        except ValueError as error:
            self.preview.set(str(error))
            self.export_button.configure(state="disabled")
            return
        sizes = ", ".join(str(signature.sheet_count) for signature in plan.signatures)
        if len(sizes) > 180:
            sizes = sizes[:177] + "…"
        self.preview.set(
            f"{self.info.page_count} Quellseiten → {plan.sheet_count} Bögen · "
            f"{len(plan.signatures)} Lagen · {plan.blank_page_count} zusätzliche Leerseiten\n"
            f"Bögen je Lage: {sizes}"
        )
        self.export_button.configure(state="disabled" if self.busy else "normal")

    def _unused_destination(self, parent: Path) -> Path:
        name = f"{self.source.stem}-files" if self.source else "bookbinding-files"
        path = parent / name
        index = 2
        while path.exists() or path.is_symlink():
            path = parent / f"{name}-{index}"
            index += 1
        return path

    def _choose_pdf(self) -> None:
        selected = filedialog.askopenfilename(
            parent=self.root, title="Quell-PDF öffnen", filetypes=[("PDF-Dateien", "*.pdf")]
        )
        if selected:
            self.load_pdf(Path(selected))

    def load_pdf(self, source: Path) -> None:
        """Load metadata before changing the current selection; prompt for passwords."""
        password = None
        while True:
            try:
                info = inspect_pdf(source, password=password)
            except FileNotDecryptedError:
                password = simpledialog.askstring(
                    "PDF-Passwort",
                    "Die PDF benötigt ein gültiges Passwort:",
                    parent=self.root,
                    show="*",
                )
                if password is None:
                    return
                continue
            except (OSError, ValueError, PyPdfError) as error:
                messagebox.showerror(
                    "PDF konnte nicht geöffnet werden", str(error), parent=self.root
                )
                return
            break
        self.source, self.password, self.info = source, password, info
        self.file_name.set(source.name)
        self.file_info.set(
            f"{info.page_count} Seiten · erste Seite {info.width_mm:.1f} × {info.height_mm:.1f} mm"
        )
        self.destination.set(str(self._unused_destination(source.parent)))
        self.status.set("PDF geladen")
        self._refresh_preview()

    def _choose_target(self) -> None:
        selected = filedialog.askdirectory(
            parent=self.root, title="Übergeordneten Zielordner wählen"
        )
        if selected:
            self.destination.set(str(self._unused_destination(Path(selected))))

    def _start_export(self) -> None:
        if self.busy or self.source is None or self.info is None:
            return
        try:
            layout_options = self._layout_options()
            make_plan(self.info.page_count, **layout_options)
            options = {**layout_options, **self._pdf_options(), "password": self.password}
            if not self.destination.get().strip():
                raise ValueError("Einen neuen Ausgabeordner angeben.")
        except ValueError as error:
            messagebox.showerror("Einstellungen prüfen", str(error), parent=self.root)
            return
        self.busy = True
        self.export_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.target_button.configure(state="disabled")
        self.status.set("Druck-PDFs werden erstellt …")
        Thread(
            target=self._export_worker,
            args=(self.source, Path(self.destination.get()), options),
            daemon=True,
        ).start()
        self.root.after(100, self._poll_export)

    def _export_worker(self, source: Path, destination: Path, options: dict) -> None:
        try:
            result = impose_pdf(source, destination, **options)
        except Exception as error:
            # UI boundary: every worker failure must restore the main-thread UI.
            self.results.put(error)
        else:
            self.results.put(result)

    def _poll_export(self) -> None:
        try:
            result = self.results.get_nowait()
        except Empty:
            self.root.after(100, self._poll_export)
            return
        self.busy = False
        self.open_button.configure(state="normal")
        self.target_button.configure(state="normal")
        self._refresh_preview()
        if isinstance(result, Exception):
            self.status.set("Export fehlgeschlagen")
            messagebox.showerror("Export fehlgeschlagen", str(result), parent=self.root)
        else:
            self.last_output = result.output_directory
            self.folder_button.configure(state="normal")
            self.status.set(f"Fertig: {len(result.files)} Druck-PDFs. Ausgabeordner öffnen.")

    def _open_output(self) -> None:
        if self.last_output is None:
            return
        if sys.platform == "darwin":
            command = ["open"]
        elif shutil.which("xdg-open"):
            command = ["xdg-open"]
        elif shutil.which("gio"):
            command = ["gio", "open"]
        else:
            messagebox.showerror(
                "Ordner öffnen",
                f"Kein Ordneröffner gefunden (xdg-open oder gio).\nAusgabe: {self.last_output}",
                parent=self.root,
            )
            return
        try:
            subprocess.Popen([*command, str(self.last_output)])
        except OSError as error:
            messagebox.showerror("Ordner öffnen", str(error), parent=self.root)

    def _close(self) -> None:
        if self.busy:
            self.status.set("Export läuft noch. Das Fenster danach schließen.")
        else:
            self.root.destroy()


def main() -> None:
    """Start the desktop application without a command-line interface."""
    root = tk.Tk()
    BookbindingApp(root)
    root.mainloop()

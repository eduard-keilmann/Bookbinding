"""Bilingual desktop interface; PDF work runs outside the Tk event loop."""

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

from .errors import InputError, UserMessageError
from .i18n import Translator
from .layout import make_plan
from .pdf import PAPER_SIZES, ExportResult, PdfInfo, impose_pdf, inspect_pdf

MODES = {
    "fixed": ("Lagen mit fester Obergrenze", "signatures"),
    "custom": ("Eigene Lagenfolge", "signatures"),
    "automatic": ("Automatik", "automatic"),
    "booklet": ("Einzelheft", "booklet"),
    "perfect-bound": ("Klebebindung", "perfect-bound"),
}
BOOK_FORMATS = {
    "full": ("Volle halbe Bogenfläche", None),
    "small": ("120 × 180 mm", (120, 180)),
    "large": ("150 × 205 mm", (150, 205)),
    "custom": ("Eigene Maße", None),
}


class BookbindingApp:
    """Own UI state and translate user choices into library parameters."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.translator = Translator()
        self.tr = self.translator.text
        self._texts = {}
        self._frames = []
        self._status_message = "Bereit"
        self._status_values = {}
        self.source: Path | None = None
        self.password: str | None = None
        self.info: PdfInfo | None = None
        self.last_output: Path | None = None
        self.busy = False
        self.about_window: tk.Toplevel | None = None
        self._about_image: tk.PhotoImage | None = None
        self.results: Queue[ExportResult | Exception] = Queue()

        self.file_name = tk.StringVar(value=self.tr("Noch keine PDF ausgewählt"))
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
        self.preview = tk.StringVar(value=self.tr("PDF öffnen, um die Lagen zu berechnen."))
        self.status = tk.StringVar(value=self.tr("Bereit"))

        root.title(self.tr("Bookbinding · PDF-Lagen für die Fadenheftung"))
        root.minsize(780, 660)
        root.protocol("WM_DELETE_WINDOW", self._close)
        self.menu_bar = tk.Menu(root, tearoff=False)
        # The special name lets macOS recognize its native Help menu.
        self.help_menu = tk.Menu(self.menu_bar, name="help", tearoff=False)
        self.help_menu.add_command(command=self._show_about)
        self.menu_bar.add_cascade(menu=self.help_menu)
        root.configure(menu=self.menu_bar)
        outer = ttk.Frame(root, padding=18)
        outer.grid(sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        ttk.Label(
            outer,
            textvariable=self._text("PDF für die Buchbindung vorbereiten"),
            font=("TkDefaultFont", 18, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))
        source_frame = self._frame(outer, "Quelldatei")
        source_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        source_frame.columnconfigure(0, weight=1)
        ttk.Label(source_frame, textvariable=self.file_name, wraplength=570).grid(
            row=0, column=0, sticky="w"
        )
        self.open_button = ttk.Button(
            source_frame, textvariable=self._text("PDF öffnen …"), command=self._choose_pdf
        )
        self.open_button.grid(row=0, column=1, padx=(12, 0))
        ttk.Label(source_frame, textvariable=self.file_info).grid(row=1, column=0, sticky="w")

        self.notebook = notebook = ttk.Notebook(outer)
        notebook.grid(row=2, column=0, sticky="nsew")
        layout = ttk.Frame(notebook, padding=12)
        format_frame = ttk.Frame(notebook, padding=12)
        notebook.add(layout, text="Lagen und Druck")
        notebook.add(format_frame, text="Papier und Buchformat")
        layout.columnconfigure(1, weight=1)
        format_frame.columnconfigure(1, weight=1)

        ttk.Label(layout, textvariable=self._text("Bindeverfahren")).grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.mode_box = ttk.Combobox(layout, state="readonly", width=38)
        self.mode_box.grid(row=0, column=1, sticky="ew", padx=(12, 0), pady=5)
        self.mode_box.bind(
            "<<ComboboxSelected>>",
            lambda event: self.mode.set(tuple(MODES)[self.mode_box.current()]),
        )
        ttk.Label(layout, textvariable=self._text("Bögen je Lage (max.)")).grid(
            row=1, column=0, sticky="w", pady=5
        )
        self.sheet_input = ttk.Spinbox(layout, from_=1, to=64, textvariable=self.sheets, width=8)
        self.sheet_input.grid(row=1, column=1, sticky="w", padx=(12, 0), pady=5)
        ttk.Label(layout, textvariable=self._text("Eigene Lagenfolge")).grid(
            row=2, column=0, sticky="w", pady=5
        )
        self.custom_input = ttk.Entry(layout, textvariable=self.custom)
        self.custom_input.grid(row=2, column=1, sticky="ew", padx=(12, 0), pady=5)
        ttk.Label(
            layout,
            textvariable=self._text("1 Bogen = 4 Buchseiten · z. B. 4, 4, 3 = 16 + 16 + 12 Seiten"),
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(2, 8))
        ttk.Checkbutton(
            layout,
            textvariable=self._text("Vorsatz: je zwei Leerseiten vorne und hinten"),
            variable=self.flyleaf,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Separator(layout).grid(row=5, column=0, columnspan=2, sticky="ew", pady=8)
        ttk.Checkbutton(
            layout,
            textvariable=self._text("Automatischer Duplexdruck (sonst getrennte Dateien)"),
            variable=self.duplex,
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Checkbutton(
            layout, textvariable=self._text("Rückseiten um 180° drehen"), variable=self.rotate_backs
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=4)

        ttk.Label(format_frame, textvariable=self._text("Druckpapier")).grid(
            row=0, column=0, sticky="w", pady=6
        )
        papers = ["A4", "A3", "A5", "LETTER", "LEGAL", "TABLOID"]
        papers.extend(sorted(set(PAPER_SIZES) - set(papers)))
        ttk.Combobox(
            format_frame, textvariable=self.paper, values=papers, state="readonly", width=30
        ).grid(row=0, column=1, sticky="ew", padx=(12, 0), pady=6)
        ttk.Label(format_frame, textvariable=self._text("Buchseitenformat")).grid(
            row=1, column=0, sticky="w", pady=6
        )
        self.format_box = ttk.Combobox(format_frame, state="readonly")
        self.format_box.grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=6)
        self.format_box.bind(
            "<<ComboboxSelected>>",
            lambda event: self.book_format.set(tuple(BOOK_FORMATS)[self.format_box.current()]),
        )
        dimensions = ttk.Frame(format_frame)
        dimensions.grid(row=2, column=1, sticky="w", padx=(12, 0), pady=6)
        self.width_input = ttk.Entry(dimensions, textvariable=self.book_width, width=8)
        self.width_input.grid(row=0, column=0)
        ttk.Label(dimensions, textvariable=self._text(" × ")).grid(row=0, column=1)
        self.height_input = ttk.Entry(dimensions, textvariable=self.book_height, width=8)
        self.height_input.grid(row=0, column=2)
        ttk.Label(dimensions, textvariable=self._text(" mm (Breite × Höhe)")).grid(row=0, column=3)
        ttk.Checkbutton(
            format_frame,
            textvariable=self._text("Seitenverhältnis erhalten (sonst auf Zielformat strecken)"),
            variable=self.proportions,
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=12)
        ttk.Label(
            format_frame,
            textvariable=self._text(
                "Buchseiten stehen um 90° gedreht auf dem Bogen.\nDie volle "
                "halbe Bogenfläche ergibt bei A4 ein Buchformat von 148,5 × "
                "210 mm."
            ),
            wraplength=650,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=8)

        preview_frame = self._frame(outer, "Lagenvorschau")
        preview_frame.grid(row=3, column=0, sticky="ew", pady=10)
        ttk.Label(preview_frame, textvariable=self.preview, wraplength=690).grid(
            row=0, column=0, sticky="w"
        )
        target_frame = self._frame(outer, "Neuer Ausgabeordner")
        target_frame.grid(row=4, column=0, sticky="ew")
        target_frame.columnconfigure(0, weight=1)
        ttk.Entry(target_frame, textvariable=self.destination).grid(row=0, column=0, sticky="ew")
        self.target_button = ttk.Button(
            target_frame, textvariable=self._text("Ziel wählen …"), command=self._choose_target
        )
        self.target_button.grid(row=0, column=1, padx=(12, 0))
        actions = ttk.Frame(outer)
        actions.grid(row=5, column=0, sticky="ew", pady=(12, 4))
        actions.columnconfigure(0, weight=1)
        ttk.Label(actions, textvariable=self.status, wraplength=440).grid(
            row=0, column=0, sticky="w"
        )
        self.folder_button = ttk.Button(
            actions,
            textvariable=self._text("Ausgabe öffnen"),
            command=self._open_output,
            state="disabled",
        )
        self.folder_button.grid(row=0, column=1, padx=8)
        self.export_button = ttk.Button(
            actions,
            textvariable=self._text("Druck-PDFs erstellen"),
            command=self._start_export,
            state="disabled",
        )
        self.export_button.grid(row=0, column=2)
        ttk.Label(
            outer,
            textvariable=self._text(
                "Druckdialog: 1 PDF-Seite pro Blattseite · tatsächliche "
                "Größe · zuerst Probeheft drucken"
            ),
            wraplength=700,
        ).grid(row=6, column=0, sticky="w", pady=(8, 0))

        self.language_button = ttk.Button(outer, command=self.toggle_language)
        self.language_button.grid(row=7, column=0, sticky="e", pady=(8, 0))
        self._apply_language()
        for variable in (self.mode, self.sheets, self.custom, self.flyleaf, self.book_format):
            variable.trace_add("write", self._refresh_preview)
        self._refresh_preview()

    def _text(self, message: str) -> tk.StringVar:
        # Retain text bindings so switching language does not recreate widgets.
        variable = tk.StringVar(value=self.tr(message))
        self._texts.setdefault(message, []).append(variable)
        return variable

    def _frame(self, parent, message: str) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text=self.tr(message), padding=10)
        self._frames.append((frame, message))
        return frame

    def _show_about(self) -> None:
        if self.about_window is not None and self.about_window.winfo_exists():
            self.about_window.lift()
            return
        if self._about_image is None:
            image_path = Path(__file__).parent / "assets" / "bookbinding-about.png"
            # Load the PNG bytes explicitly; native file loading can substitute an app icon.
            # Use the antialiased display-size asset; Tk subsampling produces jagged edges.
            self._about_image = tk.PhotoImage(
                master=self.root, data=image_path.read_bytes(), format="png"
            )

        dialog = tk.Toplevel(self.root)
        self.about_window = dialog
        dialog.title(self.tr("Über Bookbinding"))
        dialog.transient(self.root)
        dialog.resizable(False, False)
        content = ttk.Frame(dialog, padding=24)
        content.grid()
        ttk.Label(content, image=self._about_image).grid(row=0, column=0, pady=(0, 12))
        ttk.Label(
            content,
            name="credit",
            text=self.tr("Bookbinding\nEntwickelt von {author}", author="Eduard Keilmann"),
            justify="center",
        ).grid(row=1, column=0, pady=(0, 18))
        close = ttk.Button(content, name="close", text=self.tr("Schließen"), command=dialog.destroy)
        close.grid(row=2, column=0)
        dialog.bind("<Escape>", lambda event: dialog.destroy())
        dialog.bind("<Return>", lambda event: dialog.destroy())
        close.focus_set()

    def toggle_language(self) -> None:
        self.translator.language = "de" if self.translator.language == "en" else "en"
        self._apply_language()

    def _apply_language(self) -> None:
        for message, variables in self._texts.items():
            for variable in variables:
                variable.set(self.tr(message))
        for frame, message in self._frames:
            frame.configure(text=self.tr(message))
        self.root.title(self.tr("Bookbinding · PDF-Lagen für die Fadenheftung"))
        self.menu_bar.entryconfigure(0, label=self.tr("Hilfe"))
        self.help_menu.entryconfigure(0, label=self.tr("Über Bookbinding"))
        self.notebook.tab(0, text=self.tr("Lagen und Druck"))
        self.notebook.tab(1, text=self.tr("Papier und Buchformat"))
        self.language_button.configure(
            text="Deutsch" if self.translator.language == "en" else "English"
        )
        if self.source is None:
            self.file_name.set(self.tr("Noch keine PDF ausgewählt"))
        else:
            self._update_file_info()
        self.status.set(self.tr(self._status_message, **self._status_values))
        self._refresh_preview()

    def _set_status(self, message: str, **values) -> None:
        self._status_message, self._status_values = message, values
        self.status.set(self.tr(message, **values))

    def _error_text(self, error: Exception) -> str:
        if isinstance(error, UserMessageError):
            return self.tr(error.message, **error.values)
        return str(error)

    def _update_file_info(self) -> None:
        info = self.info
        self.file_info.set(
            self.tr(
                "{pages} Seiten · erste Seite {width:.1f} × {height:.1f} mm",
                pages=info.page_count,
                width=info.width_mm,
                height=info.height_mm,
            )
        )

    def _layout_options(self) -> dict:
        mode_label = self.mode.get()
        sizes = None
        if mode_label == "custom":
            text = self.custom.get().strip()
            if not re.fullmatch(r"[0-9]+(?:[\s,;]+[0-9]+)*", text):
                raise InputError(
                    "Lagenfolge: positive Bogenzahlen durch Komma oder Leerzeichen trennen."
                )
            sizes = [int(number) for number in re.split(r"[\s,;]+", text)]
        try:
            sheets = int(self.sheets.get()) if mode_label == "fixed" else 8
        except ValueError as error:
            raise InputError("Bögen je Lage muss eine positive ganze Zahl sein.") from error
        return {
            "mode": MODES[mode_label][1],
            "sheets_per_signature": sheets,
            "signature_sizes": sizes,
            "flyleaf": self.flyleaf.get(),
        }

    def _pdf_options(self) -> dict:
        book_size = BOOK_FORMATS[self.book_format.get()][1]
        if self.book_format.get() == "custom":
            try:
                book_size = (
                    float(self.book_width.get().replace(",", ".")),
                    float(self.book_height.get().replace(",", ".")),
                )
            except ValueError as error:
                raise InputError("Breite und Höhe der Buchseite in mm eingeben.") from error
        return {
            "paper_size": self.paper.get(),
            "book_size_mm": book_size,
            "keep_proportions": self.proportions.get(),
            "duplex": self.duplex.get(),
            "rotate_backs": self.rotate_backs.get(),
        }

    def _refresh_preview(self, *_: str) -> None:
        self.mode_box.configure(values=[self.tr(label) for label, _ in MODES.values()])
        self.mode_box.current(tuple(MODES).index(self.mode.get()))
        self.format_box.configure(values=[self.tr(label) for label, _ in BOOK_FORMATS.values()])
        self.format_box.current(tuple(BOOK_FORMATS).index(self.book_format.get()))
        self.sheet_input.configure(state="normal" if self.mode.get() == "fixed" else "disabled")
        self.custom_input.configure(state="normal" if self.mode.get() == "custom" else "disabled")
        dimension_state = "normal" if self.book_format.get() == "custom" else "disabled"
        self.width_input.configure(state=dimension_state)
        self.height_input.configure(state=dimension_state)
        if self.info is None:
            self.preview.set(self.tr("PDF öffnen, um die Lagen zu berechnen."))
            return
        try:
            plan = make_plan(self.info.page_count, **self._layout_options())
        except ValueError as error:
            self.preview.set(self._error_text(error))
            self.export_button.configure(state="disabled")
            return
        sizes = ", ".join(str(signature.sheet_count) for signature in plan.signatures)
        if len(sizes) > 180:
            sizes = sizes[:177] + "…"
        self.preview.set(
            self.tr(
                (
                    "Quellseiten: {pages} · Bögen: {sheets} · Lagen: {signatures} · "
                    "Zusätzliche Leerseiten: {blanks}\nBögen je Lage: {sizes}"
                ),
                pages=self.info.page_count,
                sheets=plan.sheet_count,
                signatures=len(plan.signatures),
                blanks=plan.blank_page_count,
                sizes=sizes,
            )
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
            parent=self.root,
            title=self.tr("Quell-PDF öffnen"),
            filetypes=[(self.tr("PDF-Dateien"), "*.pdf")],
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
                    self.tr("PDF-Passwort"),
                    self.tr("Die PDF benötigt ein gültiges Passwort:"),
                    parent=self.root,
                    show="*",
                )
                if password is None:
                    return
                continue
            except (OSError, ValueError, PyPdfError) as error:
                messagebox.showerror(
                    self.tr("PDF konnte nicht geöffnet werden"),
                    self._error_text(error),
                    parent=self.root,
                )
                return
            break
        self.source, self.password, self.info = source, password, info
        self.file_name.set(source.name)
        self._update_file_info()
        self.destination.set(str(self._unused_destination(source.parent)))
        self._set_status("PDF geladen")
        self._refresh_preview()

    def _choose_target(self) -> None:
        selected = filedialog.askdirectory(
            parent=self.root, title=self.tr("Übergeordneten Zielordner wählen")
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
                raise InputError("Einen neuen Ausgabeordner angeben.")
        except ValueError as error:
            messagebox.showerror(
                self.tr("Einstellungen prüfen"), self._error_text(error), parent=self.root
            )
            return
        self.busy = True
        self.export_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.target_button.configure(state="disabled")
        self._set_status("Druck-PDFs werden erstellt …")
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
            self._set_status("Export fehlgeschlagen")
            messagebox.showerror(
                self.tr("Export fehlgeschlagen"), self._error_text(result), parent=self.root
            )
        else:
            self.last_output = result.output_directory
            self.folder_button.configure(state="normal")
            self._set_status(
                "Druck-PDFs erstellt: {count}. Ausgabeordner öffnen.", count=len(result.files)
            )

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
                self.tr("Ordner öffnen"),
                self.tr(
                    "Kein Ordneröffner gefunden (xdg-open oder gio).\nAusgabe: {path}",
                    path=self.last_output,
                ),
                parent=self.root,
            )
            return
        try:
            subprocess.Popen([*command, str(self.last_output)])
        except OSError as error:
            messagebox.showerror(
                self.tr("Ordner öffnen"), self._error_text(error), parent=self.root
            )

    def _close(self) -> None:
        if self.busy:
            self._set_status("Export läuft noch. Das Fenster danach schließen.")
        else:
            self.root.destroy()


def main() -> None:
    """Start the desktop application without a command-line interface."""
    root = tk.Tk()
    BookbindingApp(root)
    root.mainloop()

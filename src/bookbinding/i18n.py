"""GUI translations. German messages are catalog IDs; values stay outside the text.

Add or edit each English translation here. German uses the message itself.
Unknown messages fail immediately so missing translations cannot go unnoticed.
"""

ENGLISH = {
    "Hilfe": "Help",
    "Über Bookbinding": "About Bookbinding",
    "Bookbinding\nEntwickelt von {author}": "Bookbinding\nCreated by {author}",
    ("Bookbinding · PDF-Lagen für die Fadenheftung"): (
        "Bookbinding · PDF signatures for sewn binding"
    ),
    ("PDF für die Buchbindung vorbereiten"): ("Prepare a PDF for bookbinding"),
    ("Noch keine PDF ausgewählt"): ("No PDF selected"),
    ("PDF öffnen, um die Lagen zu berechnen."): ("Open a PDF to calculate the signatures."),
    ("Bereit"): ("Ready"),
    ("PDF geladen"): ("PDF loaded"),
    ("Quelldatei"): ("Source file"),
    ("PDF öffnen …"): ("Open PDF …"),
    ("Lagen und Druck"): ("Signatures and printing"),
    ("Papier und Buchformat"): ("Paper and book size"),
    ("Bindeverfahren"): ("Binding method"),
    ("Bögen je Lage (max.)"): ("Sheets per signature (max.)"),
    ("Eigene Lagenfolge"): ("Custom signatures"),
    ("Lagen mit fester Obergrenze"): ("Signatures with a sheet limit"),
    ("Automatik"): ("Automatic signatures"),
    ("Einzelheft"): ("Single booklet"),
    ("Klebebindung"): ("Perfect binding"),
    ("1 Bogen = 4 Buchseiten · z. B. 4, 4, 3 = 16 + 16 + 12 Seiten"): (
        "1 sheet = 4 book pages · e.g. 4, 4, 3 = 16 + 16 + 12 pages"
    ),
    ("Vorsatz: je zwei Leerseiten vorne und hinten"): ("Add two blank pages at the front and back"),
    ("Automatischer Duplexdruck (sonst getrennte Dateien)"): (
        "Automatic duplex printing (otherwise separate files)"
    ),
    ("Rückseiten um 180° drehen"): ("Rotate backs by 180°"),
    ("Druckpapier"): ("Paper size"),
    ("Buchseitenformat"): ("Book page size"),
    ("Volle halbe Bogenfläche"): ("Use half the sheet"),
    ("120 × 180 mm"): ("120 × 180 mm"),
    ("150 × 205 mm"): ("150 × 205 mm"),
    ("Eigene Maße"): ("Custom size"),
    (" × "): (" × "),
    (" mm (Breite × Höhe)"): (" mm (width × height)"),
    ("Seitenverhältnis erhalten (sonst auf Zielformat strecken)"): (
        "Keep proportions (otherwise stretch to fit)"
    ),
    (
        "Buchseiten stehen um 90° gedreht auf dem "
        "Bogen.\nDie volle halbe Bogenfläche ergibt "
        "bei A4 ein Buchformat von 148,5 × 210 mm."
    ): (
        "Book pages are rotated 90° on the "
        "sheet.\nHalf an A4 sheet gives a book page "
        "size of 148.5 × 210 mm."
    ),
    ("Lagenvorschau"): ("Signature preview"),
    ("Neuer Ausgabeordner"): ("New output folder"),
    ("Ziel wählen …"): ("Choose location …"),
    ("Ausgabe öffnen"): ("Open output folder"),
    ("Druck-PDFs erstellen"): ("Create print PDFs"),
    ("Druckdialog: 1 PDF-Seite pro Blattseite · tatsächliche Größe · zuerst Probeheft drucken"): (
        "Print settings: 1 PDF page per sheet side · actual size · print a test booklet first"
    ),
    ("Lagenfolge: positive Bogenzahlen durch Komma oder Leerzeichen trennen."): (
        "Enter positive sheet counts separated by commas or spaces."
    ),
    ("Bögen je Lage muss eine positive ganze Zahl sein."): (
        "Sheets per signature must be a positive whole number."
    ),
    ("Breite und Höhe der Buchseite in mm eingeben."): (
        "Enter the book page width and height in mm."
    ),
    ("{pages} Seiten · erste Seite {width:.1f} × {height:.1f} mm"): (
        "{pages} pages · first page {width:.1f} × {height:.1f} mm"
    ),
    ("Quell-PDF öffnen"): ("Open source PDF"),
    ("PDF-Dateien"): ("PDF files"),
    ("Übergeordneten Zielordner wählen"): ("Choose the parent output folder"),
    ("PDF-Passwort"): ("PDF password"),
    ("Die PDF benötigt ein gültiges Passwort:"): ("Enter a valid password for this PDF:"),
    ("PDF konnte nicht geöffnet werden"): ("Could not open PDF"),
    ("Einen neuen Ausgabeordner angeben."): ("Enter a new output folder."),
    ("Einstellungen prüfen"): ("Check settings"),
    ("Druck-PDFs werden erstellt …"): ("Creating print PDFs …"),
    ("Export fehlgeschlagen"): ("Export failed"),
    ("Druck-PDFs erstellt: {count}. Ausgabeordner öffnen."): (
        "Print PDFs created: {count}. Open the output folder."
    ),
    ("Ordner öffnen"): ("Open folder"),
    ("Kein Ordneröffner gefunden (xdg-open oder gio).\nAusgabe: {path}"): (
        "No folder opener found (xdg-open or gio).\nOutput: {path}"
    ),
    ("Export läuft noch. Das Fenster danach schließen."): (
        "Export is still running. Close the window when it finishes."
    ),
    ("Die PDF muss mindestens eine Seite enthalten."): ("The PDF must contain at least one page."),
    ("Unbekanntes Bindeverfahren: {method}"): ("Unknown binding method: {method}"),
    ("Eigene Lagenfolgen sind nur im Lagenmodus möglich."): (
        "Custom sheet counts are only available in signatures mode."
    ),
    ("Die Automatik verwendet eine Vorgabe von acht Bögen."): (
        "Automatic signatures use a target of eight sheets."
    ),
    ("Jede Lage muss eine positive ganze Bogenzahl haben."): (
        "Each signature must have a positive whole number of sheets."
    ),
    (
        "Lagenfolge zu klein: {capacity} Plätze für "
        "{pages} Buchseiten einschließlich Vorsatz "
        "und Auffüllseiten. Es werden keine Seiten "
        "abgeschnitten."
    ): (
        "The signatures are too small: {capacity} "
        "spaces for {pages} book pages, including "
        "added blanks. No pages will be dropped."
    ),
    ("PDF-Seitenboxen müssen endliche Koordinaten haben."): (
        "PDF page boxes must have finite coordinates."
    ),
    ("Die PDF enthält eine leere oder ungültige Seitenbox."): (
        "The PDF contains an empty or invalid page box."
    ),
    ("Die PDF-Seitendrehung muss ein Vielfaches von 90 Grad sein."): (
        "PDF page rotation must be a multiple of 90 degrees."
    ),
    ("Zielordner existiert bereits: {path}"): ("The output folder already exists: {path}"),
    ("Zielordner wurde inzwischen angelegt: {path}"): (
        "The output folder was created during the export: {path}"
    ),
    ("Unbekanntes Papierformat: {paper}"): ("Unknown paper size: {paper}"),
    ("Die PDF enthält keine Seiten."): ("The PDF contains no pages."),
    ("Buchseitenbreite und -höhe müssen positive, endliche Maße sein."): (
        "Book page width and height must be positive, finite values."
    ),
    ("Das Buchseitenformat passt nicht auf einen halben Druckbogen."): (
        "The book page size does not fit on half a sheet."
    ),
    (
        "Quellseiten: {pages} · Bögen: {sheets} · "
        "Lagen: {signatures} · Zusätzliche "
        "Leerseiten: {blanks}\nBögen je Lage: {sizes}"
    ): (
        "Source pages: {pages} · Sheets: {sheets} · "
        "Signatures: {signatures} · Added blanks: "
        "{blanks}\nSheets per signature: {sizes}"
    ),
}


class Translator:
    """Translate complete messages and format their named values."""

    def __init__(self, language: str = "en"):
        self.language = language

    def text(self, message: str, **values: object) -> str:
        if self.language not in ("en", "de"):
            raise ValueError(f"Unsupported language: {self.language}")
        english = ENGLISH[message]
        return (english if self.language == "en" else message).format(**values)

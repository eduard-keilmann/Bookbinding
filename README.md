# Bookbinding

PDF-Seiten für gefaltete Lagen und Fadenheftung ausschießen.
Python-3-Anwendung mit deutscher Desktop-Oberfläche.

## Starten

Unter macOS `Bookbinding starten.command` doppelklicken. Die lokale
Python-Umgebung wird mit uv eingerichtet, falls sie noch fehlt.
Python ab 3.11 mit Tkinter und [uv](https://docs.astral.sh/uv/) werden benötigt.

Alternativ aus diesem Verzeichnis:

```sh
uv sync --locked --no-dev
uv run --locked --no-dev python -m bookbinding
```

Tkinter gehört zur Python-Installation. Auf diesem Mac funktioniert die
vorhandene Python-3.11-Installation mit Tkinter; die Homebrew-Installation
von Python 3.12 hat derzeit kein `_tkinter`. Der macOS-Starter bevorzugt
deshalb die bereits eingerichtete Projektumgebung.

## Begriffe und Einstellungen

Ein **Bogen** ist ein physisches Blatt Papier, beidseitig bedruckt und einmal
gefaltet. Darauf passen **vier Buchseiten**. Mehrere ineinandergesteckte
Bögen bilden eine **Lage** (englisch *signature*).
Vier Bögen je Lage entsprechen somit 16 Buchseiten.

| Verfahren | Verhalten |
| --- | --- |
| Lagen mit fester Obergrenze | Frei wählbare maximale Bogenzahl; die letzte Lage darf kleiner sein. |
| Eigene Lagenfolge | Zum Beispiel `4, 4, 3`: 16, 16 und 12 Buchseiten. Zu große Kapazität wird mit Leerseiten aufgefüllt; zu kleine Kapazität wird abgewiesen. |
| Automatik | Tabelle bis 192 Seiten, danach Verteilung mit acht Bögen als Richtwert. Kurze Dokumente können damit eine große einzelne Lage ergeben. |
| Einzelheft | Das ganze Dokument bildet eine Lage. |
| Klebebindung | Jeder Bogen enthält vier fortlaufende Buchseiten, angeordnet als 4–1 / 2–3. |

Optionale Vorsatzseiten: zwei Leerseiten vorne und zwei hinten.
Die Gesamtzahl der Buchseiten wird auf ein Vielfaches von vier aufgefüllt.
Die Oberfläche zeigt Lagen, Bögen und zusätzliche Leerseiten vor dem Export.

PDF-Buchseiten werden zu zweit auf eine Druckseite gesetzt. Es entsteht ein Hochformat-Druckbogen mit um 90 Grad gedrehten Buchseiten.
Bei aufrecht gelesenem Text stehen beispielsweise auf der Außenseite eines
achtseitigen Hefts links Seite 8 und rechts Seite 1; auf der Rückseite 2 und 7.

Papierformat, gewünschtes Buchseitenformat, proportionale Skalierung oder
Strecken sowie die Drehung der Rückseiten sind einstellbar. Maße sind in mm.
Ein leeres Buchseitenformat nutzt die volle halbe Bogenfläche.
PDF-CropBox, versetzte Seitenboxen und vorhandene Seitendrehungen werden
berücksichtigt. Text und Vektorgrafik bleiben PDF-Inhalte, ohne Rasterung.

## Ausgabe und Drucken

Das Quell-PDF bleibt unverändert. Als Ziel einen **neuen Ordner** angeben;
vorhandene Ziele werden nicht überschrieben. Standard: `<PDF-Name>-files`.
Die Oberfläche wählt bei bereits belegtem Namen einen freien Folgendenamen.

- Duplex: `lage-001-duplex.pdf`, jeweils Vorder- und Rückseite abwechselnd.
- Manuell: `lage-001-vorderseiten.pdf` und `lage-001-rueckseiten.pdf`;
  beide Dateien folgen der Bogenfolge von außen nach innen.
- Beim Einzelheft/Klebebindungsmodus wird eine entsprechende Gesamtdatei
  beziehungsweise ein Paar Dateien ausgegeben.
- `druckplan.json` dokumentiert Buchseitennummern, Leerseiten und Einstellungen.
- `Druckhinweise.txt` enthält die zum gewählten Modus passenden Druckhinweise.

Im Druckdialog **eine PDF-Seite pro Blattseite** und **100 % / tatsächliche
Größe** wählen. Die Seiten sind bereits ausgeschossen: keine zusätzliche
Broschüren- oder Zwei-Seiten-Funktion einschalten.

Bei Hochformat ohne automatische Ausrichtungsänderung passt normalerweise
„lange Kante“ zu aktivierter Rückseitendrehung und „kurze Kante“ zu
deaktivierter Rückseitendrehung. Treiber und manuelles Wiedereinlegen können
abweichen. Zuerst ein nummeriertes Zwei-Bogen-Heft probeweise drucken,
falten und die Lesereihenfolge prüfen. Bei manuellem Duplex hängt die
benötigte Rückseiten-Druckreihenfolge vom Papierweg ab; bei Bedarf im
Druckdialog „umgekehrte Reihenfolge“ für die Rückseitendatei wählen.

Ein synthetisches Acht-Seiten-Probeheft ist enthalten:
[`examples/probeheft.pdf`](examples/probeheft.pdf) ist die Quelldatei,
[`examples/probeheft-druck/lage-001-duplex.pdf`](examples/probeheft-druck/lage-001-duplex.pdf)
die ausgeschossene Version für zwei A4-Bögen mit Rückseitendrehung.
Damit die Orientierung prüfen, bevor ein ganzes Buch gedruckt wird.

## Als Python-Bibliothek

```python
from bookbinding import make_plan
from bookbinding.pdf import impose_pdf

plan = make_plan(35, sheets_per_signature=4)
print([signature.sheet_count for signature in plan.signatures])  # [4, 4, 1]

result = impose_pdf(
    "buch.pdf",
    "buch-druckfertig",  # Must not already exist.
    signature_sizes=[4, 4, 3],
    paper_size="A4",
    duplex=True,
    rotate_backs=True,
)
print(result.files)
```

`None` im Seitenplan bedeutet eine leere Buchseite. Originalseiten werden
ab 1 gezählt, unabhängig von gedruckten Seitenzahlen oder PDF-Seitenlabels.
Passwortgeschützte PDFs können mit ihrem Passwort geöffnet werden;
Ausgabedateien sind unverschlüsselte Druckkopien. Passwörter werden nicht
in den Druckplan geschrieben. Interaktive Formulare, Kommentare, Links,
Lesezeichen und digitale Signaturen sind kein Erhaltungsziel: übernommen
werden die statischen Seiteninhalte für den Druck. Formularwerte vorab als
statisches PDF exportieren.

PDF-Implementierung nach der offiziellen pypdf-Dokumentation zu
[Transformationen](https://pypdf.readthedocs.io/en/stable/user/cropping-and-transforming.html)
und [Verschlüsselung](https://pypdf.readthedocs.io/en/stable/user/encryption-decryption.html).

## Entwicklung und Prüfung

```sh
uv sync --locked --group dev
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
```

Echte Tk-Tests zusätzlich in einer Desktop-Sitzung aktivieren:

```sh
BOOKBINDING_GUI_TESTS=1 uv run --locked pytest tests/test_gui.py
```

Tests prüfen explizite Ausschießbeispiele, die Lesereihenfolge nach dem Falten,
Seitenvollständigkeit, Lagenkapazität, Leerseiten und Fehlerfälle.
PDF-Integrationstests verwenden nummerierte synthetische Seiten und prüfen
Export, Seitenpositionen, Rotation, Beschnitt, Verschlüsselung und Dateischutz.
PyMuPDF dient ausschließlich der Entwicklung und der unabhängigen Renderprüfung.
Die tatsächliche Papierführung eines Druckers muss am Gerät geprüft werden.
Durchgeführte Prüfungen und Grenzen stehen in [docs/verification.md](docs/verification.md).

Annahmen: links gebundene Bücher mit Leserichtung links nach rechts;
einfach gefaltete Bögen mit vier Buchseiten; keine automatische Kompensation
für Papierdicke oder Bundzuwachs.

# Verifikation

Stand: 14. November 2026. Alle Testdokumente sind synthetisch; es wurden
keine persönlichen Buch-PDFs umgeschrieben oder als Testfixtures übernommen.

## Geprüfte Umgebung

- macOS, Python 3.11.0, Tk 8.6.12
- pypdf 7.1.0, cryptography 50.0.2
- PyMuPDF 1.28.2 als unabhängiger PDF-Renderer
- pytest 9.2.0, Ruff 0.17.5
- Isolierte uv-Projektumgebung, keine Änderung der vorhandenen Python-Umgebung

## Tatsächlich ausgeführte Prüfungen

`BOOKBINDING_GUI_TESTS=1 .venv/bin/pytest --tb=short`:
**103 bestanden**, davon 65 Prüfungen der Seitenplanung, 30 PDF-Integrationstests,
zwei Tests mit echten Tk-Widgets und einem Export im Hintergrundthread sowie
sechs Prüfungen der Plattformintegration und des Linux-Starters.
Tk benötigt Zugriff auf die macOS-Desktop-Sitzung; die GUI-Tests wurden deshalb
außerhalb der Ausführungssandbox ausgeführt.

`ruff check .` und `ruff format --check .`: bestanden.

Die PDF-Tests prüfen unter anderem:

- explizites Acht-Seiten-Heft: 8–1 / 2–7 / 6–3 / 4–5;
- Wiederherstellung der fortlaufenden Lesereihenfolge durch simuliertes Falten;
- genau einmaliges Auftreten jeder Quellseite, einschließlich kurzer letzter Lagen;
- eigene Lagenfolgen, Vorsatzseiten, Auffüllung, vollständig leere Bogenseiten;
- identische Renderbilder der entsprechenden Duplex- und manuellen Teildateien;
- Seitendrehungen von 0°, 90°, 180° und 270° mit versetzten CropBox-/MediaBox-Koordinaten;
- Rendervergleich des sichtbaren Originalausschnitts mit dem ausgeschossenen Ausschnitt;
- Skalierung mit und ohne Erhalt des Seitenverhältnisses;
- AES-verschlüsselte Eingaben, falsche Passwörter und unverschlüsselte Druckausgaben;
- Schutz vorhandener Dateien und vollständiges Aufräumen nach einem späteren Exportfehler.

Die ursprünglich auftretende pypdf-7-Inkompatibilität ist korrigiert:
Transformationen erfolgen auf Seiten eines separaten Writers. Die PDF-Tests
scheiterten vor dieser Korrektur an `DeprecationError` und bestanden danach.
Die Testassertionen wurden dafür nicht abgeschwächt.

Die vier Seiten der mitgelieferten Druckdatei des Probehefts wurden als PNG
gerendert und visuell geprüft: Buchseitennummern, Rahmen, Orientierung und
Abstände sind vorhanden und ohne Abschneiden. Die Fenstermaße und Positionen
der Hauptbedienelemente wurden in einer echten Tk-Sitzung auf Überlauf geprüft.

## Grenzen

- Plattformpriorität: macOS zuerst, Linux danach; Windows wird nicht unterstützt.
  Der macOS-Starter blieb bei der Linux-Ergänzung unverändert. Linux-Ordneröffner
  wurden mit simulierten Programmverfügbarkeiten geprüft; der POSIX-Starter mit
  einem Testinterpreter aus einem anderen Verzeichnis und einem Projektpfad mit
  Leerzeichen. Kein vollständiger Test auf einem echten Linux-Desktop.

- Kein physischer Probeausdruck: Papierweg, Duplex-Treiber und Wiedereinlegen
  müssen am tatsächlichen Drucker geprüft werden.
- Kein visueller Screenshot-Test der gesamten Tk-Oberfläche. Widgetzustände,
  Layoutgrenzen und ein echter GUI-Export wurden automatisiert geprüft.
- Tests decken keine beliebigen defekten PDFs, Druckertreiber oder sehr großen
  Bildbände ab. Interaktive Formulare und Annotationen gehören nicht zum
  unterstützten Druck-Inhaltsmodell.
- PyMuPDF meldet fünf DeprecationWarnings aus seinen SWIG-Bindings. Die Tests
  bestehen; die Hinweise wurden nicht ausgefiltert.

Annahmen: links gebundene Bücher; Leserichtung links nach rechts; vier
Buchseiten pro einmal gefaltetem Bogen; keine Papierdickenkompensation.

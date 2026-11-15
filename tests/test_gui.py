"""Opt-in tests exercise real Tk widgets and the asynchronous export workflow."""

import os
import time
import tkinter as tk

import pytest

from bookbinding.gui import BookbindingApp

pytestmark = [
    pytest.mark.gui,
    pytest.mark.skipif(
        os.environ.get("BOOKBINDING_GUI_TESTS") != "1",
        reason="Requires an explicitly enabled desktop session",
    ),
]


@pytest.fixture
def app():
    root = tk.Tk()
    root.withdraw()
    application = BookbindingApp(root)
    yield application
    root.destroy()


def test_preview_checks_custom_capacity_and_tracks_mode_changes(app, pdf_factory):
    source = pdf_factory(12)
    app.load_pdf(source)
    app.sheets.set("2")
    assert "Signatures: 2" in app.preview.get()
    assert "Sheets per signature: 2, 1" in app.preview.get()
    app.mode.set("custom")
    app.custom.set("1")
    assert "too small" in app.preview.get()
    app.language_button.invoke()
    assert "zu klein" in app.preview.get()
    app.language_button.invoke()
    assert str(app.export_button["state"]) == "disabled"
    app.custom.set("2, 1")
    assert str(app.export_button["state"]) == "normal"
    app.custom.set("-2, 4")
    assert str(app.export_button["state"]) == "disabled"
    app.mode.set("booklet")
    assert "Signatures: 1" in app.preview.get()
    assert str(app.custom_input["state"]) == "disabled"
    assert str(app.export_button["state"]) == "normal"
    assert app.destination.get() == str(source.with_name("input-files"))


def test_real_ui_exports_in_a_worker_and_recovers_ready_state(app, pdf_factory, tmp_path):
    app.load_pdf(pdf_factory(8))
    app.destination.set(str(tmp_path / "gui-output"))
    app.sheets.set("2")
    app._start_export()
    assert app.busy
    app.language_button.invoke()
    assert app.busy
    assert str(app.export_button["state"]) == "disabled"
    app.language_button.invoke()
    deadline = time.monotonic() + 15
    while app.busy and time.monotonic() < deadline:
        app.root.update()
        time.sleep(0.005)
    assert not app.busy, "UI never received the worker result"
    assert app.last_output == tmp_path / "gui-output"
    assert (app.last_output / "lage-001-duplex.pdf").is_file()
    assert "Print PDFs created:" in app.status.get()
    app.language_button.invoke()
    assert "Druck-PDFs erstellt:" in app.status.get()
    assert app.last_output == tmp_path / "gui-output"
    assert str(app.export_button["state"]) == "normal"


def test_language_button_preserves_loaded_pdf_and_custom_settings(app, pdf_factory):
    assert app.open_button["text"] == "Open PDF …"
    app.load_pdf(pdf_factory(12))
    app.mode.set("custom")
    app.custom.set("2, 1")
    app.book_format.set("custom")
    app.book_width.set("120")
    app.book_height.set("180")
    destination = app.destination.get()
    app.language_button.invoke()
    assert app.open_button["text"] == "PDF öffnen …"
    assert "Quellseiten" in app.preview.get()
    assert app.mode.get() == "custom"
    assert app.custom.get() == "2, 1"
    assert app.book_width.get() == "120"
    assert app.destination.get() == destination
    app.language_button.invoke()
    assert app.open_button["text"] == "Open PDF …"
    assert "Source pages:" in app.preview.get()
    assert app.mode.get() == "custom"


def test_about_menu_shows_author_in_both_languages(app, monkeypatch):
    from bookbinding import gui

    shown = []
    monkeypatch.setattr(
        gui.messagebox, "showinfo", lambda title, message, **kwargs: shown.append((title, message))
    )
    assert app.help_menu.entrycget(0, "label") == "About Bookbinding"
    app.help_menu.invoke(0)
    assert shown[-1] == ("About Bookbinding", "Bookbinding\nCreated by Eduard Keilmann")
    app.language_button.invoke()
    assert app.help_menu.entrycget(0, "label") == "Über Bookbinding"
    app.help_menu.invoke(0)
    assert shown[-1] == ("Über Bookbinding", "Bookbinding\nEntwickelt von Eduard Keilmann")

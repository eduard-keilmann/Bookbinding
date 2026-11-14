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
    assert "2 Lagen" in app.preview.get()
    assert "Bögen je Lage: 2, 1" in app.preview.get()
    app.mode.set("Eigene Lagenfolge")
    app.custom.set("1")
    assert "zu klein" in app.preview.get()
    assert str(app.export_button["state"]) == "disabled"
    app.custom.set("2, 1")
    assert str(app.export_button["state"]) == "normal"
    app.custom.set("-2, 4")
    assert str(app.export_button["state"]) == "disabled"
    app.mode.set("Einzelheft")
    assert "1 Lagen" in app.preview.get()
    assert str(app.custom_input["state"]) == "disabled"
    assert str(app.export_button["state"]) == "normal"
    assert app.destination.get() == str(source.with_name("input-files"))


def test_real_ui_exports_in_a_worker_and_recovers_ready_state(app, pdf_factory, tmp_path):
    app.load_pdf(pdf_factory(8))
    app.destination.set(str(tmp_path / "gui-output"))
    app.sheets.set("2")
    app._start_export()
    assert app.busy
    deadline = time.monotonic() + 15
    while app.busy and time.monotonic() < deadline:
        app.root.update()
        time.sleep(0.005)
    assert not app.busy, "UI never received the worker result"
    assert app.last_output == tmp_path / "gui-output"
    assert (app.last_output / "lage-001-duplex.pdf").is_file()
    assert "Fertig:" in app.status.get()
    assert str(app.export_button["state"]) == "normal"

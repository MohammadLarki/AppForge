import appforge.gui as gui


def test_tkinter_instructions_distinguish_system_and_python_dependencies() -> None:
    instructions = gui.tkinter_install_instructions()

    assert "python3-tk" in instructions
    assert "python3.14-tk" in instructions
    assert "not by pip" in instructions


def test_main_reports_missing_tkinter_without_traceback(monkeypatch, capsys) -> None:
    def missing_tkinter():
        raise ModuleNotFoundError("No module named 'tkinter'", name="tkinter")

    monkeypatch.setattr(gui, "_load_desktop_main", missing_tkinter)

    assert gui.main() == 1

    captured = capsys.readouterr()
    assert "python3-tk" in captured.err
    assert "Traceback" not in captured.err


def test_main_does_not_hide_unrelated_import_errors(monkeypatch) -> None:
    def missing_project_module():
        raise ModuleNotFoundError("No module named 'appforge.detector'", name="appforge.detector")

    monkeypatch.setattr(gui, "_load_desktop_main", missing_project_module)

    try:
        gui.main()
    except ModuleNotFoundError as error:
        assert error.name == "appforge.detector"
    else:
        raise AssertionError("An unrelated import error must not be hidden")

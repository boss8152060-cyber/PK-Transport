import pytest


@pytest.fixture
def tab(tk_root, tmp_path, monkeypatch):
    root = tk_root
    monkeypatch.chdir(tmp_path)  # the tab writes .pk_ui_config.json to the cwd
    from tkinter import messagebox
    for name in ("askyesno", "showinfo", "showwarning", "showerror"):
        monkeypatch.setattr(messagebox, name, lambda *a, **k: True)
    from pk_studio.ui.tabs.tab_autolabeler import AutoLabelerTab

    lbl = tmp_path / "ds" / "labels"
    lbl.mkdir(parents=True)
    (lbl / "a.txt").write_text("0 0.5 0.5 0.2 0.2\n1 0.4 0.4 0.1 0.1\n2 0.3 0.3 0.1 0.1\n", encoding="utf-8")
    t = AutoLabelerTab(root)
    t.src_dir = str(tmp_path / "ds")
    t.lbl_dir = str(lbl)
    t.classes = ["Bus", "Car", "Motorcycle"]
    t.class_registry.load(t.classes, sort=False)
    yield t, lbl
    t.destroy()


def test_manager_rename_merge_delete_multi_select(tab, monkeypatch):
    from tkinter import simpledialog
    from pk_studio.ui import class_dialogs
    t, lbl = tab
    dlg = class_dialogs.ClassManagerDialog(t)

    monkeypatch.setattr(simpledialog, "askstring", lambda *a, **k: "Coach")
    dlg.selected = {0}
    dlg.rename_selected()
    assert t.classes == ["Coach", "Car", "Motorcycle"]
    assert (lbl / "classes.txt").exists() is False  # rename never touches label files
    assert (lbl.parent / "classes.txt").read_text() == "Coach\nCar\nMotorcycle"

    class FakeChoice:
        result = (1, "Vehicle")

        def __init__(self, *a, **k):
            pass
    monkeypatch.setattr(class_dialogs, "_MergeChoice", FakeChoice)
    monkeypatch.setattr(dlg, "wait_window", lambda w: None)
    dlg.selected = {1, 2}
    dlg.merge_selected()
    assert t.classes == ["Coach", "Vehicle"]
    assert (lbl / "a.txt").read_text().splitlines() == [
        "0 0.5 0.5 0.2 0.2", "1 0.4 0.4 0.1 0.1", "1 0.3 0.3 0.1 0.1"]

    dlg.selected = {0, 1}
    dlg.delete_selected()
    assert t.classes == [] and (lbl / "a.txt").read_text() == ""
    dlg.destroy()


def test_import_mapping_lets_autolabel_find_renamed_model_classes(tab):
    from pk_studio.core import class_ops
    from pk_studio.ui import class_dialogs
    t, _ = tab
    model_names = ["bus", "car", "motorbike", "person"]
    dlg = class_dialogs.ClassImportDialog(t, t, model_names, "best.pt", True, "match")
    # bus/car auto-match by name; motorbike has no match -> map it by hand; person -> skip
    assert dlg.combos["bus"].get().startswith("→ [1]")
    dlg.combos["motorbike"].set(dlg.options[2])
    dlg.combos["person"].set(class_dialogs.ClassImportDialog.SKIP)
    dlg.apply()
    assert t.classes == ["Bus", "Car", "Motorcycle"]
    assert t.model_class_map["motorbike"] == "Motorcycle" and t.model_class_map["person"] is None
    assert class_ops.resolve_target("motorbike", t.classes, t.model_class_map) == 2
    assert class_ops.resolve_target("person", t.classes, t.model_class_map) is None
    assert class_ops.load_model_map(t.src_dir)["motorbike"] == "Motorcycle"


def test_import_replace_adopts_model_classes_and_keeps_labels(tab):
    from pk_studio.ui import class_dialogs
    t, lbl = tab
    dlg = class_dialogs.ClassImportDialog(t, t, ["Car", "Truck", "Bus"], "best.pt", True, "replace")
    dlg.apply()
    assert t.classes == ["Car", "Truck", "Bus", "Motorcycle"]
    # old ids: 0 Bus->2, 1 Car->0, 2 Motorcycle->3
    assert [ln.split()[0] for ln in (lbl / "a.txt").read_text().splitlines()] == ["2", "0", "3"]

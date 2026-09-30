import pytest

from pk_studio.core.class_ops import (
    add_classes, auto_match, count_class_usage, delete_classes, load_class_names,
    load_model_map, merge_classes, move_class, names_to_list, remap_index_dict,
    remap_label_files, rename_class, replace_with, resolve_target, save_model_map,
    unmatched_model_classes,
)

CLASSES = ["Bus", "Car", "Motorcycle", "Side car"]


def _labels(tmp_path, files):
    d = tmp_path / "labels"
    d.mkdir()
    for name, text in files.items():
        (d / name).write_text(text, encoding="utf-8")
    return d


def test_rename_keeps_ids_and_rejects_duplicates():
    ch = rename_class(CLASSES, 1, "Sedan")
    assert ch.new_classes[1] == "Sedan" and ch.old_to_new == {0: 0, 1: 1, 2: 2, 3: 3}
    with pytest.raises(ValueError):
        rename_class(CLASSES, 1, "Bus")
    with pytest.raises(ValueError):
        rename_class(CLASSES, 1, "  ")


def test_delete_multiple_classes_remaps_and_drops():
    ch = delete_classes(CLASSES, [0, 2])
    assert ch.new_classes == ["Car", "Side car"]
    assert ch.old_to_new == {1: 0, 3: 1} and ch.dropped == {0, 2}


def test_merge_classes_points_all_to_target():
    ch = merge_classes(CLASSES, [1, 2, 3], target_idx=2, new_name="Vehicle")
    assert ch.new_classes == ["Bus", "Vehicle"]
    assert ch.old_to_new == {0: 0, 1: 1, 2: 1, 3: 1} and ch.merged
    with pytest.raises(ValueError):
        merge_classes(CLASSES, [1], 1)
    with pytest.raises(ValueError):
        merge_classes(CLASSES, [1, 2], 0)


def test_move_class_swaps_ids():
    ch = move_class(CLASSES, 0, 1)
    assert ch.new_classes[:2] == ["Car", "Bus"] and ch.old_to_new[0] == 1 and ch.old_to_new[1] == 0


def test_remap_label_files_merge_dedupes(tmp_path):
    d = _labels(tmp_path, {
        "a.txt": "1 0.5 0.5 0.2 0.2\n2 0.5 0.5 0.2 0.2\n0 0.1 0.1 0.1 0.1\n",
        "b.txt": "3 0.3 0.3 0.1 0.1\n",
        "classes.txt": "Bus\nCar\n",
    })
    ch = merge_classes(CLASSES, [1, 2, 3], 2, "Vehicle")
    assert remap_label_files(d, ch) == []
    assert (d / "a.txt").read_text().splitlines() == ["1 0.5 0.5 0.2 0.2", "0 0.1 0.1 0.1 0.1"]
    assert (d / "b.txt").read_text().splitlines() == ["1 0.3 0.3 0.1 0.1"]
    assert (d / "classes.txt").read_text() == "Bus\nCar\n"


def test_remap_label_files_delete_and_keep_unknown_ids(tmp_path):
    d = _labels(tmp_path, {"a.txt": "0 0.5 0.5 0.2 0.2\n9 0.5 0.5 0.2 0.2\n1 0.5 0.5 0.2 0.2\n"})
    remap_label_files(d, delete_classes(CLASSES, [0]))
    assert (d / "a.txt").read_text().splitlines() == ["9 0.5 0.5 0.2 0.2", "0 0.5 0.5 0.2 0.2"]


def test_count_class_usage(tmp_path):
    d = _labels(tmp_path, {"a.txt": "0 0.5 0.5 0.2 0.2\n0 0.1 0.1 0.1 0.1\n2 0.5 0.5 0.2 0.2\n"})
    assert count_class_usage(d) == {0: 2, 2: 1}


def test_auto_match_ignores_case_and_separators():
    m = auto_match(["side_car", "MOTORCYCLE", "Tuk-tuk"], CLASSES)
    assert m == {"side_car": "Side car", "MOTORCYCLE": "Motorcycle", "Tuk-tuk": None}


def test_resolve_target_prefers_saved_mapping():
    assert resolve_target("bus", CLASSES, None) == 0
    assert resolve_target("bus", CLASSES, {"bus": "Car"}) == 1
    assert resolve_target("bus", CLASSES, {"bus": None}) is None
    assert resolve_target("truck", CLASSES, None) is None


def test_unmatched_model_classes_ignores_user_decisions():
    assert unmatched_model_classes(["bus", "truck", "van"], CLASSES, {"van": None}) == ["truck"]


def test_replace_with_model_classes_keeps_old_labels():
    ch = replace_with(["car", "Thing"], ["Bus", "Car", "Truck"])
    assert ch.new_classes == ["Bus", "Car", "Truck", "Thing"]
    assert ch.old_to_new == {0: 1, 1: 3}


def test_add_classes_skips_existing_and_blank():
    assert add_classes(CLASSES, ["Bus", " ", "Van"]).new_classes == CLASSES + ["Van"]


def test_names_to_list_orders_model_dict():
    assert names_to_list({1: "b", 0: "a", 2: "c"}) == ["a", "b", "c"]


def test_load_class_names_txt_and_yaml(tmp_path):
    (tmp_path / "classes.txt").write_text("Bus\n\nCar\nBus\n", encoding="utf-8")
    assert load_class_names(tmp_path / "classes.txt") == ["Bus", "Car"]
    (tmp_path / "data.yaml").write_text("names:\n  0: Bus\n  1: Car\n", encoding="utf-8")
    assert load_class_names(tmp_path / "data.yaml") == ["Bus", "Car"]
    (tmp_path / "list.yaml").write_text("names: [x, y]\n", encoding="utf-8")
    assert load_class_names(tmp_path / "list.yaml") == ["x", "y"]
    (tmp_path / "bad.yaml").write_text("train: a\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_class_names(tmp_path / "bad.yaml")


def test_remap_index_dict_follows_change():
    ch = delete_classes(CLASSES, [0])
    assert remap_index_dict({0: "red", 1: "green", 3: "blue"}, ch) == {0: "green", 2: "blue"}


def test_model_map_roundtrip(tmp_path):
    assert load_model_map(tmp_path) == {}
    save_model_map(tmp_path, {"bus": "Bus", "person": None})
    assert load_model_map(tmp_path) == {"bus": "Bus", "person": None}

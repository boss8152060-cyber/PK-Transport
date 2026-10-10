"""Class editing, merging and model-class mapping for PK Studio.

Everything here is independent from Tkinter. A *ClassChange* describes how a
class list changed (``old_to_new`` maps every surviving old id to its new id,
``dropped`` holds ids that must be removed from label files), so the UI can
apply the same change to labels, colors and filters in one place.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set

from pk_studio.core.fileio import atomic_write_text

MODEL_MAP_FILE = ".pk_model_class_map.json"


@dataclass
class ClassChange:
    new_classes: List[str]
    old_to_new: Dict[int, int]
    dropped: Set[int] = field(default_factory=set)

    @property
    def merged(self) -> bool:
        """True when two old ids now share one new id."""
        targets = list(self.old_to_new.values())
        return len(targets) != len(set(targets))


# --------------------------------------------------------------------------
# Reading class names
# --------------------------------------------------------------------------
def names_to_list(names) -> List[str]:
    """Ordered class names from an Ultralytics ``model.names`` dict or a list."""
    if isinstance(names, Mapping):
        return [str(names[k]) for k in sorted(names, key=lambda k: int(k))]
    return [str(n) for n in names]


def load_class_names(path) -> List[str]:
    """Read class names from ``.txt`` / ``.names`` (one per line) or a YOLO ``data.yaml``."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        import yaml
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict) or "names" not in data:
            raise ValueError("This YAML file has no 'names' entry.")
        names = names_to_list(data["names"])
    else:
        names = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    names = list(dict.fromkeys(n.strip() for n in names if n and n.strip()))
    if not names:
        raise ValueError("No class names found in this file.")
    return names


# --------------------------------------------------------------------------
# Matching
# --------------------------------------------------------------------------
def normalize_name(name: str) -> str:
    return "".join(ch for ch in str(name).casefold() if ch.isalnum())


def auto_match(source_names: Iterable[str], classes: Sequence[str]) -> Dict[str, Optional[str]]:
    """Match each source name to one of ``classes``: exact first, then ignoring
    case, spaces, ``_`` and ``-`` ("Side car" == "side_car"). No match -> None."""
    by_norm: Dict[str, str] = {}
    for c in classes:
        by_norm.setdefault(normalize_name(c), c)
    result: Dict[str, Optional[str]] = {}
    for name in source_names:
        if name in classes:
            result[name] = name
        else:
            result[name] = by_norm.get(normalize_name(name))
    return result


def resolve_target(model_name: str, classes: Sequence[str], mapping: Optional[Mapping[str, Optional[str]]]) -> Optional[int]:
    """Dataset class index for a model class name, or None to skip it.

    A saved/edited mapping wins; otherwise fall back to automatic matching."""
    if mapping and model_name in mapping:
        target = mapping[model_name]
        return classes.index(target) if target in classes else None
    match = auto_match([model_name], classes)[model_name]
    return classes.index(match) if match else None


def unmatched_model_classes(model_names: Iterable[str], classes: Sequence[str],
                            mapping: Optional[Mapping[str, Optional[str]]] = None) -> List[str]:
    """Model classes that would be skipped (no mapping target and no name match)."""
    out = []
    for name in model_names:
        if mapping and name in mapping:
            continue  # the user already decided (including "skip")
        if resolve_target(name, classes, None) is None:
            out.append(name)
    return out


# --------------------------------------------------------------------------
# Editing operations (each returns a ClassChange; nothing touches disk)
# --------------------------------------------------------------------------
def _identity(n: int) -> Dict[int, int]:
    return {i: i for i in range(n)}


def add_classes(classes: Sequence[str], names: Iterable[str]) -> ClassChange:
    new = list(classes)
    for n in names:
        n = str(n).strip()
        if n and n not in new:
            new.append(n)
    return ClassChange(new, _identity(len(classes)))


def rename_class(classes: Sequence[str], idx: int, new_name: str) -> ClassChange:
    new_name = str(new_name).strip()
    if not new_name:
        raise ValueError("Class name cannot be empty.")
    if not 0 <= idx < len(classes):
        raise IndexError(idx)
    for j, c in enumerate(classes):
        if j != idx and c == new_name:
            raise ValueError(f'"{new_name}" already exists. Use Merge to combine two classes.')
    new = list(classes)
    new[idx] = new_name
    return ClassChange(new, _identity(len(classes)))


def move_class(classes: Sequence[str], idx: int, delta: int) -> ClassChange:
    j = idx + delta
    if not (0 <= idx < len(classes) and 0 <= j < len(classes)):
        return ClassChange(list(classes), _identity(len(classes)))
    new = list(classes)
    new[idx], new[j] = new[j], new[idx]
    mapping = _identity(len(classes))
    mapping[idx], mapping[j] = j, idx
    return ClassChange(new, mapping)


def delete_classes(classes: Sequence[str], idxs: Iterable[int]) -> ClassChange:
    gone = {i for i in idxs if 0 <= i < len(classes)}
    new, mapping = [], {}
    for i, c in enumerate(classes):
        if i in gone:
            continue
        mapping[i] = len(new)
        new.append(c)
    return ClassChange(new, mapping, dropped=gone)


def merge_classes(classes: Sequence[str], idxs: Iterable[int], target_idx: int,
                  new_name: Optional[str] = None) -> ClassChange:
    """Merge ``idxs`` into ``target_idx`` (which must be one of them)."""
    idxs = {i for i in idxs if 0 <= i < len(classes)}
    if target_idx not in idxs:
        raise ValueError("The target class must be one of the merged classes.")
    if len(idxs) < 2:
        raise ValueError("Select at least two classes to merge.")
    new, mapping = [], {}
    for i, c in enumerate(classes):
        if i in idxs and i != target_idx:
            continue
        mapping[i] = len(new)
        new.append(c)
    for i in idxs:
        mapping[i] = mapping[target_idx]
    if new_name is not None and new_name.strip():
        name = new_name.strip()
        if name in [c for j, c in enumerate(new) if j != mapping[target_idx]]:
            raise ValueError(f'"{name}" already exists.')
        new[mapping[target_idx]] = name
    return ClassChange(new, mapping)


def replace_with(classes: Sequence[str], source_names: Sequence[str]) -> ClassChange:
    """Adopt ``source_names`` (e.g. a model's classes) as the class list.

    Existing classes are matched by name so their labels follow. Old classes that
    match nothing are appended after the source classes so no label is lost."""
    source = list(dict.fromkeys(str(n) for n in source_names))
    matches = auto_match(classes, source)
    new = list(source)
    mapping: Dict[int, int] = {}
    for i, c in enumerate(classes):
        target = matches[c]
        if target is None:
            new.append(c)
            mapping[i] = len(new) - 1
        else:
            mapping[i] = new.index(target)
    return ClassChange(new, mapping)


# --------------------------------------------------------------------------
# Applying a change to label files
# --------------------------------------------------------------------------
def remap_label_files(lbl_dir, change: ClassChange) -> List[str]:
    """Rewrite YOLO label files for ``change``. Returns names of files that could not be updated.

    Ids that are neither remapped nor dropped are left untouched. After a merge,
    exact duplicate lines created by the merge are removed."""
    failures: List[str] = []
    if not lbl_dir or not os.path.isdir(lbl_dir):
        return failures
    dedupe = change.merged
    for root, _dirs, files in os.walk(lbl_dir):
        for filename in files:
            if not filename.lower().endswith(".txt") or filename.lower() == "classes.txt":
                continue
            path = os.path.join(root, filename)
            try:
                lines_out: List[str] = []
                changed = False
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split()
                        if not parts:
                            continue
                        try:
                            old_id = int(parts[0])
                        except ValueError:
                            lines_out.append(line.rstrip())
                            continue
                        if old_id in change.dropped:
                            changed = True
                            continue
                        if old_id in change.old_to_new:
                            new_id = change.old_to_new[old_id]
                            changed = changed or new_id != old_id
                            parts[0] = str(new_id)
                        lines_out.append(" ".join(parts))
                if dedupe:
                    unique = list(dict.fromkeys(lines_out))
                    changed = changed or len(unique) != len(lines_out)
                    lines_out = unique
                if changed:
                    atomic_write_text(path, "\n".join(lines_out) + ("\n" if lines_out else ""))
            except (OSError, UnicodeError):
                failures.append(filename)
    return failures


def count_class_usage(lbl_dir) -> Dict[int, int]:
    """How many boxes each class id has across all label files."""
    counts: Dict[int, int] = {}
    if not lbl_dir or not os.path.isdir(lbl_dir):
        return counts
    for root, _dirs, files in os.walk(lbl_dir):
        for filename in files:
            if not filename.lower().endswith(".txt") or filename.lower() == "classes.txt":
                continue
            try:
                with open(os.path.join(root, filename), "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.split()
                        if parts and parts[0].lstrip("-").isdigit():
                            cid = int(parts[0])
                            counts[cid] = counts.get(cid, 0) + 1
            except (OSError, UnicodeError):
                continue
    return counts


def remap_index_dict(data: Mapping[int, object], change: ClassChange) -> Dict[int, object]:
    """Carry an index-keyed dict (colors, visibility, filters) across a change.

    When several old ids merge into one, the target keeps the first value seen."""
    out: Dict[int, object] = {}
    for old, value in data.items():
        if old in change.old_to_new:
            out.setdefault(change.old_to_new[old], value)
    return out


# --------------------------------------------------------------------------
# Saved model -> dataset class mapping
# --------------------------------------------------------------------------
def load_model_map(dataset_dir) -> Dict[str, Optional[str]]:
    path = Path(dataset_dir) / MODEL_MAP_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(k): (None if v is None else str(v)) for k, v in data.items()} if isinstance(data, dict) else {}


def save_model_map(dataset_dir, mapping: Mapping[str, Optional[str]]) -> None:
    atomic_write_text(Path(dataset_dir) / MODEL_MAP_FILE, json.dumps(dict(mapping), ensure_ascii=False, indent=2))

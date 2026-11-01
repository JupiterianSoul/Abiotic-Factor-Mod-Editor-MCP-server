"""Copies of a mod folder and of the test save. Everything goes in a folder outside the mods folder, because Upload zips a whole mod folder."""

import re
import shutil
import time
from pathlib import Path

ROOT = Path.home() / "abf-mod-backups"
_SAFE = re.compile(r"[^A-Za-z0-9_.\-]")


def _stamp():
    return time.strftime("%Y%m%d-%H%M%S")


def _unique(folder):
    """A new path: two backups in the same second must not collide."""
    path, n = folder, 1
    while path.exists():
        n += 1
        path = folder.with_name(f"{folder.name}-{n}")
    return path


def backup(mod_dir, label="", root=None):
    """Copy a mod folder to <root>/<mod>/<time>[-label] and return the new path."""
    src = Path(mod_dir)
    if not (src.is_dir() and any(src.glob("*.uplugin"))):
        raise ValueError(f"{src} is not a mod folder: no .uplugin in it")
    name = _stamp() + ("-" + _SAFE.sub("_", label) if label else "")
    dest = _unique(Path(root or ROOT) / src.name / name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest)
    return dest


def list_backups(mod_name, root=None):
    """Backups of one mod, newest first."""
    folder = Path(root or ROOT) / mod_name
    if not folder.is_dir():
        return []
    found = sorted((p for p in folder.iterdir() if p.is_dir() and not p.name.startswith("replaced-")),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    return [p.name for p in found]


def restore(mod_dir, backup_name=None, root=None):
    """Put a backup back. The current folder is moved to replaced-<time> first, so a restore can be undone."""
    dest = Path(mod_dir)
    folder = Path(root or ROOT) / dest.name
    names = list_backups(dest.name, root)
    if not names:
        raise ValueError(f"No backups of {dest.name} in {folder}")
    chosen = backup_name or names[0]
    if Path(chosen).name != chosen or chosen not in names:
        raise ValueError(f"No backup named {chosen!r}. Available: {names}")
    kept = None
    if dest.exists():
        kept = _unique(folder / ("replaced-" + _stamp()))
        shutil.move(str(dest), str(kept))
    shutil.copytree(folder / chosen, dest)
    return {"restored": chosen, "previous_version_kept_at": str(kept) if kept else None}


def clear_save(saved_dir, world="Cascade", root=None):
    """Move a test world's save out of the way, so the next Play starts fresh. Returns what moved and where."""
    base = Path(saved_dir) / "SaveGames" / "Editor"
    dest = _unique(Path(root or ROOT) / "test-saves" / (world + "-" + _stamp()))
    moved = []
    for kind in ("Worlds", "Backups"):
        src = base / kind / world
        if src.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest / kind))
            moved.append(kind)
    return {"moved": moved, "kept_at": str(dest) if moved else None}

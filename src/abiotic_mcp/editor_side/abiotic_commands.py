"""Commands executed on the editor main thread by abiotic_listener.

Each cmd_* function takes JSON values and returns JSON values. Anything that
changes an asset goes through _require_writable, which limits writes to the
active mod and refuses mods listed as protected in the user's config.
"""

import contextlib
import io
import json
import os
import re
import sys

import unreal

_PROP_RE = re.compile(r"^- ``(\w+)`` \((.+?)\):", re.M)
_RAW_TEXT_PREFIXES = ("(", "NSLOCTEXT(", "LOCTABLE(", "INVTEXT(")
_MAX_DEPTH = 16


# Reflection helpers. Python has no property listing API, but the generated
# class docstrings list every editor property with its type.


def _props(cls):
    props = {}
    for base in reversed(cls.__mro__):
        props.update(_PROP_RE.findall(base.__doc__ or ""))
    return props


def _resolve_type(name):
    return getattr(unreal, name, None)


def to_json(value, depth=0):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, unreal.EnumBase):
        return str(value.name)
    if isinstance(value, (unreal.Name, unreal.Text)):
        return str(value)
    if isinstance(value, (unreal.Array, unreal.Set)):
        return [to_json(item, depth + 1) for item in value]
    if isinstance(value, unreal.Map):
        return {str(to_json(k, depth + 1)): to_json(v, depth + 1) for k, v in value.items()}
    if isinstance(value, unreal.StructBase):
        if depth >= _MAX_DEPTH:
            return value.export_text()
        return _object_props(value, depth)
    if isinstance(value, unreal.Object):
        return value.get_path_name()
    return str(value)


def _object_props(obj, depth=0):
    out = {}
    for name in sorted(_props(type(obj))):
        try:
            out[name] = to_json(obj.get_editor_property(name), depth + 1)
        except Exception:
            # Some properties are listed but not readable from Python.
            continue
    return out


def _coerce(type_name, value, current=None):
    match = re.fullmatch(r"(Array|Set)\[(.+)\]", type_name)
    if match:
        element = _element_class(match.group(2))
        container = unreal.Array if match.group(1) == "Array" else unreal.Set
        result = container(element)
        for item in value:
            coerced = _coerce(match.group(2), item)
            if container is unreal.Array:
                result.append(coerced)
            else:
                result.add(coerced)
        return result
    cls = _resolve_type(type_name)
    if value is None or not isinstance(cls, type):
        return value
    if issubclass(cls, unreal.EnumBase):
        member = getattr(cls, str(value).upper().replace(" ", "_"), None)
        if member is None:
            raise ValueError("{} is not a valid {}".format(value, type_name))
        return member
    if issubclass(cls, unreal.StructBase):
        return _coerce_struct(cls, value, current)
    if issubclass(cls, unreal.Name):
        return unreal.Name(value)
    if issubclass(cls, unreal.Text):
        return unreal.Text(value)
    if issubclass(cls, unreal.Object) and isinstance(value, str):
        loaded = unreal.load_asset(value)
        if loaded is None:
            raise ValueError("Could not load asset {}".format(value))
        return loaded
    return value


def _element_class(type_name):
    primitives = {"str": str, "bool": bool, "int32": int, "int64": int, "float": float, "double": float}
    if type_name in primitives:
        return primitives[type_name]
    cls = _resolve_type(type_name)
    if cls is None:
        raise ValueError("Unknown element type {}".format(type_name))
    return cls


def _coerce_struct(cls, value, current=None):
    struct = current if current is not None else cls()
    if isinstance(value, str):
        if not struct.import_text(value):
            raise ValueError("Could not parse {!r} as {}".format(value, cls.__name__))
        return struct
    apply_values(struct, value)
    return struct


def apply_values(target, values):
    """Set nested JSON values on a UObject or struct, validating every name."""
    props = _props(type(target))
    for name, value in values.items():
        if name not in props:
            raise ValueError(
                "{} has no property '{}'. Available: {}".format(
                    type(target).__name__, name, ", ".join(sorted(props))
                )
            )
        current = target.get_editor_property(name)
        target.set_editor_property(name, _coerce(props[name], value, current))


def _to_import_text(value):
    """Convert one value from a DataTable JSON export to Unreal import text."""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "({})".format(",".join(_to_import_text(item) for item in value))
    if isinstance(value, dict):
        return "({})".format(",".join("{}={}".format(k, _to_import_text(v)) for k, v in value.items()))
    if str(value).startswith(_RAW_TEXT_PREFIXES):
        return value
    return '"{}"'.format(str(value).replace("\\", "\\\\").replace('"', '\\"'))


def import_exported_row(struct, exported):
    """Fill a row struct from one exported JSON row. Returns fields that failed."""
    failed = []
    for key, value in exported.items():
        if key == "Name":
            continue
        if not struct.import_text("({}={})".format(key, _to_import_text(value))):
            failed.append(key)
    return failed


# Guards


def _config():
    path = os.path.join(os.path.expanduser("~"), ".abiotic-mcp", "config.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _active_mod():
    config = unreal.AbioticFactorEditorCookedFunctionLibrary.get_active_mod_configuration()
    if config is None:
        return None
    return config.get_path_name().split("/")[1]


def _require_active_mod():
    mod = _active_mod()
    if mod is None:
        raise RuntimeError("No mod is open. Load a mod project in the Mod Browser, then retry.")
    return mod


def _require_writable(path):
    mod = _require_active_mod()
    if mod in _config().get("protected_mods", []):
        raise PermissionError("Mod '{}' is protected in config.json, so it cannot be changed.".format(mod))
    if not (path + "/").startswith("/{}/".format(mod)):
        raise PermissionError("{} is outside the active mod (/{}). Refusing to write.".format(path, mod))
    return mod


def _load(path):
    asset = unreal.load_asset(path)
    if asset is None:
        raise ValueError("Asset not found: {}".format(path))
    return asset


def _registry():
    return unreal.AssetRegistryHelpers.get_asset_registry()


def _describe(data):
    return {
        "path": str(data.package_name),
        "name": str(data.asset_name),
        "class": str(data.asset_class_path.asset_name),
    }


# Commands


def cmd_status():
    mod = _active_mod()
    return {
        "engine_version": unreal.SystemLibrary.get_engine_version(),
        "project": unreal.SystemLibrary.get_game_name(),
        "python": sys.version.split()[0],
        "active_mod": mod,
        "active_mod_protected": mod in _config().get("protected_mods", []),
    }


def cmd_list_assets(path, recursive=True, limit=500):
    assets = _registry().get_assets_by_path(path, recursive=recursive)
    return {"total": len(assets), "assets": [_describe(a) for a in list(assets)[:limit]]}


def cmd_search_assets(query="", asset_class="", path="/Game", limit=100):
    query = query.lower()
    found = []
    for data in _registry().get_assets_by_path(path, recursive=True):
        info = _describe(data)
        if query and query not in info["path"].lower():
            continue
        if asset_class and asset_class.lower() != info["class"].lower():
            continue
        found.append(info)
        if len(found) >= limit:
            break
    return {"assets": found, "truncated": len(found) >= limit}


def cmd_read_asset(path):
    asset = _load(path)
    if isinstance(asset, unreal.DataTable):
        return cmd_read_datatable(path)
    return {
        "path": asset.get_path_name(),
        "class": type(asset).__name__,
        "properties": _object_props(asset),
    }


def cmd_list_datatables(query=""):
    tables = _registry().get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "DataTable"))
    paths = sorted(str(t.package_name) for t in tables)
    return {"tables": [p for p in paths if query.lower() in p.lower()]}


def _table_rows(table):
    return json.loads(unreal.DataTableFunctionLibrary.export_data_table_to_json_string(table))


def cmd_read_datatable(path, rows=None, offset=0, limit=25):
    table = _load(path)
    if not isinstance(table, unreal.DataTable):
        raise ValueError("{} is not a DataTable".format(path))
    all_rows = _table_rows(table)
    if rows:
        wanted = set(rows)
        selected = [r for r in all_rows if r.get("Name") in wanted]
    else:
        selected = all_rows[offset : offset + limit]
    return {
        "path": path,
        "row_struct": table.get_editor_property("row_struct").get_name(),
        "total_rows": len(all_rows),
        "row_names": [r.get("Name") for r in all_rows],
        "rows": selected,
    }


def cmd_list_row_asset_types():
    names = [n for n in dir(unreal) if n.endswith("ModRowAsset") and n != "AbioticModRowAsset"]
    return {"types": sorted(names)}


def _row_asset_class(name):
    cls = getattr(unreal, name, None)
    if not (isinstance(cls, type) and issubclass(cls, unreal.AbioticModRowAsset)):
        raise ValueError("{} is not a mod row asset type. See list_row_asset_types.".format(name))
    return cls


def _open_row_asset(cls, table, row_name):
    mod = _require_active_mod()
    package_dir = "/{}/DataTables/{}".format(mod, table)
    path = "{}/{}".format(package_dir, row_name)
    _require_writable(path)
    created = False
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        asset = _load(path)
        if not isinstance(asset, cls):
            raise ValueError("{} exists but is a {}".format(path, type(asset).__name__))
    else:
        factory = unreal.DataAssetFactory()
        factory.set_editor_property("data_asset_class", cls)
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        asset = tools.create_asset(row_name, package_dir, cls, factory)
        if asset is None:
            raise RuntimeError("Could not create {}".format(path))
        created = True
    return asset, path, created


def cmd_upsert_mod_rows(row_asset_class, table, rows):
    """Mods add rows as one asset per row: /<Mod>/DataTables/<Table>/<RowName>."""
    cls = _row_asset_class(row_asset_class)
    results = []
    for spec in rows:
        asset, path, created = _open_row_asset(cls, table, spec["row_name"])
        asset.set_editor_property("row_name", spec["row_name"])
        asset.set_editor_property("override_existing_row", bool(spec.get("override_existing_row", False)))
        row = asset.get_editor_property("row")
        apply_values(row, spec.get("values", {}))
        asset.set_editor_property("row", row)
        results.append({"path": path, "created": created})
    return {"rows": results, "saved": False}


def cmd_clone_row(source_table, source_row, row_asset_class, table, new_row_name, override_existing_row=False):
    """Copy a row from any table into a new row asset in the active mod."""
    cls = _row_asset_class(row_asset_class)
    exported = [r for r in _table_rows(_load(source_table)) if r.get("Name") == source_row]
    if not exported:
        raise ValueError("Row {} not found in {}".format(source_row, source_table))
    asset, path, created = _open_row_asset(cls, table, new_row_name)
    row = asset.get_editor_property("row")
    failed = import_exported_row(row, exported[0])
    asset.set_editor_property("row", row)
    asset.set_editor_property("row_name", new_row_name)
    asset.set_editor_property("override_existing_row", bool(override_existing_row))
    return {"path": path, "created": created, "failed_fields": failed, "saved": False}


def cmd_duplicate_asset(source, destination):
    _require_writable(destination)
    if unreal.EditorAssetLibrary.does_asset_exist(destination):
        raise ValueError("{} already exists".format(destination))
    copy = unreal.EditorAssetLibrary.duplicate_asset(source, destination)
    if copy is None:
        raise RuntimeError("Could not duplicate {}".format(source))
    return {"path": destination, "saved": False}


def cmd_set_properties(path, properties):
    _require_writable(path)
    asset = _load(path)
    apply_values(asset, properties)
    return {"path": path, "saved": False}


def cmd_save_all():
    mod = _require_writable("/" + _require_active_mod())
    ok = unreal.EditorAssetLibrary.save_directory("/" + mod, only_if_is_dirty=True, recursive=True)
    return {"mod": mod, "saved": bool(ok)}


def cmd_validate_mod():
    mod = _require_active_mod()
    assets = _registry().get_assets_by_path("/" + mod, recursive=True)
    subsystem = unreal.get_editor_subsystem(unreal.EditorValidatorSubsystem)
    failures, _, results = subsystem.validate_assets_with_settings(assets)
    return {"mod": mod, "assets_with_issues": failures, "results": to_json(results)}


def cmd_list_templates():
    subsystem = unreal.get_editor_subsystem(unreal.UGCTemplateSubsystem)
    return {"templates": [str(t.get_editor_property("name")) for t in subsystem.discover_templates()]}


def cmd_create_mod(name, template, substitutions=None):
    subsystem = unreal.get_editor_subsystem(unreal.UGCTemplateSubsystem)
    templates = {str(t.get_editor_property("name")): t for t in subsystem.discover_templates()}
    if template not in templates:
        raise ValueError(
            "Template '{}' is not available from Python (found: {}). Create the mod in the "
            "Mod Browser instead, then retry.".format(template, ", ".join(sorted(templates)) or "none")
        )
    values = unreal.Map(str, str)
    for key, value in (substitutions or {}).items():
        values[key] = value
    return {"created": bool(subsystem.create_ugc_from_template(name, templates[template], values))}


def cmd_python(code):
    """Run arbitrary Python in the editor and return what it printed."""
    out = io.StringIO()
    scope = {"unreal": unreal, "__name__": "__abiotic_mcp__"}
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        exec(compile(code, "<abiotic-mcp>", "exec"), scope)
    return {"output": out.getvalue(), "result": repr(scope.get("result"))}

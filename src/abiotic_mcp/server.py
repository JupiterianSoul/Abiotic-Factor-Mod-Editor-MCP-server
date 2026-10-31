"""MCP tools. Each one forwards to the editor listener or reads local files."""

import json
from collections import deque

from mcp.server.mcpserver import MCPServer

from . import TESTED_ENGINE_PREFIX, __version__, blueprint_filter, paths
from .bridge import Bridge, EditorNotConnected
from .redact import redact

mcp = MCPServer("abiotic-factor-mod-editor")
bridge = Bridge()


@mcp.tool()
def editor_status() -> dict:
    """Report whether the Mod Editor is connected, its version and the open mod."""
    install_dir, version = paths.find_editor()
    info = {"server_version": __version__, "editor_install": str(install_dir), "editor_version": version}
    try:
        status = bridge.call("status")
    except EditorNotConnected as exc:
        return {**info, "connected": False, "hint": str(exc)}
    info.update(status, connected=True)
    if not status["engine_version"].startswith(TESTED_ENGINE_PREFIX):
        info["warning"] = "Untested engine version {}, expected {}.x. Some tools may not work.".format(
            status["engine_version"], TESTED_ENGINE_PREFIX
        )
    return info


@mcp.tool()
def list_mods() -> dict:
    """List local mod projects (works without the editor open)."""
    mods = []
    root = paths.mods_dir()
    if root.is_dir():
        for plugin in sorted(root.glob("*/*.uplugin")):
            try:
                descriptor = json.loads(plugin.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                descriptor = {}
            mods.append(
                {
                    "id": plugin.stem,
                    "name": descriptor.get("FriendlyName", plugin.stem),
                    "content_root": "/" + plugin.stem,
                    "folder": str(plugin.parent),
                }
            )
    return {"mods_dir": str(root), "mods": mods}


@mcp.tool()
def list_assets(path: str, recursive: bool = True, limit: int = 500) -> dict:
    """List assets under a content path, such as /Game/Blueprints/Items or /MyMod."""
    return bridge.call("list_assets", path=path, recursive=recursive, limit=limit)


@mcp.tool()
def search_assets(query: str = "", asset_class: str = "", path: str = "/Game", limit: int = 100) -> dict:
    """Find assets under a path by package path substring and/or exact class name."""
    return bridge.call("search_assets", query=query, asset_class=asset_class, path=path, limit=limit)


@mcp.tool()
def read_asset(path: str) -> dict:
    """Read an asset's properties as JSON. DataTables return their rows."""
    return bridge.call("read_asset", path=path)


@mcp.tool()
def list_datatables(query: str = "") -> dict:
    """List DataTable assets, optionally filtered by path substring."""
    return bridge.call("list_datatables", query=query)


@mcp.tool()
def read_datatable(path: str, rows: list[str] | None = None, offset: int = 0, limit: int = 25) -> dict:
    """Read rows from a DataTable. Pass row names, or page with offset and limit."""
    return bridge.call("read_datatable", path=path, rows=rows, offset=offset, limit=limit)


@mcp.tool()
def list_row_asset_types() -> dict:
    """List row asset classes a mod can create, such as RecipeModRowAsset."""
    return bridge.call("list_row_asset_types")


@mcp.tool()
def upsert_datatable_rows(row_asset_class: str, table: str, rows: list[dict]) -> dict:
    """Create or update rows in the active mod. Call save_all afterwards.

    Mods add one asset per row, stored at /<Mod>/DataTables/<table>/<row_name>.
    Each entry is {"row_name": str, "override_existing_row": bool, "values": {...}},
    with values in the snake_case form that read_asset returns. Set
    override_existing_row to replace a vanilla row of the same name.
    """
    return bridge.call("upsert_mod_rows", row_asset_class=row_asset_class, table=table, rows=rows)


@mcp.tool()
def clone_row(
    source_table: str,
    source_row: str,
    row_asset_class: str,
    table: str,
    new_row_name: str,
    override_existing_row: bool = False,
) -> dict:
    """Copy a vanilla row into a new row asset in the active mod, as a starting point."""
    return bridge.call(
        "clone_row",
        source_table=source_table,
        source_row=source_row,
        row_asset_class=row_asset_class,
        table=table,
        new_row_name=new_row_name,
        override_existing_row=override_existing_row,
    )


@mcp.tool()
def duplicate_asset(source: str, destination: str) -> dict:
    """Copy an asset into the active mod. The destination must be inside that mod."""
    return bridge.call("duplicate_asset", source=source, destination=destination)


@mcp.tool()
def set_properties(path: str, properties: dict) -> dict:
    """Set properties on an asset in the active mod. Call save_all afterwards."""
    return bridge.call("set_properties", path=path, properties=properties)


@mcp.tool()
def save_all() -> dict:
    """Save every changed asset in the active mod."""
    return bridge.call("save_all")


@mcp.tool()
def validate_mod() -> dict:
    """Run the editor's asset validators over the active mod."""
    return bridge.call("validate_mod")


@mcp.tool()
def list_templates() -> dict:
    """List mod templates the editor exposes to scripting."""
    return bridge.call("list_templates")


@mcp.tool()
def create_mod(name: str, template: str, substitutions: dict | None = None) -> dict:
    """Create a mod project from a template, if the editor exposes templates to scripting."""
    return bridge.call("create_mod", name=name, template=template, substitutions=substitutions)


@mcp.tool()
def package_mod() -> dict:
    """Save and validate the active mod, then explain how to package it.

    The editor only offers packaging through its own dialog, so this stops
    there. It never uploads anything to mod.io.
    """
    saved = bridge.call("save_all")
    validation = bridge.call("validate_mod")
    return {
        "saved": saved,
        "validation": validation,
        "packaged": False,
        "next_step": "In the Mod Editor, use the Package UGC action, choose platforms and an output "
        "folder. Upload the result to mod.io yourself from the editor.",
    }


@mcp.tool()
def check_blueprint_symbol(class_path: str, function: str | None = None) -> dict:
    """Check a class or function against Deep Field's Blueprint filter.

    Check before generating Blueprint logic and never use a blocked symbol.
    Example: class_path="/Script/Engine.GameplayStatics", function="GetPlayerController".
    """
    version, rules = blueprint_filter.load()
    return {"filter_version": version, **blueprint_filter.check(rules, class_path, function)}


@mcp.tool()
def run_python(code: str) -> dict:
    """Run Python inside the editor, with `unreal` imported, and return its output.

    This is an escape hatch and is not limited to the active mod. Use it for
    inspection and for gaps in the other tools. Do not use it to bypass the
    write guards, delete assets, or upload to mod.io without the user asking.
    """
    return bridge.call("python", code=code)


@mcp.tool()
def get_log(lines: int = 100, contains: str = "") -> dict:
    """Tail the editor log, with auth codes and API keys removed."""
    path = paths.log_file()
    if not path.exists():
        return {"log": "", "note": "No editor log at {}".format(path)}
    with open(path, encoding="utf-8", errors="replace") as f:
        selected = (line for line in f if contains.lower() in line.lower())
        return {"log": redact("".join(deque(selected, maxlen=min(lines, 2000))))}


def main():
    mcp.run()

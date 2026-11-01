# Abiotic Factor Mod Editor MCP server

An [MCP](https://modelcontextprotocol.io) server that lets an MCP client read and edit mods in the official Abiotic Factor Mod Editor: browse vanilla data, add or override table rows, change asset properties, and validate a mod before you package it.

Unofficial community tool, not affiliated with or endorsed by Deep Field Games.

## Quick start

You need the Mod Editor (1.5.0, from the Epic Games Launcher) on Windows, and [uv](https://docs.astral.sh/uv/).

1. Install the server:
   ```
   uv tool install git+https://github.com/JupiterianSoul/Abiotic-Factor-Mod-Editor-MCP-server
   ```
2. Set up the editor side (no admin rights needed):
   ```
   abiotic-mcp install
   ```
   This registers the server if the `claude` CLI is found. Otherwise it prints the config to paste.
3. Restart the Mod Editor and open a mod project.
4. Check everything:
   ```
   abiotic-mcp doctor
   ```

No uv? Run `install.ps1` from this repo, it needs Python 3.10 or newer instead.

## What install does

- Copies the listener to `%USERPROFILE%\.abiotic-mcp\editor`.
- Adds a small marked block to `Documents\UnrealEngine\Python\init_unreal.py`, which starts the listener whenever the Mod Editor launches. Other Unreal projects are skipped, and an existing `init_unreal.py` is kept.
- Writes nothing to Program Files and does not patch the editor.

The listener binds to `127.0.0.1` only and needs a token that is regenerated on every editor start.

To start the listener for one session instead, use Tools > Execute Python Script in the editor and pick `%USERPROFILE%\.abiotic-mcp\editor\start_listener.py`.

## MCP client config

Claude Code:

```
claude mcp add abiotic -- abiotic-mcp serve
```

Claude Desktop (`claude_desktop_config.json`) and Cursor (`.cursor/mcp.json`) use the same block:

```json
{
  "mcpServers": {
    "abiotic": { "command": "abiotic-mcp", "args": ["serve"] }
  }
}
```

If the client can't find the command, run `abiotic-mcp config` to get the block with the full path.

## Tools

| Tool | What it does |
|---|---|
| `editor_status` | Connection, versions and the open mod |
| `list_mods` | Local mod projects, works without the editor |
| `list_assets`, `search_assets` | Browse content by path, name or class |
| `read_asset` | Asset properties as JSON |
| `list_datatables`, `read_datatable` | Vanilla and mod tables, paged |
| `list_row_asset_types` | Row asset classes a mod can create |
| `upsert_datatable_rows` | Create or update rows in the open mod |
| `clone_row` | Copy a vanilla row into the open mod as a starting point |
| `duplicate_asset`, `set_properties` | Copy assets into the open mod, edit them |
| `save_all` | Save changed assets in the open mod |
| `validate_mod` | Run the editor's validators |
| `package_mod` | Save, validate and open the editor's upload panel |
| `open_mod_panel` | Open the editor's Mod Management Tool |
| `list_templates`, `create_mod` | Create a mod from a template, see limitations |
| `check_blueprint_symbol` | Look up a class or function in the Blueprint filter |
| `run_python` | Run Python in the editor, for anything not covered |
| `get_log` | Tail the editor log with auth codes and API keys removed |

Mods store one asset per row, at `/<Mod>/DataTables/<Table>/<RowName>`. `upsert_datatable_rows` follows that layout. Fields you leave out of a new row get struct defaults, so to change part of a vanilla row, use `clone_row` with `override_existing_row` and the same row name, then set what differs.

## Testing a mod locally

You don't need to package or upload a mod to try it:

1. Open the mod in the editor and save your changes (`save_all`).
2. Load a game map with File > Open Level, or ask your client to run this with `run_python`:
   ```python
   unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/Maps/Facility")
   ```
   `Facility` is a big map, so this can take a minute or two.
3. Press Play in the editor and check your change. Press Esc to stop.

This runs inside the editor, so it doesn't replace a final check of a packaged build in the game.

## Configuration

Nothing is required. Optional settings go in `%USERPROFILE%\.abiotic-mcp\config.json`:

```json
{
  "protected_mods": ["MyFinishedMod12345"],
  "editor_dir": "D:\\Epic Games\\AbioticFactorModEditor",
  "mods_dir": "D:\\Mods"
}
```

`protected_mods` lists mod folder names that write tools must refuse. Set `ABIOTIC_MCP_PORT` to change the listener port (default 47821).

## Limitations

- **Writes stay in the open mod.** Write tools refuse any other path, including `/Game`. `run_python` is not limited this way, so treat it like any other code you run on your PC.
- **Blueprint filter.** Deep Field restricts which Blueprint nodes mods can use. `check_blueprint_symbol` reads their published list, and clients should check it before generating Blueprint logic. The editor has the final say. This server can't inspect Blueprint graphs for you.
- **Packaging and uploading are yours.** Packaging is part of the editor's upload flow, so `package_mod` saves, validates and opens the editor's Mod Management Tool, then stops. Nothing here creates a mod.io page or uploads anything. mod.io rejects the 128x128 and 400x200 images in a new mod's `Media` folder, so use a listing image of at least 1024x576.
- **No deleting.** There is no delete tool.
- **`create_mod`** depends on the editor exposing templates to scripting, which 1.5.0 currently doesn't. Create the mod in the Mod Browser for now.
- **Validation details** go to the editor's message log. `validate_mod` returns counts, plus any rows that share a name, because the editor only warns about those once per session.
- Tested with editor 1.5.0 (UE 5.4.4). Other versions show a warning rather than failing outright.
- **Early version: not yet tested in a packaged build.** A recipe override made with this server worked in the editor's Play mode, but no mod made with it has been packaged or loaded in the game itself yet.
- Close open dialogs in the editor if a tool times out: commands run on the editor's main thread.

## Uninstall

```
abiotic-mcp uninstall
uv tool uninstall abiotic-mcp
```

This removes the startup block and `%USERPROFILE%\.abiotic-mcp`. Your mod projects are not touched.

## Development

```
uv venv
uv pip install -e ".[dev]"
.venv\Scripts\python -m pytest
```

`src/abiotic_mcp/editor_side` runs inside the editor (Python 3.11, standard library and `unreal` only). The rest runs outside it. After changing `abiotic_commands.py`, copy it to the install folder and send the listener a `reload` command, so you don't need to restart the editor.

## License

MIT, see [LICENSE](LICENSE).

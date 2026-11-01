# Technical details

For anyone who wants to know how this works or change it. If you just want to make mods, the [README](../README.md) is all you need.

Built on [abf-mod-editor-mcp](https://github.com/theelites11gamer/abf-mod-editor-mcp) by theelites11gamer. It's pure Python with no packages, and the server speaks MCP over stdio.

## Install from a clone

The script in the README does the same as this, without needing git:

```bash
git clone https://github.com/JupiterianSoul/Abiotic-Factor-Mod-Editor-MCP-server.git
cd Abiotic-Factor-Mod-Editor-MCP-server
python install.py
```

`install.py`:

1. Finds the Mod Editor through the Epic Games Launcher's install manifests (every install has a different random folder suffix, so nothing is hardcoded). If it can't, set `ABF_EDITOR_ROOT` or put `{"editor_root": "..."}` in a `config.json` next to `server.py`.
2. Puts a small startup hook in `Documents\UnrealEngine\Python\` (`init_unreal.py` + `abf_mcp_startup.py`). Every Unreal editor runs that file at startup; the hook checks the engine build tag and does nothing outside the Mod Editor. If you already have an `init_unreal.py`, the hook is appended as a marked block and your file is backed up.
3. Registers the server with Claude Code at user scope (through the `claude` CLI when it's on PATH, otherwise by adding it to `~/.claude.json` with a backup). `--no-register` skips this and just prints the command for other clients.

Then **restart the Mod Editor** and start a **new** Claude Code session. Ask it to call `editor_status`.

Remove everything with `python install.py --uninstall`.

## What the hook does

The editor's Python plugin has a "remote execution" mode (UDP discovery on 239.0.0.1:6766, loopback only, then a TCP command channel the editor opens back to the client). It's compiled into the Mod Editor but off by default, and the setting doesn't survive in the editor's config file. The hook switches it on at runtime for that session and also starts a tiny **file bridge** (`%LOCALAPPDATA%\abf-mod-editor-mcp\bridge`) as a fallback for when a modal dialog blocks remote execution or another client holds its connection.

The server uses remote execution first and the bridge second, opens a fresh connection per command (so it can share the editor with other tools), and reports a command that was sent but got no reply instead of retrying it.

## Tools (55)

| Group | Tools |
| --- | --- |
| Status and launch | `editor_status` (call first), `launch_editor`, `open_mod` (drives the picker's Browse… dialog, since the command line can't open a mod) |
| Python | `run_python`, `evaluate_python`, `run_python_file` (`args` → `ARGS` inside the script) |
| Mod data | `list_mods`, `list_mod_templates`, `find_assets`, `get_row`, `set_row` (plain values, Python expressions, or whole export text), `create_row_asset` (any of the 72 `*ModRowAsset` classes, optionally copied from a base-game row or another mod row), `delete_asset`, `save_assets`, `validate_assets` |
| Base-game data | `get_game_row`, list or read any row the game exposes through its `<Kind>HandleFunctionLibrary` (gear_item, weapon_item, recipe, buff_debuff, npc, pet, trait, …) |
| Blueprints | `build_graph` (node list → graph, every pin checked against the editor), `discover_pins` (the real pins of any node), `paste_graph` (clipboard T3D → graph, then checks what arrived), `compile_blueprint` (reports the compiler's errors; a Blueprint with errors isn't saved), `inspect_blueprint` (parent, variables, graphs, every reference, errors, nodes and pins), `export_t3d`, `t3d_errors`, `blueprint_filter_check` |
| Window | `open_asset`, `close_asset`, `editor_windows`, `editor_screenshot` (one editor window, returned as an image, works in the background), `editor_click`, `editor_keys`, `close_editor_window` |
| Map and play | `load_map`, `play_in_editor` start/stop, `pie_info` (players, pawns, locations, chosen pawn properties), `console_command` (editor or game world) |
| Easy row changes | `find_game_content` (search by in-game name: "duct tape" finds `ducttape`), `tweak_game_row` (safely override a vanilla row), `new_row_from` (a new row based on a vanilla one) |
| Testing | `test_mod` (one call: saves, checks, verifies rows, loads Facility and starts Play), `verify_mod` (asks the game's own lookup whether each row is active), `explain_mod` (what changed compared with vanilla), `check_mod_rows` (row name collisions and overrides), `clear_test_save` |
| Backups | `backup_mod`, `list_backups`, `restore_mod` (kept in `%USERPROFILE%\abf-mod-backups`, and a restore can be undone) |
| Release | `check_upload` (offline pre-upload check), `audit_mod` (the editor's Asset Audit and validators), `open_mod_manager`, `check_listing_image`, `make_listing_image`, `explain_upload_error` (the real reason an upload failed, with a fix), `read_editor_log` (hides auth codes and API keys) |
| Assets | `import_asset` (textures and models, no dialogs) |
| Guidance | `modding_guide` (workflow, rows, testing, upload, limits, starters, Blueprints, deployables) |

### Safety rails built in

- The row, save, compile, delete and T3D-export tools refuse anything under `/Game` (base content). Exporting a base-game Blueprint has crashed the editor. `run_python` can do anything the editor can, so review what it's about to run.
- `save_assets` with no paths saves only the open mods.
- Screenshots capture one editor window, never the desktop.
- Keys and text are only sent while the editor is the foreground window.
- `delete_asset` deletes one asset per call: a delete loop crashed the editor.
- Nothing uploads to mod.io. You do that in the editor.

### `check_upload` and `blueprint_filter_check`

The editor's **Upload Mod** zips the whole project folder and mod.io rejects some of what ends up inside (for instance any `.md` file, reported only as "Unknown ApiError"). The cloud cook then recompiles Blueprints without the editor-only assets, so a reference to something that exists only in the editor fails there. `check_upload` scans the folder for both, using the file lists in `data/` (names only, from game/editor version 1.5; see `data/make_editor_list.py`).

The upload's Asset Audit checks every function call, event, variable and event dispatcher in a mod's Blueprints against Deep Field's filter rules. `blueprint_filter_check` asks the editor for those same rules, with its `ABF.BlueprintFilter.DumpClass` console command, and names each blocked reference and the node it's on, before you find out one upload at a time. Nothing is downloaded, so the answer always matches the audit in your editor. This was compared with the real audit on test Blueprints and on a real mod, and the results were the same. The audit reads the nodes, not the compiled code, so an unconnected blocked call still fails it.

Neither replaces the editor's own checks; they catch the common failures early.

## Building graphs

Python can't create Blueprint nodes in this editor, so nodes go in as clipboard text (T3D). `build_graph` writes that text for you from a short list:

```json
{
  "asset_path": "/MyMod/Blueprints/BP_MyActor",
  "nodes": [
    {"id": "begin", "type": "event", "owner": "/Script/Engine.Actor", "function": "ReceiveBeginPlay"},
    {"id": "say", "owner": "/Script/Engine.KismetSystemLibrary", "function": "PrintString", "args": {"InString": "Hello"}}
  ],
  "links": [["begin.then", "say.execute"]],
  "paste": true,
  "compile": true
}
```

It never guesses a pin. Each kind of node is first pasted bare into a throwaway Blueprint outside your mod, which is never saved and is deleted straight away, and the pins the editor allocates are the ones used. Answers about game and engine classes are kept in `data/node-templates.json`, so the next request for the same node is instant. A wrong pin name is an error that lists the real ones. After pasting it reads the Blueprint back and reports any node or link that didn't arrive.

The result also lists anything the upload filter would block. For nodes `build_graph` has no type for, `raw` takes a node class and properties. `paste_graph` does the same pasting and checking for T3D you already have.

## Working notes

- Mod row assets are `PrimaryDataAsset`s; `row_name` defaults to the asset name and the game adds the mod prefix at runtime.
- Paste in passes: custom events must exist and be compiled before anything calls them, or the calls are dropped. `build_graph` resolves a Blueprint's own functions by building its throwaway Blueprint as a child of the one you name, so the same rule applies there.
- The editor drops every link of the last node in a paste. `paste_graph` and `build_graph` end each paste with a small comment node so that's never a real node; it's safe to delete.
- Pasted nodes can't link to nodes already in the graph, like a function's entry node. Wire those in the editor, or with `editor_click` and `editor_keys`.
- A call to a function the Blueprint doesn't have, pasted as raw T3D, opens a Fix Self Context Function References dialog that blocks the editor. `paste_graph` reports it under `dialogs`; close it with `close_editor_window`. `build_graph` names the class instead, so it gets an error and no dialog. Deletes never run through the file bridge, because that can happen behind a dialog and has crashed the editor.
- A variable with an `owner` needs a target linked to its `self` pin. Leave the owner out for the Blueprint's own or inherited variables.
- A pasted copy of an event that already exists in the graph, including a greyed-out default one, turns into a custom event that nothing calls. The paste report lists these under `changed_class`; delete the old event first, or paste with `clear`.
- A pure function has no exec pins. If pasted T3D links some on one, the editor removes them and joins what led into the node to what came after it. That graph is right, so the paste report counts it as fine, with a lint warning and the details under `pure_nodes` and `joined_links`. If the joined link isn't there, it's under `missing_links` and the paste fails. An exec output can only hold one link, so a pure node's `then` joins to the first of several.
- `clear` first pastes a marker comment and reads it back, so its Ctrl+A and Delete can only happen with a graph focused. On the Viewport tab they would delete components.
- A new Blueprint opens on its Viewport tab and a widget on its Designer. `paste_graph` brings the Event Graph or Graph view forward when nothing arrives, using positions in the default window layout. For a function's graph, open its tab first.
- T3D exports also hold deleted nodes and whole graphs the compiler generates. The tools count only live nodes in the graphs the Blueprint lists itself; `inspect_blueprint(include_deleted=true)` shows the rest.
- A T3D export is plain ASCII until the asset holds any other character, like a `°` in a text block. Then the whole file is UTF-16 with a byte-order mark. Read exports with `bpscan.read_t3d`, which handles both: read as UTF-8, a UTF-16 export parses as an empty Blueprint with no error.
- A new mod project can't be created from Python (the template system has no entry point). Do it in the picker: ITEMS tile → template → name → Create. `editor_screenshot` + `editor_click`/`editor_keys` can drive it.
- Loading a map opens the Message Log over the viewport; `close_editor_window("Message Log")` before Play In Editor.
- The editor runs commands on its game thread: keep scripts short, and never open a modal dialog from one.

## Testing

`python test_safety.py` needs no editor: write guards, log masking, listing images and the guide. `python test_offline.py` needs no editor either: filter rules, T3D parsing, paste checks and the graph builder. `python test_client.py` speaks MCP to the server over stdio and exercises the read-only tools against the open editor. `--bridge` forces the file-bridge transport. `--row <mod row asset> <mod folder>` also edits and restores a row, creates and deletes a row asset, and runs the two checkers. `--graph <mod root>` builds, pastes and compiles a throwaway Blueprint, taking the mouse and keyboard for a minute. Use a throwaway copy of a mod for the last two.

## Limits

- Built against Mod Editor 1.5.0 (engine `5.4.4-1050002+++DF+ABF`, Python 3.11). A future editor update may change the Python API; the file lists in `data/` are versioned and will need regenerating after a game update.
- Windows only.
- New mod projects are created by the user in the Mod Browser. The editor's template API isn't usable from Python: calling it crashed the editor.
- `verify_mod` proves the game's lookup returns a row, not how it plays. Testing in the real game needs a private upload, because mods are cooked on mod.io's servers.
- Upload status has no tool, because mod.io's API would need the login details in the editor log. Check Files > Cloud Cooking on the mod's page.
- Bringing the graph forward clicks positions in the default window layout, tested at 100% Windows display scaling. If they miss, `paste_graph` says nothing arrived, and a click on the tab from `editor_click` does the same job.
- A mod made with these tools still has to pass the editor's Asset Audit and mod.io's cloud cook; the checkers here reduce surprises, they don't guarantee anything.

# Abiotic Factor Mod Editor MCP server

Make Abiotic Factor mods by describing them.

Tell your AI assistant "make the Crafting Bench cost 1 duct tape", and it makes the change in the official Mod Editor, checks it, and starts the game inside the editor so you can try it. You don't need to know Unreal Engine.

## Getting started

You'll need:

- A Windows PC with the [Abiotic Factor Mod Editor](https://store.epicgames.com/) installed (it's free on the Epic Games Launcher)
- An AI app that supports MCP, such as Claude Code, Claude Desktop, Codex or Cursor

**1. Install it.** Open PowerShell, paste this and press Enter:

```powershell
irm https://raw.githubusercontent.com/JupiterianSoul/Abiotic-Factor-Mod-Editor-MCP-server/main/install.ps1 | iex
```

This also needs Python. If you don't have it, the installer will try to add it for you. If you use Claude Code, you're all set. For other apps, the installer prints what to paste into their settings.

**2. Open the Mod Editor** (close it first if it's already open), then open a mod or create one in the Mod Browser. Log in to mod.io when it asks, if you plan to upload later.

**3. Start a new chat in your AI app and say what you want.**

## Things you can ask for

- "Make the Crafting Bench cost 1 duct tape, then test it."
- "Make the security pistol do double damage."
- "Add a stronger version of the knife that I can craft."
- "What does my mod change compared to the normal game?"
- "Undo that."

It works best for changes to the game's data, like recipes, items, weapons and enemies. It can also build simple Blueprint logic. For a new look, you'll need to bring your own 3D models or textures.

## Testing your mod

Say "test it". The AI saves your mod, checks it for problems, loads the game's map and starts playing inside the editor, usually in a minute or two. Then you just try your change. Press Esc when you're done.

This is a good test of whether your mod works, but it isn't quite the real game. To try it in the real game, upload it privately to mod.io and install it from the game's mod menu.

## Uploading your mod

When you're happy with it, say "help me upload this". The AI checks your mod, makes a listing image if you need one, and tells you what to click. It never uploads anything by itself, and your mod stays private until you decide otherwise.

After you upload, mod.io packages your mod on its servers, which can take a while. If an upload fails, ask the AI why. The editor's error messages are often vague, but it can usually find the real reason.

## Good to know

- **This is an early version.** It has been tested in the editor with a recipe mod, but no mod made with it has been uploaded or played in the real game yet. You may run into bugs.
- **Your mods are backed up when you ask.** Say "back up my mod" before big changes. Backups go in `abf-mod-backups` in your user folder.
- **It can't change the base game's files.** Like any mod, your changes live in your own mod.
- **You still create new mods yourself.** Making a new mod project in the Mod Browser takes a few clicks. The AI can tell you what to click.
- **Keep an eye on what it does.** The AI can run code inside the editor, so read what it's about to do when your app asks for permission.
- **The installer adds a small startup file** to `Documents\UnrealEngine\Python`. It only does something in the Mod Editor.

## Removing it

Paste this into PowerShell, then delete the `abf-mod-editor-mcp` folder in your user folder:

```powershell
python "$env:USERPROFILE\abf-mod-editor-mcp\install.py" --uninstall
```

Your mods aren't touched.

## Credits

Built on [abf-mod-editor-mcp](https://github.com/theelites11gamer/abf-mod-editor-mcp) by theelites11gamer. Thanks also to the Abiotic Factor modding community for [their guides](https://mod.io/g/abiotic-factor/r).

This is an unofficial fan project, not affiliated with Deep Field Games, Playstack or mod.io.

Want to see how it works or help out? See the [technical details](docs/TECHNICAL.md). MIT licensed, see [LICENSE](LICENSE).

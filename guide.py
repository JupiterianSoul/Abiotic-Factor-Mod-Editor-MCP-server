"""Modding knowledge served by the modding_guide tool, so a client can help someone who is new to modding."""

SOURCES = "Community guides: https://mod.io/g/abiotic-factor/r"

TOPICS = {
    "workflow": """Making a mod from an idea:
1. Check it's possible (topic 'limits'). Say up front if you need files from the user, such as a 3D model.
2. Call editor_status. If no suitable mod is open, the user creates one: in the Mod Browser, ITEMS tile, then a template, a name (letters and digits only), then Create. Only one mod can be opened per editor launch.
3. Build it, saving only inside that mod (topics 'rows', 'blueprints', 'deployables').
4. Call test_mod. It saves, runs the checks, loads the Facility map and starts Play. Tell the user exactly what to look at in-game.
5. Only when the user says it works, walk them through uploading (topic 'upload'). The user clicks every upload button.""",
    "rows": """DataTable rows:
- Base tables can't be edited. A mod adds one asset per row, at /<Mod>/DataTables/<Table>/<RowName>, of a *ModRowAsset class.
- Use find_game_content to turn what the user calls something into a row name.
- To change a vanilla row: use tweak_game_row. It copies the whole row as an override, because fields left out of an uncopied row become blank defaults, which can break the vanilla row.
- To add something new: use new_row_from, then add a recipe row if it should be craftable.
- verify_mod asks the game's own lookup whether each row is active. explain_mod shows what changed compared with vanilla.
- A row that refers to another row in the same mod uses <mod_prefix>_<row_name>. list_mods shows the prefix. Base-game row names have no prefix.
- Not every table can be added to: the available ones are those listed when creating a row.
- Copying a row asset can keep the old row name, and rows that share a name collide. The editor warns only once per session, so run check_mod_rows.""",
    "testing": """Testing:
- test_mod does the local test in one call, including verify_mod. Press Esc in the game window, or call play_in_editor with action 'stop', to end it.
- verify_mod confirms the game's lookup returns a row. It doesn't prove how it plays, so still ask the user to try anything that depends on gameplay.
- The backslash key opens the in-game cheat menu. Ask the user to press it, because keyboard layouts differ.
- Playing in Facility creates an autosave called Cascade. clear_test_save moves it away when old save data could affect a test.
- Play In Editor runs inside the editor. It's a good test of a mod's logic, but not of the packaged result. Mods are cooked on mod.io's servers, so there is no local .pak to copy into the game, and the real game needs an upload. Listings can stay private for this.""",
    "upload": """Uploading (the user clicks every button; never upload for them):
1. The user must be logged in to mod.io, not only Epic, when the editor starts. Otherwise uploads fail with vague errors.
2. Listing image: 16:9, at least 512x288, under 8 MB. check_listing_image tests one and make_listing_image makes a placeholder. The images in the mod's Media folder are too small.
3. Run the checks: check_upload, blueprint_filter_check and audit_mod. audit_mod results also appear in the Message Log, and clear that log between runs.
4. Call open_mod_manager, or the user clicks the test tube icon then Manage Mod. Choose Create New Mod, or Use Existing Mod with the ID from the mod's page.
5. Name, summary (up to 250 characters), image. Leave Public Mod unticked to keep it private. The user clicks Create Mod.
6. Version, changelog, platforms, then Validate, then Upload Mod. The window closing afterwards is normal.
7. On the mod's mod.io page, Files > Cloud Cooking shows the progress, normally one cook per platform. Queued usually takes 5 to 10 minutes. If a cook fails, View details has the log.
8. Visibility on the mod's settings page controls who can see it. To update a mod, repeat step 6 with a newer version.
The panel's errors are often generic: explain_upload_error usually finds the real reason. If an upload fails, call it first.""",
    "limits": """What mods can do:
- Add or override rows in most DataTables: items, buffs, NPCs, recipes and more.
- New Blueprints, by child class or by duplicating. A Blueprint may spawn actors or change a level during play.
- NPC spawns through DT_NPCSpawns, and entity encounters like the Coworker and Leyak through DT_ClassManager.
- New models, textures and animations, using files from the user.
What they can't do:
- Change anything under /Game. Everything lives in the mod's own Content folder.
- Add or directly edit levels.
- Use Blueprint nodes blocked by the upload filter (blueprint_filter_check).
- Change Global Static Switch Parameter Values on a material: the upload fails for consoles.
- Include .md files in the mod folder: Upload zips the whole folder, and mod.io rejects them.
Ask the user for: an .fbx model and textures for a new look (reusing a game mesh needs nothing), audio files for new sounds. Custom costumes are an advanced job: offer a retexture or stat change first.""",
    "starters": """Common jobs for a first mod (always use find_game_content first):
- Cheaper or better recipe: tweak_game_row on the recipe row, with field_text for recipe_items.
- Stronger weapon or tool: tweak_game_row on the item's row. Read it first with get_game_row to find the field names.
- Bigger stacks or more durability: tweak_game_row on the item's row.
- New variant of an item: new_row_from the closest item, change its name and values, then new_row_from a similar recipe with item_to_create set to <mod_prefix>_<new_row>.
- Stronger or weaker enemy: tweak_game_row on the NPC's row.
- Furniture: see topic 'deployables'. Official templates: list_mod_templates.
Before big changes, call backup_mod. Finish with test_mod.""",
    "blueprints": """Blueprints:
- Use a child class when game systems look for a parent in the class chain (for example NPC_Soldier_Grunt). Duplicate for NPCs with no child classes (for example Coworker) or Animation Blueprints. Only Blueprints that include source can be duplicated.
- Functions can be overridden in a child Blueprint. Buff Objects and Buff Actors are powerful and include source.
- Build logic with build_graph, which checks every pin against the editor. Paste custom events and compile before pasting what calls them. New nodes can't link to nodes already in a graph.
- build_graph, paste_graph, discover_pins and open_mod use the clipboard, mouse and keyboard, so tell the user to leave the PC alone during them.
- Never T3D-export a /Game Blueprint: it crashes the editor. Calling UGCTemplateSubsystem from Python crashed it too.""",
    "deployables": """Deployables (furniture):
- Import the model with import_asset and make materials, or reuse a game mesh.
- Create the Blueprint and set FurnitureMesh.
- On the row: Deployed Item Class and Deploy Hologram Mesh.
- Back on the Blueprint: Deconstructed Item Data.
- Add a recipe row if it should be craftable.""",
}


def get(topic=None):
    """One topic, or the list of topics when none is given."""
    if not topic:
        return "Topics: " + ", ".join(TOPICS) + ".\n\n" + TOPICS["workflow"] + "\n\n" + SOURCES
    text = TOPICS.get(str(topic).lower())
    if text is None:
        return f"Unknown topic '{topic}'. Topics: " + ", ".join(TOPICS) + "."
    return text + "\n\n" + SOURCES

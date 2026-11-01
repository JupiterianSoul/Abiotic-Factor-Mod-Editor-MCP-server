"""Checks for the write guards, log masking, listing images and guide. Needs no editor.

    python -I test_safety.py
"""

import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backups        # noqa: E402
import guide          # noqa: E402
import listing_image  # noqa: E402
import safety         # noqa: E402
import upload_help    # noqa: E402


class Paths(unittest.TestCase):
    def test_mod_paths_are_allowed(self):
        for p in ("/MyMod", "/MyMod/DataTables/DT_Recipes/row", "/GameplayMod/Row"):
            self.assertIsNone(safety.base_path_problem(p), p)

    def test_base_and_odd_paths_are_refused(self):
        for p in ("/Game", "/Game/Maps/Facility", "/game/maps/x", "/GAME/x", "/Engine/x", "/Script/Engine.Actor",
                  "/MyMod/../Game/x", "/MyMod//x", "/MyMod/./x", "C:\\mods\\x", "MyMod/x", "", None):
            self.assertIsNotNone(safety.base_path_problem(p), p)


class Redact(unittest.TestCase):
    def test_secrets_are_hidden(self):
        line = ('LogInit: Command Line: -AUTH_LOGIN=abc -AUTH_PASSWORD=s3cretvalue -AUTH_TYPE=exchangecode '
                '-epicusername="Some Name" -epicuserid=1234567890abcdef1234567890abcdef')
        out = safety.redact(line)
        for secret in ("s3cretvalue", "Some Name", "1234567890abcdef"):
            self.assertNotIn(secret, out)
        self.assertTrue(out.startswith("LogInit: "))

    def test_urls_and_tokens_are_hidden(self):
        out = safety.redact("GET g-13105.modapi.io/v1/me?api_key=deadbeef https://x.io/y?api_key=deadbeef2 "
                            "Authorization: Bearer abcdef me@example.com access_token=zzz")
        for secret in ("deadbeef", "deadbeef2", "abcdef", "me@example.com", "zzz"):
            self.assertNotIn(secret, out)

    def test_useful_errors_stay_readable(self):
        line = ('LogModio: {"error":{"code":422,"error_ref":13009,"errors":{"logo":"The logo has invalid image '
                'dimensions."}}}')
        out = safety.redact(line)
        for keep in ("422", "13009", "invalid image dimensions"):
            self.assertIn(keep, out)
        self.assertIn("/Game/Maps/Facility_Office1_LongEnoughToLookLikeAToken", safety.redact(
            "Loaded /Game/Maps/Facility_Office1_LongEnoughToLookLikeAToken"))


class Listing(unittest.TestCase):
    def test_made_image_passes(self):
        with tempfile.TemporaryDirectory() as d:
            r = listing_image.check(listing_image.make(Path(d) / "sub" / "logo.png"))
            self.assertTrue(r["ok"], r)
            self.assertEqual((r["width"], r["height"]), (1024, 576))

    def test_bad_images_fail(self):
        with tempfile.TemporaryDirectory() as d:
            small = Path(d) / "small.png"
            small.write_bytes(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 128, 128))
            r = listing_image.check(small)
            self.assertFalse(r["ok"])
            self.assertEqual(len(r["problems"]), 2)
            self.assertFalse(listing_image.check(Path(d) / "missing.png")["ok"])
            other = Path(d) / "notes.txt"
            other.write_text("hello")
            self.assertFalse(listing_image.check(other)["ok"])

    def test_jpeg_size(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.jpg"
            p.write_bytes(b"\xff\xd8\xff\xe0\x00\x04\x00\x00\xff\xc0\x00\x11\x08" + struct.pack(">HH", 576, 1024) + b"\x00" * 8)
            self.assertEqual(listing_image.image_size(p), (1024, 576))


class Backups(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "backups"
        self.mod = Path(self.tmp.name) / "mods" / "MyMod"
        self.mod.mkdir(parents=True)
        (self.mod / "MyMod.uplugin").write_text("{}")
        (self.mod / "row.uasset").write_text("v1")

    def tearDown(self):
        self.tmp.cleanup()

    def test_backup_and_restore(self):
        backups.backup(self.mod, "first try!", root=self.root)
        (self.mod / "row.uasset").write_text("v2")
        (self.mod / "extra.uasset").write_text("new")
        r = backups.restore(self.mod, root=self.root)
        self.assertEqual((self.mod / "row.uasset").read_text(), "v1")
        self.assertFalse((self.mod / "extra.uasset").exists())
        self.assertEqual((Path(r["previous_version_kept_at"]) / "row.uasset").read_text(), "v2")
        self.assertEqual(len(backups.list_backups("MyMod", self.root)), 1)

    def test_same_second_backups_dont_collide(self):
        a = backups.backup(self.mod, root=self.root)
        b = backups.backup(self.mod, root=self.root)
        self.assertNotEqual(a, b)

    def test_refusals(self):
        with self.assertRaises(ValueError):
            backups.backup(self.mod.parent, root=self.root)
        with self.assertRaises(ValueError):
            backups.restore(self.mod, root=self.root)
        backups.backup(self.mod, root=self.root)
        with self.assertRaises(ValueError):
            backups.restore(self.mod, "../../secret", root=self.root)
        self.assertTrue((self.mod / "row.uasset").exists())

    def test_clear_save(self):
        saved = Path(self.tmp.name) / "Saved"
        (saved / "SaveGames" / "Editor" / "Worlds" / "Cascade").mkdir(parents=True)
        (saved / "SaveGames" / "Editor" / "Worlds" / "Cascade" / "a.sav").write_text("x")
        r = backups.clear_save(saved, root=self.root)
        self.assertEqual(r["moved"], ["Worlds"])
        self.assertFalse((saved / "SaveGames" / "Editor" / "Worlds" / "Cascade").exists())
        self.assertTrue((Path(r["kept_at"]) / "Worlds" / "a.sav").exists())
        self.assertEqual(backups.clear_save(saved, root=self.root)["moved"], [])


class UploadHelp(unittest.TestCase):
    def test_known_causes(self):
        line = 'LogModio: [Error][Http] Non 200-204 response received: {"error":{"code":422,"errors":{"logo":"The logo has invalid image dimensions."}}}'
        r = upload_help.explain([line, "LogModio: [Info] fine"])
        self.assertIn("listing image", r["causes"][0]["cause"])
        self.assertEqual(len(r["error_lines"]), 1)

    def test_unknown_and_clean(self):
        self.assertIn("Nothing matched", upload_help.explain(["LogModio: [Error] something odd"])["note"])
        self.assertIn("No upload errors", upload_help.explain(["LogModio: [Info] ok"])["note"])
        self.assertEqual(upload_help.explain(["[Error][File] Raw MS filesystem error 3 received"])["causes"], [])


class Guide(unittest.TestCase):
    def test_topics(self):
        self.assertIn("rows", guide.get())
        for topic in guide.TOPICS:
            self.assertGreater(len(guide.get(topic)), 100)
        self.assertIn("Unknown topic", guide.get("nope"))


class Server(unittest.TestCase):
    def test_tools_and_guards(self):
        import server
        names = {t[0] for t in server.TOOLS}
        self.assertTrue({"test_mod", "check_mod_rows", "audit_mod", "open_mod_manager", "modding_guide",
                         "check_listing_image", "make_listing_image", "verify_mod", "explain_mod", "find_game_content",
                         "tweak_game_row", "new_row_from", "backup_mod", "restore_mod", "list_backups", "clear_test_save",
                         "explain_upload_error", "import_asset"} <= names)
        for bad in ("/Game/x", "/game/x", "/MyMod/../Game/x"):
            for call in (lambda: server.t_save_assets({"asset_paths": [bad]}),
                         lambda: server.t_compile_blueprint({"asset_path": bad}),
                         lambda: server.t_set_row({"asset_path": bad}),
                         lambda: server.t_delete_asset({"asset_path": bad}),
                         lambda: server.t_create_row_asset({"asset_path": bad}),
                         lambda: server.t_import_asset({"file": __file__, "destination_path": bad})):
                with self.assertRaises(server.RemoteError):
                    call()

    def test_log_name_cant_leave_the_logs_folder(self):
        import server
        self.assertEqual(server.log_file("..\\..\\secret.txt").parent, server.SAVED_DIR / "Logs")
        self.assertEqual(server.log_file("../../secret.txt").name, "secret.txt")
        self.assertEqual(server.log_file("../../secret.txt").parent, server.SAVED_DIR / "Logs")

    def test_keys(self):
        import wininput
        self.assertEqual(wininput._vk("alt"), 0x12)
        self.assertEqual(wininput._vk("p"), ord("P"))
        self.assertEqual(wininput._vk("7"), ord("7"))
        with self.assertRaises(wininput.WinError):
            wininput._vk("notakey")
        # Whatever the layout, these must never turn into the raw character code (0x5C is the Windows key).
        for char in "\\/;'[]":
            try:
                self.assertNotEqual(wininput._vk(char), ord(char), char)
            except wininput.WinError:
                pass


if __name__ == "__main__":
    unittest.main()

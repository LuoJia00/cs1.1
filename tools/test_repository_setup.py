"""Run against an isolated source checkout, never the user's live data."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import config_transfer


class TransferTests(unittest.TestCase):
    def test_roundtrip_preserves_private_records_and_backs_up_settings(self):
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as target_dir:
            source, target = Path(source_dir), Path(target_dir)
            for root, value in [(source, b"example-setting-source"), (target, b"example-setting-target")]:
                (root / "API").mkdir()
                (root / "API/.env").write_bytes(value)
            (source / "history.json").write_text("source history")
            (target / "history.json").write_text("target history")
            archive = config_transfer.backup(source)
            recovery, count = config_transfer.restore(archive, target)
            self.assertEqual(count, 1)
            self.assertEqual((target / "API/.env").read_bytes(), b"example-setting-source")
            self.assertEqual((target / "history.json").read_text(), "target history")
            with zipfile.ZipFile(recovery) as saved:
                self.assertEqual(saved.read("API/.env"), b"example-setting-target")

    def test_rejects_non_config_and_tampered_files_before_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "API").mkdir()
            (root / "API/.env").write_bytes(b"keep-existing")
            for name in ["../main.py", "main.py", "data/conversations/private.json", "API/.env"]:
                archive = root / "invalid.zip"
                manifest = {"format": "infinite-canvas-settings-v1", "files": {name: hashlib.sha256(b"different").hexdigest()}}
                with zipfile.ZipFile(archive, "w") as z:
                    z.writestr("manifest.json", json.dumps(manifest))
                    z.writestr(name, b"tampered")
                with self.assertRaises(ValueError):
                    config_transfer.restore(archive, root)
                self.assertEqual((root / "API/.env").read_bytes(), b"keep-existing")


class CleanCheckoutTests(unittest.TestCase):
    @unittest.skipUnless(
        Path(__file__).resolve().parents[2].name == ".local-backups"
        and Path(__file__).resolve().parents[1].name.startswith("verify-"),
        "Run this startup check in an isolated verify-* source copy",
    )
    def test_fresh_start_and_update_guards(self):
        import main
        from fastapi.testclient import TestClient
        root = Path(main.BASE_DIR)
        # Refuse accidental use in the real workspace.
        self.assertEqual(root.parent.name, ".local-backups")
        self.assertTrue(root.name.startswith("verify-"))
        with patch.object(main.requests, "get", side_effect=AssertionError("Unexpected network access")):
            with TestClient(main.app) as client:
                self.assertEqual(client.get("/").status_code, 200)
                info = client.get("/api/app-info").json()
                self.assertEqual(info["update_mode"], "git")
                self.assertEqual(info["repo_url"], "https://github.com/LuoJia00/cs1.1")
                self.assertFalse(client.get("/api/check-update").json()["update_available"])
                for source in ["github", "modelscope"]:
                    response = client.post("/api/update-from-github", json={"source": source, "fallback": True})
                    self.assertEqual(response.status_code, 409)
                self.assertEqual(client.get("/static/canvas.html").status_code, 200)
                self.assertEqual(client.get("/api/providers").status_code, 200)


if __name__ == "__main__":
    unittest.main()

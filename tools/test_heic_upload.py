import asyncio
from io import BytesIO
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from starlette.datastructures import Headers

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main


class HeicUploadTests(unittest.TestCase):
    @staticmethod
    def heic_bytes():
        source = BytesIO()
        Image.new("RGB", (8, 6), (220, 40, 30)).save(source, format="HEIF", quality=90)
        return source.getvalue()

    def test_heic_is_converted_to_browser_safe_jpeg(self):
        self.assertEqual(main._local_upload_kind_ext("IMG_2012.HEIC", "audio/heic"), ("image", ".heic"))
        data, name, mime = main.normalize_heif_upload(self.heic_bytes(), "IMG_2012.HEIC", "audio/heic")

        self.assertEqual(name, "IMG_2012.jpg")
        self.assertEqual(mime, "image/jpeg")
        with Image.open(BytesIO(data)) as converted:
            self.assertEqual(converted.format, "JPEG")
            self.assertEqual(converted.size, (8, 6))

    def test_upload_endpoint_returns_image_even_with_wrong_audio_mime(self):
        upload = main.UploadFile(
            filename="IMG_2012.HEIC",
            file=BytesIO(self.heic_bytes()),
            headers=Headers({"content-type": "audio/heic"}),
        )
        with tempfile.TemporaryDirectory() as folder:
            output_path = lambda name, _category="input": str(Path(folder) / name)
            output_url = lambda name, _category="input": f"/assets/input/{name}"
            with patch.object(main, "output_path_for", side_effect=output_path), patch.object(main, "output_url_for", side_effect=output_url):
                result = asyncio.run(main.upload_ai_reference([upload]))

            item = result["files"][0]
            self.assertEqual(item["kind"], "image")
            self.assertEqual(item["mime"], "image/jpeg")
            self.assertTrue(item["url"].endswith(".jpg"))
            with Image.open(Path(folder) / item["url"].rsplit("/", 1)[-1]) as converted:
                self.assertEqual(converted.format, "JPEG")


if __name__ == "__main__":
    unittest.main()

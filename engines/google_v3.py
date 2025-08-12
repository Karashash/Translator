import os, time
from typing import List
from google.cloud import translate

def is_google_ready() -> bool:
    return bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

class GoogleV3Translator:
    def __init__(self, project_id: str = None, location: str = "global"):
        self.client = translate.TranslationServiceClient()
        project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
        if not project_id:
            raise RuntimeError(
                "project_id"
            )
        self.parent = f"projects/{project_id}/locations/{location}"

    def translate_html(self, texts: List[str], source: str, target: str) -> List[str]:
        out, start = [], 0
        while start < len(texts):
            batch = texts[start:start+32]
            resp = self._call(batch, source, target)
            out.extend([t.translated_text for t in resp.translations])
            start += len(batch)
            time.sleep(0.05)
        return out

    def _call(self, texts: List[str], source: str, target: str):
        request = {
            "parent": self.parent,
            "contents": texts,
            "mime_type": "text/html",
            "source_language_code": source,
            "target_language_code": target,
        }
        return self.client.translate_text(request=request)

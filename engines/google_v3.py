import os, time, json
from typing import List, Optional
from google.cloud import translate
from google.oauth2 import service_account

try:
    import streamlit as st
except Exception:
    st = None

def is_google_ready() -> bool:
    """Проверяем, что есть либо secrets, либо переменная окружения с ключом/ADC."""
    if st and ("gcp_service_account" in st.secrets or "gcp_service_account_json" in st.secrets):
        return True
    return bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT"))

def _load_credentials_and_project():
    """Возвращает (creds, project_id). creds может быть None, если используем ADC по файлу."""
    project_id = None
    creds = None

    if st:
        if "gcp_service_account" in st.secrets:
            info = dict(st.secrets["gcp_service_account"])
            project_id = info.get("project_id")
            creds = service_account.Credentials.from_service_account_info(info)
        elif "gcp_service_account_json" in st.secrets:
            info = json.loads(st.secrets["gcp_service_account_json"])
            project_id = info.get("project_id")
            creds = service_account.Credentials.from_service_account_info(info)
        if not project_id:
            project_id = st.secrets.get("gcp_project") or st.secrets.get("GOOGLE_CLOUD_PROJECT") or st.secrets.get("GCP_PROJECT")

    if not creds:
        project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
        creds = None

    if not project_id:
        raise RuntimeError("Не задан project_id. Укажи его в secrets (gcp_project) или переменной окружения GOOGLE_CLOUD_PROJECT/GCP_PROJECT.")

    return creds, project_id

class GoogleV3Translator:
    def __init__(self, project_id: str = None, location: str = "global"):
        creds, proj = _load_credentials_and_project()
        self.project_id = project_id or proj
        if creds is not None:
            self.client = translate.TranslationServiceClient(credentials=creds)
        else:
            self.client = translate.TranslationServiceClient()  
        self.parent = f"projects/{self.project_id}/locations/{location}"

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

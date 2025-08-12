import os, time, json
from typing import List, Optional
from google.cloud import translate
from google.oauth2 import service_account

try:
    import streamlit as st 
except Exception:
    st = None

def is_google_ready() -> bool:
    if st:
        if "gcp" in st.secrets and st.secrets["gcp"].get("key"):
            return True
        if "gcp_service_account_json" in st.secrets:
            return True
        if "gcp_service_account" in st.secrets:
            return True
        if st.secrets.get("gcp_project"):
            return True
    return bool(
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCP_PROJECT")
    )

def _load_credentials_project_location():
    """Возвращает (creds, project_id, location). creds может быть None, если используем ADC."""
    creds = None
    project_id: Optional[str] = None
    location = "global"

    if st:
        if "gcp" in st.secrets:
            g = st.secrets["gcp"]
            project_id = g.get("project") or g.get("project_id") or project_id
            location   = g.get("location", location)
            key_json   = g.get("key")
            if key_json:
                info = json.loads(key_json)
                if "private_key" in info and "\\n" in info["private_key"]:
                    info["private_key"] = info["private_key"].replace("\\n", "\n")
                creds = service_account.Credentials.from_service_account_info(info)

        if creds is None and "gcp_service_account_json" in st.secrets:
            info = json.loads(st.secrets["gcp_service_account_json"])
            if "private_key" in info and "\\n" in info["private_key"]:
                info["private_key"] = info["private_key"].replace("\\n", "\n")
            project_id = project_id or info.get("project_id")
            creds = service_account.Credentials.from_service_account_info(info)

        if creds is None and "gcp_service_account" in st.secrets:
            info = dict(st.secrets["gcp_service_account"])
            if "private_key" in info and "\\n" in info["private_key"]:
                info["private_key"] = info["private_key"].replace("\\n", "\n")
            project_id = project_id or info.get("project_id")
            creds = service_account.Credentials.from_service_account_info(info)

        project_id = project_id or st.secrets.get("gcp_project") or st.secrets.get("GOOGLE_CLOUD_PROJECT") or st.secrets.get("GCP_PROJECT")
        location   = st.secrets.get("location", location)

    if creds is None:
        project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
        location   = os.environ.get("GCP_LOCATION", location)

    if not project_id:
        raise RuntimeError("Не задан project_id. Укажи [gcp].project в secrets, либо gcp_project, либо GOOGLE_CLOUD_PROJECT/GCP_PROJECT.")

    return creds, project_id, location

class GoogleV3Translator:
    def __init__(self, project_id: str = None, location: str = None):
        creds, proj, loc = _load_credentials_project_location()
        self.project_id = project_id or proj
        self.location   = location or loc or "global"
        self.parent     = f"projects/{self.project_id}/locations/{self.location}"
        self.client     = translate.TranslationServiceClient(credentials=creds) if creds else translate.TranslationServiceClient()

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

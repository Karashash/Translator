import os, io, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import streamlit as st
from utils.glossary import load_glossary
from translator_core import translate_docx
from engines.google_v3 import GoogleV3Translator, is_google_ready

st.set_page_config(page_title="DocxTranslator", layout="centered")
st.title("DocxTranslator")

with st.expander("Параметры"):
    col1, col2 = st.columns(2)
    with col1:
        src_lang = st.selectbox("Исходный язык", ["ru", "kk", "en"], index=0)
    with col2:
        tgt_lang = st.selectbox("Целевой язык", ["kk", "ru", "en"], index=1)
    aggressive_cleanup = st.checkbox("Легкая очистка пробелов и мусорных символов", value=True)
    use_glossary = st.checkbox("Использовать глоссарий (csv)", value=False)
    glossary_file = None
    if use_glossary:
        glossary_file = st.file_uploader("Загрузить csv с колонками source,target", type=["csv"])

uploaded = st.file_uploader("Загрузить .docx", type=["docx"])

if not is_google_ready():
    st.info("Нужна GOOGLE_APPLICATION_CREDENTIALS")
if not (os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")):
    st.info("Укажи проект")

if uploaded and st.button("Перевести"):
    data = uploaded.read()
    glossary = None
    if use_glossary and glossary_file:
        glossary = load_glossary(glossary_file)

    translator = GoogleV3Translator()

    with st.spinner("Переводим"):
        out_buf = io.BytesIO()
        translate_docx(
            input_bytes=data,
            output=out_buf,
            translator=translator,
            src_lang=src_lang,
            tgt_lang=tgt_lang,
            aggressive_cleanup=aggressive_cleanup,
            glossary=glossary,
        )
        out_buf.seek(0)
        st.success("")
        st.download_button(
            "Скачать",
            out_buf,
            file_name="translated.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

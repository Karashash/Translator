import io
from typing import Optional, Dict, List, Any
from docx import Document
from bs4 import BeautifulSoup, NavigableString
from utils.docx_io import iter_all_paragraphs, iter_all_tables, replace_paragraph_text_from_spans, replace_cell_text_from_spans
from utils.chunking import chunk_texts
from utils.glossary import apply_glossary_pre, apply_glossary_post

HTML_SPAN = "span"

def paragraph_to_html(par):
    pieces = []
    ridx = 0
    for run in par.runs:
        text = run.text or ""
        if text == "":
            ridx += 1
            continue
        open_tags, close_tags = "", ""
        if run.bold:
            open_tags += "<b>"; close_tags = "</b>" + close_tags
        if run.italic:
            open_tags += "<i>"; close_tags = "</i>" + close_tags
        if run.underline:
            open_tags += "<u>"; close_tags = "</u>" + close_tags
        pieces.append(f'{open_tags}<span data-r="{ridx}">{html_escape(text)}</span>{close_tags}')
        ridx += 1
    return "".join(pieces)

def cell_to_html(cell):
    parts = []
    for p in cell.paragraphs:
        parts.append(paragraph_to_html(p))
    return "<br/>".join(parts)

def html_escape(s: str):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def parse_spans_from_html(html: str):
    from bs4 import BeautifulSoup, NavigableString

    soup = BeautifulSoup(html or "", "lxml")

    for br in soup.find_all("br"):
        br.replace_with(NavigableString("\n"))

    out = []

    def walk(node):
        for child in getattr(node, "children", []):
            if isinstance(child, NavigableString):
                parent = getattr(child, "parent", None)
                if not (getattr(parent, "name", None) == "span" and parent.has_attr("data-r")):
                    txt = str(child)
                    if txt:
                        out.append((None, txt))
                continue

            if getattr(child, "name", None) == "span" and child.has_attr("data-r"):
                try:
                    rid = int(child["data-r"])
                except Exception:
                    rid = None
                txt = child.get_text()
                if txt:
                    out.append((rid, txt))
                continue

            walk(child)

    walk(soup)

    coalesced = []
    for rid, txt in out:
        if coalesced and coalesced[-1][0] == rid:
            coalesced[-1] = (rid, coalesced[-1][1] + txt)
        else:
            coalesced.append((rid, txt))
    return coalesced


def translate_docx(
    input_bytes: bytes,
    output: io.BytesIO,
    translator,
    src_lang: str,
    tgt_lang: str,
    aggressive_cleanup: bool = True,
    glossary: Optional[Dict[str, str]] = None,
):
    doc = Document(io.BytesIO(input_bytes))

    items: List[Dict[str, Any]] = []
    for par in iter_all_paragraphs(doc):
        html = paragraph_to_html(par)
        items.append({"kind": "p", "obj": par, "html": html})
    for cell in iter_all_tables(doc):
        html = cell_to_html(cell)
        items.append({"kind": "cell", "obj": cell, "html": html})

    original_htmls: List[str] = [it["html"] or "" for it in items]
    texts = original_htmls[:]
    if glossary:
        texts = [apply_glossary_pre(t, glossary) for t in texts]

    translate_indices: List[int] = []
    texts_for_api: List[str] = []
    for i, t in enumerate(texts):
        if t is not None and str(t).strip() != "":
            translate_indices.append(i)
            texts_for_api.append(t)
    if not texts_for_api:
        doc.save(output)
        return

    translated_flat: List[str] = []
    for batch in chunk_texts(texts_for_api, max_chars=18000, max_items=64):
        translated_flat.extend(
            translator.translate_html(batch, source=src_lang, target=tgt_lang)
        )

    translated_htmls: List[str] = original_htmls[:]
    k = 0
    for idx in translate_indices:
        translated_htmls[idx] = translated_flat[k]
        k += 1

    if glossary:
        translated_htmls = [apply_glossary_post(t, glossary) for t in translated_htmls]

    for it, translated in zip(items, translated_htmls):
        spans = parse_spans_from_html(translated or "")
        if it["kind"] == "p":
            replace_paragraph_text_from_spans(it["obj"], spans)
        else:
            replace_cell_text_from_spans(it["obj"], spans)

    doc.save(output)


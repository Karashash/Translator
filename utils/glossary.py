import csv
from io import StringIO, TextIOWrapper
from typing import Dict

def load_glossary(file) -> Dict[str, str]:
    if isinstance(file, (StringIO, TextIOWrapper)):
        content = file.read()
    else:
        content = file.getvalue().decode("utf-8", errors="ignore")
    rdr = csv.reader(StringIO(content))
    mapping = {}
    for row in rdr:
        if not row:
            continue
        parts = [p.strip() for p in row]
        if len(parts) >= 2 and parts[0] and parts[1]:
            mapping[parts[0]] = parts[1]
    return mapping

def apply_glossary_pre(text: str, glossary: Dict[str, str]) -> str:
    for k, v in glossary.items():
        text = text.replace(k, f"«{v}»")
    return text

def apply_glossary_post(text: str, glossary: Dict[str, str]) -> str:
    for _, v in glossary.items():
        text = text.replace(f"«{v}»", v)
    return text

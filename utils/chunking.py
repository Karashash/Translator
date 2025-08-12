from typing import Iterable, List

def chunk_texts(items: List[str], max_chars: int = 18000, max_items: int = 64) -> Iterable[List[str]]:
    batch, total = [], 0
    for s in items:
        s = s or ""
        if batch and (total + len(s) > max_chars or len(batch) >= max_items):
            yield batch
            batch, total = [], 0
        batch.append(s); total += len(s)
    if batch:
        yield batch

"""Small instructor-provided lexical retriever for the fictional corpus."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

from .models import PolicyPassage

TOKEN_RE = re.compile(r"[a-z0-9_]+")


def _tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


class PolicyRetriever:
    """A compact BM25 implementation; students use but do not reimplement it."""

    def __init__(self, corpus_path: str | Path):
        raw = json.loads(Path(corpus_path).read_text())
        self.passages = [PolicyPassage.model_validate(item) for item in raw]
        self.documents = [_tokens(p.text) for p in self.passages]
        self.average_length = sum(map(len, self.documents)) / max(
            len(self.documents), 1
        )
        self.document_frequency = Counter()
        for document in self.documents:
            self.document_frequency.update(set(document))

    def search(
        self,
        query: str,
        *,
        document_types: list[str] | None = None,
        top_k: int = 5,
    ) -> list[PolicyPassage]:
        query_tokens = _tokens(query)
        scores: list[tuple[float, PolicyPassage]] = []
        total = len(self.passages)
        k1, b = 1.5, 0.75

        for passage, document in zip(self.passages, self.documents, strict=True):
            if document_types and passage.document_type not in document_types:
                continue
            frequencies = Counter(document)
            score = 0.0
            for token in query_tokens:
                frequency = frequencies[token]
                if not frequency:
                    continue
                df = self.document_frequency[token]
                idf = math.log(1 + (total - df + 0.5) / (df + 0.5))
                denominator = frequency + k1 * (
                    1 - b + b * len(document) / self.average_length
                )
                score += idf * frequency * (k1 + 1) / denominator
            if score > 0:
                scores.append((score, passage))

        scores.sort(key=lambda item: (-item[0], item[1].passage_id))
        return [
            passage.model_copy(update={"score": score})
            for score, passage in scores[:top_k]
        ]

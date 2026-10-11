"""Bounded retrieval of creator-authored world details; never user memory."""

import re


def _terms(value: str) -> set[str]:
    words = set(re.findall(r"[a-z0-9_]{2,}", value.casefold()))
    # Bigrams support Japanese and Korean without requiring a tokenizer service.
    for run in re.findall(r"[^\W\d_a-zA-Z]+", value):
        words.update(run[i : i + 2] for i in range(len(run) - 1))
    return words


def select_world_book(book: str, query: str, budget: int = 3000) -> str:
    """Keep a short introduction and rank bounded passages against the turn."""
    if budget <= 0:
        return ""
    book = book[:10000]
    if len(book) <= budget:
        return book
    chunks = [book[i : i + 500] for i in range(0, len(book), 500)]
    terms = _terms(query)
    ranked = sorted(range(1, len(chunks)), key=lambda i: (-len(terms & _terms(chunks[i])), i))
    selected = [0]
    remaining = budget - len(chunks[0])
    for index in ranked:
        if len(chunks[index]) + 1 <= remaining:
            selected.append(index)
            remaining -= len(chunks[index]) + 1
    return "\n".join(chunks[i] for i in sorted(selected))[:budget]

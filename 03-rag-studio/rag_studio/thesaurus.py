"""A small, opinionated thesaurus used for demo-mode query rewriting.

When no API key is available the retriever can't ask a model for alternative
queries, so it expands the question with synonyms instead: tokens in this table
grow into related terms from the bundled corpus vocabulary. Expansion is only
ever additive — merged retrieval keeps the best score per chunk, so a synonym
that pulls in noise cannot outrank a direct lexical match.
"""

from __future__ import annotations

from rag_studio.text import tokenize

# Keys must be tokenizer-normalized forms ("packets" -> "packet"); values are
# appended verbatim and re-normalized when the expanded query is tokenized.
THESAURUS: dict[str, tuple[str, ...]] = {
    "internet": ("network", "web", "routers"),
    "web": ("website", "site", "browser"),
    "website": ("domain", "site", "web"),
    "packet": ("packets", "routing", "tcp"),
    "tcp": ("transmission control", "retransmission", "ip"),
    "ip": ("ipv4", "address", "routing"),
    "router": ("routing", "hop", "routers"),
    "dns": ("domain name", "resolver", "lookup"),
    "domain": ("dns", "hostname", "name"),
    "lookup": ("dns", "resolver", "query"),
    "cache": ("caching", "ttl", "stored"),
    "ttl": ("time to live", "cache", "expiry"),
    "browser": ("render", "web page", "html"),
    "http": ("https", "request", "status code", "tls", "certificate", "secure"),
    "certificate": ("certificate authority", "tls", "padlock"),
    "encrypt": ("encryption", "tls", "keys"),
    "encryption": ("tls", "keys", "secure"),
    "password": ("hash", "salt", "credentials"),
    "cookie": ("cookies", "tracking", "session"),
    "wifi": ("wireless", "radio", "2.4 ghz"),
    "wireless": ("wifi", "radio waves", "signals"),
    "fiber": ("optic", "light", "cables"),
    "cable": ("ethernet", "fiber", "wire"),
    "datacenter": ("servers", "racks", "cdn"),
    "cdn": ("cache", "servers", "edge"),
    "status": ("code", "http", "404"),
    "404": ("not found", "status code", "error"),
}


def expansions(query: str) -> list[str]:
    """Return rewritten variants of `query`: the original plus one expanded copy.

    The expanded copy appends synonyms for every token the thesaurus knows;
    when nothing matches (or the question is already saturated) the list is
    just `[query]` so callers can treat "no expansion" uniformly.
    """
    tokens = tokenize(query)
    extra: list[str] = []
    for token in tokens:
        for synonym in THESAURUS.get(token, ()):
            if synonym not in tokens and synonym not in extra:
                extra.append(synonym)
    if not extra:
        return [query]
    return [query, f"{query} {' '.join(extra)}"]

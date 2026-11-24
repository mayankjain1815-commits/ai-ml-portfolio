"""The public repositories orbiting the landing page's word ring.

One record per repository, with the live metadata checked from the GitHub API
on 2026-11-24. `word_atlas/data.py` stays the source of truth for the ten
concept words; this module is the source of truth for the repository ring.
"""

from .data import PALETTE

# Metadata snapshot date — shown in the UI so nobody mistakes it for live data.
SNAPSHOT = "2026-11-24"

CATEGORY_COLORS = {
    "Security": PALETTE["magenta"],
    "Agents": PALETTE["violet"],
    "Finance": PALETTE["lime"],
    "Developer Tools": PALETTE["cyan"],
    "Infrastructure": PALETTE["violet"],
    "Data": PALETTE["cyan"],
    "Civic": PALETTE["lime"],
    "Portfolio": PALETTE["magenta"],
    "Operations": PALETTE["cyan"],
    "Hackathon": PALETTE["lime"],
    "Media": PALETTE["violet"],
}


def _repo(slug, name, short, description, language, stars, updated, category,
          stack, highlights, words, systems, command, note="", kind="original"):
    return {
        "slug": slug,
        "name": name,
        "short": short,
        "description": description,
        "language": language,
        "stars": stars,
        "updated": updated,
        "url": f"https://github.com/mayankjain1815-commits/{name}",
        "category": category,
        "color": CATEGORY_COLORS.get(category, PALETTE["cyan"]),
        "stack": stack,
        "highlights": highlights,
        "words": words,
        "systems": systems,
        "command": command,
        "note": note,
        "kind": kind,
    }


REPOS = [
    _repo("slop", "AI-Slop-Detector", "SLOP",
          "End-to-end implementation of an AI writing detector.", "Python", 5,
          "2026-10-03", "Security", ["Python", "NLP", "classification"],
          ["Detects machine-like writing patterns in submitted text.",
           "Package the detector behind a small runnable entry point.",
           "Scores and explanations are kept separate so results are inspectable."],
          ["signals", "risk", "skills"], ["neural"],
          "gh repo clone mayankjain1815-commits/AI-Slop-Detector && cd AI-Slop-Detector && python -m pytest -q"),
    _repo("trading", "AI-Trading-Bot", "TRADE",
          "Trading bot that analyses sentiment of live news events and trades accordingly.",
          "HTML", 5, "2026-10-03", "Finance", ["HTML", "JavaScript", "news sentiment"],
          ["Ingests news events and derives a sentiment score.",
           "Turns signals into a documented decision rather than a black-box bet.",
           "Frontend presents the reasoning alongside the action."],
          ["signals", "risk", "forecast"], ["particles"],
          "gh repo clone mayankjain1815-commits/AI-Trading-Bot && cd AI-Trading-Bot"),
    _repo("memory-guard", "Agent-Memory-Guard", "GUARD",
          "Runtime defense that catches AI memory poisoning attacks, even after a context reset.",
          "Python", 4, "2026-10-02", "Security", ["Python", "agents", "runtime policy"],
          ["Treats memory writes as an untrusted boundary.",
           "Detects poisoning that survives a context reset.",
           "Policy decisions are explicit so they can be tested offline."],
          ["agents", "risk", "offline"], ["neural"],
          "gh repo clone mayankjain1815-commits/Agent-Memory-Guard && cd Agent-Memory-Guard && python -m pytest -q"),
    _repo("wallet", "Agent-Wallet-SDK", "WALLET",
          "Non-custodial multi-chain financial infrastructure SDK for autonomous AI agents.",
          "TypeScript", 4, "2026-10-02", "Finance", ["TypeScript", "SDK", "multi-chain"],
          ["Agent-safe wallet primitives with no custody handoff.",
           "Multi-chain interface behind one SDK surface.",
           "Guard rails are part of the API, not an afterthought."],
          ["agents", "skills", "risk"], ["neural"],
          "gh repo clone mayankjain1815-commits/Agent-Wallet-SDK && cd Agent-Wallet-SDK && npm test"),
    _repo("citadel", "CITADEL", "CITADEL",
          "Open-source operating layer for Claude Code and OpenAI Codex — routes and hardens agent requests against real repositories.",
          "JavaScript", 4, "2026-10-19", "Infrastructure", ["JavaScript", "agent routing", "guardrails"],
          ["Routes agent requests through one hardened control plane.",
           "Checks requests against the real repository before execution.",
           "Dependency and workflow alerts are guarded in CI."],
          ["agents", "skills", "offline"], ["particles", "neural"],
          "gh repo clone mayankjain1815-commits/CITADEL && cd CITADEL && npm test"),
    _repo("cleanconnect", "CleanConnect", "CLEAN",
          "Verified waste collection platform with QR + GPS pickup verification, Civic Points, driver routes and admin analytics.",
          "JavaScript", 0, "2026-11-05", "Civic", ["JavaScript", "QR", "GPS", "analytics"],
          ["Closes the loop from pickup proof to civic reward.",
           "Driver routes and admin analytics share one data model.",
           "Newest public repository in this orbit."],
          ["signals", "iot", "demo"], ["globe"],
          "gh repo clone mayankjain1815-commits/CleanConnect && cd CleanConnect"),
    _repo("doclify", "Doclify", "DOCS",
          "AI agent that documents software projects by scanning a codebase and building structured per-file context.",
          "Python", 4, "2026-11-04", "Developer Tools", ["Python", "AST", "documentation"],
          ["Scans a repository and builds per-file structured context.",
           "Documentation is generated from real code, not guessed prose.",
           "Output is inspectable and versionable."],
          ["agents", "skills", "rag"], ["neural"],
          "gh repo clone mayankjain1815-commits/Doclify && cd Doclify && python -m pytest -q"),
    _repo("feature-engine", "Feature-Engine", "FEATURES",
          "Python library with multiple transformers to engineer and select features for machine learning models.",
          "Python", 5, "2026-10-05", "Data", ["Python", "transformers", "feature selection"],
          ["Composable transformers for real ML pipelines.",
           "Selection is explicit rather than hidden inside a model.",
           "Library-first: usable outside the demo that motivated it."],
          ["mlops", "signals", "demo"], ["particles"],
          "gh repo clone mayankjain1815-commits/Feature-Engine && cd Feature-Engine && python -m pytest -q"),
    _repo("marketinsight", "Marketinsight", "MARKET",
          "AI-powered stock market analysis platform offering financial data and insights through a conversational interface.",
          "Python", 4, "2026-11-06", "Finance", ["Python", "LLM", "financial data"],
          ["Conversational interface over market data.",
           "Combines retrieval and a reasoning layer for explanations.",
           "Designed to show the source behind each insight."],
          ["forecast", "signals", "agents"], ["neural"],
          "gh repo clone mayankjain1815-commits/Marketinsight && cd Marketinsight && python -m pytest -q"),
    _repo("mirrorgpt", "MirrorGPT", "MIRROR",
          "Tools for building a personalized agent that mirrors your facts, speaking style and voice.",
          "Python", 4, "2026-10-02", "Agents", ["Python", "personalization", "voice"],
          ["Builds an agent profile from the user's own facts and style.",
           "Voice and text stay on one pipeline.",
           "Falls back to deterministic behaviour with no key."],
          ["agents", "skills", "offline"], ["neural"],
          "gh repo clone mayankjain1815-commits/MirrorGPT && cd MirrorGPT && python -m pytest -q"),
    _repo("movies", "Movie-Recommendation-System", "MOVIES",
          "Movie recommendation system that delivers personalized movie suggestions.",
          "Jupyter Notebook", 5, "2026-10-05", "Data", ["Jupyter", "pandas", "recommendation"],
          ["Classic recommendation work in a readable notebook.",
           "Personalised suggestions from interaction history.",
           "Good example of the data-to-product bridge."],
          ["rag", "demo", "signals"], ["particles"],
          "gh repo clone mayankjain1815-commits/Movie-Recommendation-System && cd Movie-Recommendation-System"),
    _repo("next-role", "Next-Role", "ROLE",
          "Upload a CV and job description to get a tailored resume, researched interview prep and a day-of battlecard.",
          "Python", 4, "2026-10-05", "Agents", ["Python", "RAG", "document generation"],
          ["Retrieves role context before drafting anything.",
           "Produces a resume, prep notes and a day-of battlecard.",
           "Three outputs share one grounded context bundle."],
          ["agents", "rag", "skills"], ["neural"],
          "gh repo clone mayankjain1815-commits/Next-Role && cd Next-Role && python -m pytest -q"),
    _repo("omniroute", "OmniRoute", "OMNI",
          "Unified AI proxy/router: one OpenAI-compatible endpoint across 291 LLM providers, with automatic fallback, quota pooling and cost control.",
          "TypeScript", 6, "2026-10-07", "Infrastructure", ["TypeScript", "proxy", "fallback routing"],
          ["One compatible endpoint across 291 providers.",
           "Automatic fallback and quota pooling keep requests alive.",
           "Cost control is a first-class routing constraint."],
          ["agents", "offline", "mlops"], ["particles", "globe"],
          "gh repo clone mayankjain1815-commits/OmniRoute && cd OmniRoute && npm test"),
    _repo("shopping", "ShoppingGPT", "SHOP",
          "AI-powered shopping assistant combining natural language processing for a smart shopping experience.",
          "HTML", 3, "2026-10-05", "Agents", ["HTML", "JavaScript", "NLP"],
          ["Natural-language shopping flow in a small frontend.",
           "Commodity example of intent → action.",
           "Kept deliberately simple and readable."],
          ["agents", "demo", "skills"], ["particles"],
          "gh repo clone mayankjain1815-commits/ShoppingGPT && cd ShoppingGPT"),
    _repo("synapse", "Synapse", "SYNAPSE",
          "Daily news and content aggregation application, cloned and maintained independently.",
          "Python", 3, "2026-10-02", "Media", ["Python", "aggregation", "feeds"],
          ["Aggregates daily news into one view.",
           "Independently maintained clone, not a passive fork.",
           "Signal processing over messy real-world feeds."],
          ["signals", "agents", "demo"], ["particles"],
          "gh repo clone mayankjain1815-commits/Synapse && cd Synapse && python -m pytest -q"),
    _repo("pii", "TrustBoost-PII-Sanitizer", "PII",
          "Inspection layer between agents and LLMs that detects and sanitizes raw PII before it leaves your pipeline.",
          "HTML", 5, "2026-10-02", "Security", ["HTML", "JavaScript", "PII detection"],
          ["Sits on the boundary between agent and model.",
           "Detects and sanitizes raw PII before egress.",
           "Safety rule that is trivial to describe and hard to skip."],
          ["risk", "signals", "offline"], ["neural"],
          "gh repo clone mayankjain1815-commits/TrustBoost-PII-Sanitizer && cd TrustBoost-PII-Sanitizer"),
    _repo("portfolio", "ai-ml-portfolio", "PORTFOLIO",
          "Eight self-contained AI/ML projects plus a Flask word atlas — no langchain, no SDK wrappers, offline by design.",
          "Python", 0, "2026-11-21", "Portfolio", ["Python", "Flask", "pytest", "Node 22"],
          ["Eight projects with one-command demos and 333 offline tests.",
           "The rotating words and this repo ring are backed by the Word Atlas API.",
           "Three hand-written canvas systems and a duplicate 3D word ring."],
          ["rag", "agents", "mlops", "forecast", "signals", "skills", "risk", "offline", "demo", "iot"],
          ["particles", "globe", "neural"],
          "cd ai-ml-portfolio && cd backend && python -m word_atlas"),
    _repo("jarvis", "jarvis-mac", "JARVIS",
          "Local assistant experiments for macOS.", "Python", 0, "2026-11-23", "Agents",
          ["Python", "macOS", "assistant"],
          ["Newest local assistant experiment.",
           "Explores agent loops against desktop context.",
           "Description intentionally short — the code is the documentation."],
          ["agents", "signals", "demo"], ["neural"],
          "gh repo clone mayankjain1815-commits/jarvis-mac && cd jarvis-mac && python -m pytest -q"),
    _repo("profile", "mayankjain1815-commits", "PROFILE",
          "Public work: TypeScript AI infrastructure, agents and tooling — plus the inline aurora-neon showcase.",
          "TypeScript", 5, "2026-10-02", "Portfolio", ["Markdown", "shields.io", "WebP"],
          ["Profile README with inline animated WebP showcases.",
           "Live shields.io badges query GitHub at render time.",
           "Aurora palette carried from the portfolio into the profile."],
          ["demo", "offline", "signals"], ["particles"],
          "gh repo clone mayankjain1815-commits/mayankjain1815-commits",
          kind="profile"),
    _repo("n8n", "n8n", "N8N",
          "Fair-code platform to build and deploy AI agents and workflows, self-hosted or in the cloud.",
          "TypeScript", 3, "2026-10-20", "Infrastructure", ["TypeScript", "workflows", "self-hosted"],
          ["Workflow automation with AI agents.",
           "Self-hosted or cloud deployment.",
           "Independently maintained clone."],
          ["agents", "skills", "demo"], ["neural"],
          "gh repo clone mayankjain1815-commits/n8n && cd n8n && npm test"),
    _repo("sentinel", "sentinel-iot-disaster-command", "SENTINEL",
          "Standalone IoT early-warning command repo — the upstream of the SENTINEL project in the portfolio.",
          "JavaScript", 0, "2026-10-31", "Operations", ["Node 22", "React", "sqlite"],
          ["Three-node ESP32/LoRa early-warning concept.",
           "Kept as the standalone companion to portfolio project 08.",
           "Bug fixes live in the portfolio copy, not here."],
          ["iot", "risk", "signals", "forecast"], ["globe"],
          "gh repo clone mayankjain1815-commits/sentinel-iot-disaster-command",
          note="The portfolio's 08-sentinel-iot is the maintained copy."),
    _repo("strix", "strix", "STRIX",
          "AI-powered security agent that scans codebases and pull requests for vulnerabilities in CI/CD pipelines.",
          "Python", 4, "2026-11-11", "Security", ["Python", "CI/CD", "security scanning"],
          ["Scans code and pull requests in CI.",
           "Security findings are produced by an agent, not a regex wall.",
           "Recently updated public work."],
          ["risk", "agents", "mlops"], ["neural"],
          "gh repo clone mayankjain1815-commits/strix && cd strix && python -m pytest -q"),
    _repo("sih", "sih-main", "SIH",
          "District-level weather forecast verification with SHAP explanations — selected for the national round of Smart India Hackathon 2026.",
          "Python", 4, "2026-10-02", "Hackathon", ["Python", "XGBoost", "FastAPI", "React", "SHAP"],
          ["Predicts where India's medium-range forecasts will bust.",
           "SHAP explains why each district is flagged.",
           "Problem statement 26079, Ministry of Earth Sciences."],
          ["forecast", "risk", "mlops", "signals"], ["globe", "particles"],
          "gh repo clone mayankjain1815-commits/sih-main && cd sih-main && python -m pytest -q",
          note="Forked upstream for the hackathon; the only fork in this orbit.", kind="fork"),
]

REPO_REQUIRED_FIELDS = (
    "slug", "name", "short", "description", "language", "stars", "updated",
    "url", "category", "color", "stack", "highlights", "words", "systems",
    "command", "note", "kind",
)


def all_repos():
    return [dict(repo) for repo in REPOS]


def get_repo(slug):
    for repo in REPOS:
        if repo["slug"] == slug.lower():
            return dict(repo)
    return None


def repos_for_word(word_slug):
    return [dict(r) for r in REPOS if word_slug in r["words"]]


def related_repos(slug):
    repo = get_repo(slug)
    if repo is None:
        return []
    result = []
    for other in REPOS:
        if other["slug"] == repo["slug"]:
            continue
        shared_words = set(repo["words"]) & set(other["words"])
        shared_systems = set(repo["systems"]) & set(other["systems"])
        reason = []
        if repo["category"] == other["category"]:
            reason.append("same category")
        if shared_words:
            reason.append("shares " + ", ".join(sorted(shared_words)))
        if shared_systems and not reason:
            reason.append("shares a canvas system")
        if reason:
            result.append({
                "slug": other["slug"], "name": other["name"],
                "short": other["short"], "color": other["color"],
                "reason": "; ".join(reason),
            })
    return result

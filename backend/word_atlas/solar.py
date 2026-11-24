"""Deterministic solar-system layout for the portfolio's two record sets.

The ten concept words become inner planets; the 23 public repositories become
outer planets. One star sits at the centre and every orbital value is derived
from the record slug, so the browser, the API and the embedded JSON agree
without a database, a random seed or a network call.

These are *visualisation* measurements, not astronomy. They are honest about
that in the API payload and in the UI.
"""

from hashlib import sha256

from .data import WORDS
from .repos import REPOS, SNAPSHOT

TEXTURES = ("banded", "cratered", "icy", "stormy", "terran")
MOON_NAMES = ("I", "II", "III", "IV")
BANDS = {"word": 5, "repo": 8}


def _unit(seed):
    digest = sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / 0xFFFFFFFFFFFF


def _texture(kind, slug):
    value = _unit(kind + ":texture:" + slug)
    return TEXTURES[min(int(value * len(TEXTURES)), len(TEXTURES) - 1)]


def _orbit(index, kind):
    bands = BANDS[kind]
    band = index % bands
    lane = index // bands
    if kind == "word":
        return round(0.26 + band * 0.072 + lane * 0.006, 4), band + 1
    return round(0.70 + band * 0.035 + lane * 0.004, 4), band + 1


def _body(record, kind, index):
    u = _unit(kind + ":" + record["slug"])
    orbit, band = _orbit(index, kind)
    period = round(24 * (orbit ** 1.45) * (0.92 + u * 0.16), 2)
    radius = round((9.2 if kind == "word" else 7.1) + u * 3.4, 2)
    moons = int(u * 4) % (3 if kind == "word" else 4)
    temperature = "hot" if orbit < 0.45 else "temperate" if orbit < 0.75 else "cold"
    label = record["term"] if kind == "word" else record["short"]
    name = record["title"] if kind == "word" else record["name"]
    summary = record["tagline"] if kind == "word" else record["description"]
    linked = (len([r for r in REPOS if record["slug"] in r["words"]])
              if kind == "word" else len(record["words"]))
    return {
        "slug": record["slug"],
        "kind": kind,
        "catalog_id": ("W" if kind == "word" else "R") + f"{index + 1:02d}",
        "label": label,
        "name": name,
        "category": record["category"],
        "color": record["color"],
        "summary": summary,
        "orbit": orbit,
        "orbit_band": band,
        "period": period,
        "radius": radius,
        "phase": round((index * 2.39996323 + u * 0.42) % 6.283185307, 4),
        "spin": round(0.18 + u * 0.52, 3),
        "texture": _texture(kind, record["slug"]),
        "ring": kind == "word" and index in (1, 5, 8) or kind == "repo" and index in (2, 6, 12, 17, 21),
        "ring_tilt": round(-0.55 + u * 1.1, 3),
        "moons": moons,
        "moon_names": list(MOON_NAMES[:moons]),
        "inclination": round(1.2 + u * 11.5, 2),
        "eccentricity": round(0.01 + u * 0.13, 3),
        "temperature": temperature,
        "linked": linked,
        "language": "concept" if kind == "word" else record["language"],
        "updated": "" if kind == "word" else record["updated"],
        "stars": 0 if kind == "word" else record["stars"],
        "url": "" if kind == "word" else record["url"],
    }


STAR = {
    "name": "Portfolio Core",
    "label": "CORE",
    "caption": "10 concepts · 23 repositories · 33 worlds",
    "color": "#C4FF4D",
    "radius": 30,
    "note": "One deterministic layout shared by the canvas, the API and the offline JSON.",
}

SOLAR_REQUIRED_FIELDS = (
    "slug", "kind", "catalog_id", "label", "name", "category", "color",
    "summary", "orbit", "orbit_band", "period", "radius", "phase", "spin",
    "texture", "ring", "ring_tilt", "moons", "moon_names", "inclination",
    "eccentricity", "temperature", "linked", "language", "updated", "stars",
    "url",
)


def all_bodies():
    return ([_body(w, "word", i) for i, w in enumerate(WORDS)]
            + [_body(r, "repo", i) for i, r in enumerate(REPOS)])


def get_body(kind, slug):
    kind = kind.lower().rstrip("s")
    if kind not in BANDS:
        return None
    for body in all_bodies():
        if body["kind"] == kind and body["slug"] == slug.lower():
            return body
    return None


def neighbours(body, bodies=None):
    bodies = all_bodies() if bodies is None else bodies
    return [{
        "kind": other["kind"], "slug": other["slug"],
        "catalog_id": other["catalog_id"], "label": other["label"],
        "color": other["color"], "orbit": other["orbit"],
        "reason": "same orbit band" if other["orbit_band"] == body["orbit_band"]
                  else "same class",
    } for other in bodies
        if other["kind"] == body["kind"]
        and other["slug"] != body["slug"]
        and (other["orbit_band"] == body["orbit_band"]
             or other["category"] == body["category"])]


def solar_stats(bodies=None):
    bodies = all_bodies() if bodies is None else bodies
    categories = {body["category"] for body in bodies}
    languages = {body["language"] for body in bodies}
    bands = {(body["kind"], body["orbit_band"]) for body in bodies}
    return {
        "bodies": len(bodies),
        "words": sum(b["kind"] == "word" for b in bodies),
        "repos": sum(b["kind"] == "repo" for b in bodies),
        "moons": sum(b["moons"] for b in bodies),
        "ring_worlds": sum(b["ring"] for b in bodies),
        "orbit_bands": len(bands),
        "categories": len(categories),
        "languages": len(languages),
        "stars": sum(b["stars"] for b in bodies),
        "period_min": min(b["period"] for b in bodies),
        "period_max": max(b["period"] for b in bodies),
        "snapshot": SNAPSHOT,
    }


def solar_payload():
    bodies = all_bodies()
    return {
        "star": STAR,
        "bodies": bodies,
        "stats": solar_stats(bodies),
        "textures": list(TEXTURES),
        "snapshot": SNAPSHOT,
        "note": "Orbits, periods, moons and rings are deterministic UI metadata, not astronomical facts.",
    }

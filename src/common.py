"""Shared helpers: paths and bilingual number/date formatting (English vs French conventions)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB, PROC = ROOT / "data" / "public", ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

MONTHS = {"en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                 "November", "December"],
          "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
                 "novembre", "décembre"]}
COUNTRY = {"FR": ("France", "la France"), "DE": ("Germany", "l'Allemagne"), "ES": ("Spain", "l'Espagne"),
           "IT": ("Italy", "l'Italie"), "NL": ("the Netherlands", "les Pays-Bas"), "BE": ("Belgium", "la Belgique"),
           "AT": ("Austria", "l'Autriche"), "PT": ("Portugal", "le Portugal"), "PL": ("Poland", "la Pologne"),
           "SE": ("Sweden", "la Suède"), "IE": ("Ireland", "l'Irlande"), "FI": ("Finland", "la Finlande"),
           "EA20": ("the euro area", "la zone euro")}
# NUTS 2 (2021) statistical regions used here, with the administrative region (since 2016) that contains them
NUTS = {"FR10": ("Île-de-France", "Île-de-France"), "FRE1": ("Nord-Pas-de-Calais", "Hauts-de-France"),
        "FRH0": ("Bretagne", "Bretagne"), "FRI1": ("Aquitaine", "Nouvelle-Aquitaine"),
        "FRJ2": ("Midi-Pyrénées", "Occitanie"), "FRK2": ("Rhône-Alpes", "Auvergne-Rhône-Alpes"),
        "FRL0": ("Provence-Alpes-Côte d'Azur", "Provence-Alpes-Côte d'Azur"), "FRM0": ("Corse", "Corse")}


def num(x: float, lang: str, d: int = 1) -> str:
    """1234.5 -> '1,234.5' (en) / '1 234,5' (fr)."""
    s = f"{x:,.{d}f}"
    return s if lang == "en" else s.replace(",", " ").replace(".", ",")


def pct(x: float, lang: str, d: int = 1, sign: bool = True) -> str:
    s = f"{x:+.{d}f}" if sign else f"{x:.{d}f}"
    return s + "%" if lang == "en" else s.replace(".", ",") + " %"


def pts(x: float, lang: str, d: int = 1) -> str:
    s = f"{x:+.{d}f}"
    if lang == "en":
        return f"{s} percentage points"
    return s.replace(".", ",") + (" point" if abs(x) < 2 else " points") + " de pourcentage"


def ym(t: str, lang: str) -> str:
    y, m = t.split("-")
    return f"{MONTHS[lang][int(m) - 1]} {y}"


def cname(code: str, lang: str) -> str:
    return COUNTRY[code][0] if lang == "en" else COUNTRY[code][1]


def cshort(code: str, lang: str) -> str:
    """Country name without the French article (for lists)."""
    n = cname(code, lang)
    if lang == "fr":
        for a in ("la ", "le ", "les ", "l'"):
            if n.startswith(a):
                return n[len(a):]
    return n.replace("the ", "")


def join(items, lang):
    items = list(items)
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + (" and " if lang == "en" else " et ") + items[-1]

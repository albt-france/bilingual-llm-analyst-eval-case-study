"""Collect the public sources used in the case study (official APIs only).

Polite by design: at most 1 request per second, every raw response cached in data/raw/ (not published),
small tidy extracts written to data/public/.
    python src/fetch_public.py
"""
import json
import re
import time
import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW, PUB = ROOT / "data" / "raw", ROOT / "data" / "public"
RAW.mkdir(parents=True, exist_ok=True)
PUB.mkdir(parents=True, exist_ok=True)
HEADERS = {"User-Agent": "llm-analyst-case-study/1.0"}
EUROSTAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
INSEE = "https://bdm.insee.fr/series/sdmx/data/SERIES_BDM/"
_last = [0.0]


def get(url: str, name: str, timeout: int = 120) -> Path:
    """Download once into data/raw/<name>; later runs read the cache."""
    path = RAW / name
    if path.exists() and path.stat().st_size > 0:
        return path
    wait = 1.0 - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    path.write_bytes(r.content)
    print(f"  fetched {name} ({len(r.content) / 1e3:.0f} KB)")
    return path


def jsonstat_to_df(js: dict) -> pd.DataFrame:
    """Flatten a Eurostat JSON-stat response (flat index built from id and size), keeping status flags."""
    ids, sizes = js["id"], js["size"]
    labels = []
    for d in ids:
        idx = js["dimension"][d]["category"]["index"]
        labels.append(sorted(idx, key=idx.get))
    status = js.get("status", {})
    rows = []
    for k, v in js["value"].items():
        flat, coords = int(k), []
        for s in reversed(sizes):
            coords.append(flat % s)
            flat //= s
        coords.reverse()
        row = {d: labels[i][c] for i, (d, c) in enumerate(zip(ids, coords))}
        row.update(value=v, status=status.get(k, ""))
        rows.append(row)
    df = pd.DataFrame(rows)
    if "month" in df:  # tour_occ_nin2m: 'time' is the YEAR and months sit in a separate 'month' dimension
        df = df[df["month"].str.fullmatch(r"M\d\d")].copy()
        df["time"] = df["time"] + "-" + df["month"].str[1:]
    geo_lab = js["dimension"]["geo"]["category"]["label"]
    df["geo_label"] = df["geo"].map(geo_lab)
    df["dataset_updated"] = js.get("updated", "")[:10]
    return df


def eurostat(code: str, params: str, name: str) -> pd.DataFrame:
    p = get(EUROSTAT + code + "?" + params, name)
    js = json.loads(p.read_bytes().decode("utf-8"))
    df = jsonstat_to_df(js)
    df.insert(0, "series_code", code)
    return df


def insee(idbank: str, n: int = 48) -> pd.DataFrame:
    p = get(f"{INSEE}{idbank}?lastNObservations={n}", f"insee_{idbank}.xml")
    t = p.read_bytes().decode("utf-8")
    title = re.search(r'TITLE_EN="([^"]*)"', t) or re.search(r'TITLE_FR="([^"]*)"', t)
    title_fr = re.search(r'TITLE_FR="([^"]*)"', t).group(1)
    rows = []
    for o in re.finditer(r"<Obs ([^>]*)/>", t):
        a = dict(re.findall(r'(\w+)="([^"]*)"', o.group(1)))
        rows.append({"idbank": idbank, "title_en": title.group(1), "title_fr": title_fr,
                     "period": a["TIME_PERIOD"], "value": float(a["OBS_VALUE"]),
                     "obs_status": a.get("OBS_STATUS", ""), "obs_qual": a.get("OBS_QUAL", "")})
    return pd.DataFrame(rows).sort_values("period")


def wiki(lang: str, title: str) -> dict:
    """Plain-text extract + revision id of a Wikipedia article (CC BY-SA 4.0). Full text stays in data/raw/."""
    url = (f"https://{lang}.wikipedia.org/w/api.php?action=query&format=json&formatversion=2&prop=extracts|revisions"
           f"&explaintext=1&rvprop=ids|timestamp&redirects=1&titles={requests.utils.quote(title)}")
    safe = re.sub(r"[^A-Za-z0-9]+", "_", unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode())
    p = get(url, f"wiki_{lang}_{safe}.json")
    page = json.loads(p.read_bytes().decode("utf-8"))["query"]["pages"][0]
    text = page["extract"]
    (RAW / f"wiki_{lang}_{safe}.txt").write_text(text, encoding="utf-8")
    heads = re.findall(r"^==\s*([^=].*?)\s*==\s*$", text, re.M)
    return {"lang": lang, "title": page["title"], "revid": page["revisions"][0]["revid"],
            "rev_timestamp": page["revisions"][0]["timestamp"],
            "url": f"https://{lang}.wikipedia.org/w/index.php?oldid={page['revisions'][0]['revid']}",
            "raw_file": f"wiki_{lang}_{safe}.txt", "n_words": len(text.split()), "n_sections": len(heads),
            "sections": " | ".join(heads)}


def main():
    today = date.today().isoformat()
    print("Eurostat retail trade volume (sts_trtu_m)")
    geos = "".join(f"&geo={g}" for g in ["FR", "DE", "ES", "IT", "NL", "BE", "AT", "PT", "PL", "SE", "IE", "FI"])
    retail = eurostat("sts_trtu_m", f"indic_bt=VOL_SLS&nace_r2=G47&s_adj=SCA&unit=I21&sinceTimePeriod=2022-01{geos}",
                      "eurostat_sts_trtu_m.json")
    print("Eurostat tourist nights by NUTS 2 region (tour_occ_nin2m)")
    regs = "".join(f"&geo={g}" for g in ["FR10", "FRL0", "FRK2", "FRI1", "FRJ2", "FRH0", "FRM0", "FRE1"])
    nights = eurostat("tour_occ_nin2m", f"c_resid=TOTAL&nace_r2=I551-I553&unit=NR&sinceTimePeriod=2022-01{regs}",
                      "eurostat_tour_occ_nin2m.json")
    print("Eurostat HICP annual rate (prc_hicp_manr) and unemployment (une_rt_m)")
    g4 = "".join(f"&geo={g}" for g in ["FR", "DE", "ES", "IT", "NL", "BE", "PT", "EA20"])
    # prc_hicp_manr stopped at 2025-12 (last update 2026-02-06); prc_hicp_minr (ECOICOP ver.2) is the current dataset
    hicp_old = eurostat("prc_hicp_manr", f"coicop=CP00&unit=RCH_A&sinceTimePeriod=2023-01{g4}", "eurostat_prc_hicp_manr.json")
    hicp = eurostat("prc_hicp_minr", f"coicop18=TOTAL&unit=RCH_A&sinceTimePeriod=2023-01{g4}", "eurostat_prc_hicp_minr.json")
    unemp = eurostat("une_rt_m", f"s_adj=SA&age=TOTAL&sex=T&unit=PC_ACT&sinceTimePeriod=2023-01{g4}",
                     "eurostat_une_rt_m.json")
    for df, f in [(retail, "retail"), (nights, "nights"), (hicp_old, "hicp_stopped"), (hicp, "hicp"),
                  (unemp, "unemployment")]:
        df["extracted"] = today
        keep = ["series_code", "geo", "geo_label", "time", "value", "status", "dataset_updated", "extracted"]
        df[keep].sort_values(["geo", "time"]).to_csv(PUB / f"eurostat_{f}.csv", index=False, encoding="utf-8")
        print(f"  {f}: {len(df)} values, {df.time.min()}..{df.time.max()}, flags {sorted(set(df.status) - {''})}")

    print("INSEE BDM (SDMX)")
    ins = pd.concat([insee("001763852", 60),   # CPI base 2015, all households, France: discontinued series
                     insee("011814630", 30),   # CPI base 2025, all households, France: current series
                     insee("001688526", 16),   # ILO unemployment rate, metropolitan France, SA: discontinued series
                     insee("001688527", 16)])  # ILO unemployment rate, France excl. Mayotte, SA: current series
    ins["extracted"] = today
    ins.to_csv(PUB / "insee_series.csv", index=False, encoding="utf-8")
    for i, g in ins.groupby("idbank"):
        print(f"  {i}: {g.period.min()}..{g.period.max()} last={g.value.iloc[-1]}")

    print("Wikipedia texts (CC BY-SA 4.0) for summarising and chunking")
    arts = [("en", "Eurostat"), ("en", "Consumer price index"), ("en", "Seasonal adjustment"),
            ("fr", "Institut national de la statistique et des études économiques"),
            ("fr", "Nomenclature des unités territoriales statistiques")]
    meta = pd.DataFrame([wiki(l, t) for l, t in arts])
    # revisions used for the published gold set; a newer revision changes word counts and sections
    pinned = {"Eurostat": 1356128040, "Consumer price index": 1385974709, "Seasonal adjustment": 1356584187,
              "Institut national de la statistique et des études économiques": 241378467,
              "Nomenclature des unités territoriales statistiques": 229375657}
    for _, m in meta.iterrows():
        if pinned.get(m.title) != m.revid:
            print(f"  WARNING: '{m.title}' is now revision {m.revid} (gold set built on {pinned.get(m.title)}); "
                  "text tasks will reflect the newer revision")
    meta["extracted"] = today
    meta.to_csv(PUB / "texts_meta.csv", index=False, encoding="utf-8")
    print(meta[["lang", "title", "revid", "n_words", "n_sections"]].to_string(index=False))


if __name__ == "__main__":
    main()

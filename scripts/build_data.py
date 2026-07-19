#!/usr/bin/env python3
"""Build assets/flights.json from Flighty CSV exports in data/raw/.

Usage:
    python3 scripts/build_data.py

Inputs:
    data/raw/*.csv      one Flighty export per person; person name = filename
                        (e.g. "randy.csv" -> "Randy"), overridable in data/people.json
    data/people.json    optional: {"randy": {"name": "Randy"}, ...} keyed by filename stem
    data/airports.json  IATA -> [lon, lat, name, city, country]

Output:
    assets/flights.json  everything the page needs (only airports actually used)

Privacy: only date, airline, flight number, and route are exported. PNR, seat,
notes, and all other Flighty columns never leave data/raw/ (which is gitignored).
"""

import csv
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
AIRPORTS = json.loads((ROOT / "data" / "airports.json").read_text())

# Validated dark-mode categorical slots (dataviz reference palette, all-pairs pass)
COLORS = ["#3987e5", "#008300", "#d55181", "#c98500"]


def haversine_km(lon1, lat1, lon2, lat2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def find_col(fieldnames, *candidates):
    """Case-insensitive exact-then-prefix column match."""
    lower = {f.lower().strip(): f for f in fieldnames}
    for c in candidates:
        if c in lower:
            return lower[c]
    for c in candidates:
        for k, orig in lower.items():
            if k.startswith(c):
                return orig
    return None


def extract_iata(value):
    """Flighty writes plain IATA codes; tolerate 'City (ABC)' style too."""
    v = (value or "").strip().upper()
    if re.fullmatch(r"[A-Z]{3}", v):
        return v
    m = re.search(r"\(([A-Z]{3})\)", v)
    return m.group(1) if m else None


def parse_person(path):
    flights, skipped = [], []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        c_date = find_col(cols, "date")
        c_from = find_col(cols, "from")
        c_to = find_col(cols, "to")
        c_airline = find_col(cols, "airline")
        c_flight = find_col(cols, "flight")
        c_cancel = find_col(cols, "canceled", "cancelled")
        c_divert = find_col(cols, "diverted to", "diverted")
        if not (c_from and c_to):
            sys.exit(f"{path.name}: couldn't find From/To columns in {cols}")
        for row in reader:
            if c_cancel and (row.get(c_cancel) or "").strip().lower() in ("true", "yes", "1"):
                continue
            frm = extract_iata(row.get(c_from))
            to = extract_iata(row.get(c_divert)) or extract_iata(row.get(c_to))
            if not frm or not to or frm == to:
                skipped.append(f"{row.get(c_from)}->{row.get(c_to)}")
                continue
            if frm not in AIRPORTS or to not in AIRPORTS:
                skipped.append(f"{frm}->{to} (unknown airport)")
                continue
            flights.append({
                "date": (row.get(c_date) or "").strip()[:10],
                "from": frm,
                "to": to,
                "airline": (row.get(c_airline) or "").strip(),
                "flight": (row.get(c_flight) or "").strip(),
            })
    return flights, skipped


def main():
    csvs = sorted(RAW.glob("*.csv"))
    if not csvs:
        sys.exit(f"No CSVs found in {RAW}/ — drop the four Flighty exports there first.")
    people_cfg = {}
    cfg_path = ROOT / "data" / "people.json"
    if cfg_path.exists():
        people_cfg = json.loads(cfg_path.read_text())

    people, all_flights, used_airports = [], [], set()
    for i, path in enumerate(csvs):
        stem = path.stem
        cfg = people_cfg.get(stem, {})
        name = cfg.get("name", stem.replace("-", " ").replace("_", " ").title())
        flights, skipped = parse_person(path)
        if skipped:
            print(f"  {name}: skipped {len(skipped)} rows: {skipped[:5]}{'…' if len(skipped) > 5 else ''}")
        km = 0.0
        airports, countries, airlines = set(), set(), set()
        for fl in flights:
            a, b = AIRPORTS[fl["from"]], AIRPORTS[fl["to"]]
            km += haversine_km(a[0], a[1], b[0], b[1])
            airports.update((fl["from"], fl["to"]))
            countries.update((a[4], b[4]))
            if fl["airline"]:
                airlines.add(fl["airline"])
            all_flights.append({**fl, "p": i})
        used_airports.update(airports)
        people.append({
            "name": name,
            "color": cfg.get("color", COLORS[i % len(COLORS)]),
            "flights": len(flights),
            "km": round(km),
            "airports": len(airports),
            "countries": len(countries),
            "airlines": len(airlines),
        })
        print(f"  {name}: {len(flights)} flights, {round(km):,} km, "
              f"{len(airports)} airports, {len(countries)} countries")

    all_flights.sort(key=lambda f: f["date"])
    out = {
        "people": people,
        "flights": all_flights,
        "airports": {a: AIRPORTS[a][:4] for a in sorted(used_airports)},
        "totals": {
            "flights": len(all_flights),
            "km": sum(p["km"] for p in people),
            "airports": len(used_airports),
            "countries": len({AIRPORTS[a][4] for a in used_airports}),
        },
    }
    dest = ROOT / "assets" / "flights.json"
    dest.write_text(json.dumps(out, separators=(",", ":")))
    t = out["totals"]
    print(f"\nWrote {dest} — {t['flights']} flights, {t['km']:,} km, "
          f"{t['airports']} airports, {t['countries']} countries")


if __name__ == "__main__":
    main()

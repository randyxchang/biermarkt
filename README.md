# biermarkt.org

Combined flight map for four people, drawn from [Flighty](https://flighty.com) exports.
Hosted on GitHub Pages (custom domain via Cloudflare DNS, grey-cloud A records).

## Updating with new flight data

1. Export each person's data from Flighty (Settings → Export Data → CSV) and drop
   the four CSVs into `data/raw/` — one per person, filename becomes the display
   name (`randy.csv` → "Randy"). `data/raw/` is gitignored: PNRs, seats, and notes
   never leave this machine.
2. Optionally override names/colors in `data/people.json`:
   `{"randy": {"name": "Randy", "color": "#3987e5"}}`
3. Run `python3 scripts/build_data.py` — regenerates `assets/flights.json`
   (routes, dates, airline + flight number only).
4. Commit and push. The map is `map.html`; once real data is in, copy it over
   `index.html` to make it the landing page.

## Files

- `map.html` — the visualization (D3, dark map, per-person arcs)
- `scripts/build_data.py` — Flighty CSV → `assets/flights.json`
- `data/airports.json` — IATA → coordinates lookup (OurAirports, public domain)
- `assets/countries-110m.json` — world topojson (world-atlas)

Colors are the dark-mode categorical slots from the validated reference palette
(all-pairs CVD check passes for four series).

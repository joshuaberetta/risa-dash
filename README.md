# RISA Dashboard

A web tool for RISA (Rapid Infrastructure and Service Assessment) responses. It puts drone and satellite imagery, KoboCollect observations and analysis layers on one map, prints **RISA page 1** (the Common Operational Picture) to PDF, and exports the data for QGIS and ArcGIS.

The consortium instance is at **https://risa-dash.kobolabs.dev**. The same image runs self-hosted (an NDMA's server) or fully offline on a [kobo-in-a-box](../kobo-in-a-box). The plan and decisions are in [`plans/mvp.md`](plans/mvp.md); the non-technical overview for partners and donors is [`docs/concept-note.md`](docs/concept-note.md).

Stack: Django 5.2 + GeoDjango + PostGIS, Django Ninja, Procrastinate (Postgres job queue), GDAL, Typst for printed pages (with Playwright/Chromium rendering the map image); React 19 + Vite + Mantine 8 + MapLibre GL, Terra Draw for drawing. Licence: [AGPL-3.0](LICENSE), as KoboToolbox.

## What works

- **Responses and sites**, with a shared **edit key** per response (no accounts). Viewing is open at unlisted URLs, `noindex`.
- **Imagery**: upload a GeoTIFF orthomosaic or satellite scene (resumable 8 MB parts, up to 8 GB). The worker makes a Web Mercator Cloud-Optimised GeoTIFF (JPEG with a transparency mask; drone collars made transparent with `nearblack`), and the browser reads it straight from storage with range requests, so there's no tile server. Imagery by URL (XYZ, WMS, COG) when online.
- **Vector**: GeoJSON, GeoPackage, zipped Shapefile, KML/KMZ, CSV with lat/lon. Attributes like `type`/`status`/`label` (also Spanish and French words) are matched to RISA types and statuses.
- **Kobo**: connect a project on kf, eu, or any server on `ALLOWED_SERVERS` (an `http://` server only when listed exactly, e.g. `http://kf.kobo.local`). The token is stored encrypted and never reaches the browser. Points come from the first geopoint question; type and status are guessed from the form and adjustable ("Map form to RISA"). Photos are proxied. Syncs every 10 minutes and on demand.
- **Drawing**: points, lines and areas with type, status and label; edit and reshape them.
- **RISA symbology** from [`symbology/risa.json`](symbology/risa.json): the reserved status colours, always shown twice (colour plus line style or symbol shape).
- **Page 1**: frame the map, set title, code, version, authority, key message and at-a-glance figures (computed, overridable, TBC flags). Locator maps are optional: the area round the site, and a country overview joined to it by leader lines (as on MapAction's maps), on the map's corner or at the top of the side panel. The worker renders the map and locators in headless Chromium at 300 dpi, and [Typst](backend/risa/typst/page1.typ) lays out the page around them: vector text, legend symbols as SVG, about 1.4 MB for an A3. The editor's preview is a low-resolution draft of the same render. Page labels in English, Spanish and French follow the response's language. Versions are kept.
- **Data table**: the records of a Kobo or vector layer under the map, with photos (a template image when there's none), search and a status filter. A row frames the feature on the map.
- **AI analysis (example output only)**: a tab showing what an imagery and field-data model could return: a situation brief, shelters and people per block, findings checked against Sphere standards (water per person and distance, flood exposure, access, data quality), suggested priorities, and notes on photos. Nothing runs a model yet; [`frontend/src/analysis.ts`](frontend/src/analysis.ts) makes the output from the site's data, and the shelter counts are made up.
- **Imagery analysis (simulated)**: in the AI analysis tab, **Detect shelters on imagery** finds shelters and buildings on the orthomosaic (current view or the whole image), groups shelters into blocks and outlines the site, with a progress spinner while it runs. Results are suggestions: dashed until a person accepts them, one at a time or by confidence; they can be re-tagged and reshaped like drawn features, and only accepted shelters count on page 1. The detector is a stand-in (colour rules on the real image, [`risa/analysis.py`](backend/risa/analysis.py)) for a segmentation model; see the plan.
- **Learning from corrections (simulated)**: every accept, reject, reshape and hand-drawn missed shelter is kept as a label. **Learn from corrections** in the AI analysis tab trains a new detector version for the response (once there are 20 reviews each way) and reports its accuracy on reviews held back from training, next to the built-in rules; the next detection uses it. **Download training data** exports the imagery and labels for fine-tuning a real model. [`risa/learning.py`](backend/risa/learning.py).
- **Walkthrough**: each page (home, response, site) has a short tour that highlights its parts in turn. It starts by itself the first time someone opens that kind of page, and again from **Tour** in the header, or with `?tour` on any link for demos. The wording is in [`frontend/src/tours.ts`](frontend/src/tours.ts).
- **Export**: a GeoPackage of every vector layer (opens in QGIS and ArcGIS Pro), the COG and the original upload per layer.

Not yet: pages 2 and 3, QML styles inside the GeoPackage, response bundles, offline content packs (`pack build/load`), swipe between imagery dates, generated OpenAPI client. See the plan.

## Run it locally

Needs Docker and Node 22.

```sh
docker compose up -d                 # PostGIS, API on :8070, worker
cd frontend && npm install && npm run dev   # http://localhost:5173
```

### Sample data

Real drone imagery with fictional RISA data on top: IOM's 2012 orthomosaic of Aviation Camp, Port-au-Prince (CC BY 4.0, via OpenAerialMap).

```sh
mkdir -p .sample-data/oam
curl -L -o .sample-data/oam/haiti-aviation-camp-1.tif \
  https://oin-hotosm-temp.s3.us-east-1.amazonaws.com/69bbae0f57bbd74f1e80e3ad/0/69bbae0f57bbd74f1e80e3ae.tif
python3 -I scripts/seed_sample.py --api http://localhost:8070 --imagery .sample-data/oam/haiti-aviation-camp-1.tif
```

It prints the site URL and the edit key (use **Unlock editing**). Against the hosted instance, pass `--api https://risa-dash.kobolabs.dev --create-key …`.

### Tests

```sh
docker compose exec web python -m pytest -q risa/tests
cd frontend && npx tsc -b
```

`scripts/shot.py` screenshots a page in the worker's headless Chromium (no GPU, like printing).

## Self-hosting and offline

```sh
cp deploy/.env.example deploy/.env      # set SECRET_KEY, POSTGRES_PASSWORD, ALLOWED_SERVERS…
docker compose -f deploy/compose.yaml --env-file deploy/.env up -d --build
```

Files go on a volume (`STORAGE=filesystem`) and are served with range requests. Nothing calls the internet at runtime except the online basemaps, which `ONLINE_BASEMAPS=false` hides. On a kobo-in-a-box, add [`deploy/nginx/risa.conf`](deploy/nginx/risa.conf) to the edge nginx and set `ALLOWED_SERVERS=http://kf.kobo.local`, `PUBLIC_URL=http://risa.kobo.local`. Offline basemaps are PMTiles extracts under `basemaps/` in the media volume. **Offline gap today:** map label fonts (glyphs) still come from OpenFreeMap; bundling them is on the list.

## Hosting (DigitalOcean)

App Platform app `risa-dash` (region `fra`) from [`.do/app.yaml`](.do/app.yaml): `web` and `worker` from the same Dockerfile, managed Postgres 17 `risa-dash-db` with PostGIS, Spaces bucket `risa-dash` (fra1, CDN on) under the `prod/` prefix. Pushing to `main` deploys. Secrets (`SECRET_KEY`, `CREATE_KEY`, Spaces keys) are set in the app.

## Settings

All environment variables; see [`backend/config/settings.py`](backend/config/settings.py) and [`deploy/.env.example`](deploy/.env.example).

| Setting | Default | |
|---|---|---|
| `PUBLIC_URL` | `http://localhost:8000` | Where people open it |
| `ALLOWED_SERVERS` | kf, eu | Kobo servers it may connect to |
| `CREATE_KEY` | empty | Needed to create a response, when set |
| `READ_ONLY_PUBLIC` | `true` | `false`: viewing needs the edit key |
| `STORAGE` | `filesystem` | or `s3` with `S3_*`, `MEDIA_PUBLIC_URL` |
| `ONLINE_BASEMAPS` | `true` | `false` on an offline box |
| `PRINT_BASE_URL` | `PUBLIC_URL` | Where the worker's Chromium opens the print route |

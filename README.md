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
- **Page 1**: frame the map, set title, code, version, authority, key message and at-a-glance figures (computed, overridable, TBC flags). A second QR code goes to the feedback form, when one is set. Locator maps are optional: the area round the site, and a country overview joined to it by leader lines (as on MapAction's maps), on the map's corner or at the top of the side panel. The worker renders the map and locators in headless Chromium at 300 dpi, and [Typst](backend/risa/typst/page1.typ) lays out the page around them: vector text, legend symbols as SVG, about 1.4 MB for an A3. The editor's preview is a low-resolution draft of the same render. Page labels in English, Spanish and French follow the response's language. Versions are kept.
- **Data table**: the records of a Kobo or vector layer under the map, with photos (a template image when there's none), search and a status filter. A row frames the feature on the map.
- **AI analysis (example output only)**: a tab showing what an imagery and field-data model could return: a situation brief, shelters and people per block, findings checked against Sphere standards (water per person and distance, flood exposure, access, data quality), suggested priorities, and notes on photos. Nothing runs a model yet; [`frontend/src/analysis.ts`](frontend/src/analysis.ts) makes the output from the site's data, and the shelter counts are made up.
- **Imagery analysis (simulated)**: in the AI analysis tab, **Detect shelters on imagery** finds shelters and buildings on the orthomosaic (current view or the whole image), groups shelters into blocks and outlines the site, with a progress spinner while it runs. Results are suggestions: dashed until a person accepts them, one at a time or by confidence; they can be re-tagged and reshaped like drawn features, and only accepted shelters count on page 1. The detector is a stand-in (colour rules on the real image, [`risa/analysis.py`](backend/risa/analysis.py)) for a segmentation model; see the plan.
- **Learning from corrections (simulated)**: every accept, reject, reshape and hand-drawn missed shelter is kept as a label. **Learn from corrections** in the AI analysis tab trains a new detector version for the response (once there are 20 reviews each way) and reports its accuracy on reviews held back from training, next to the built-in rules; the next detection uses it. **Download training data** exports the imagery and labels for fine-tuning a real model. [`risa/learning.py`](backend/risa/learning.py).
- **User guide** at `/guide/`, linked as **Guide** in the app bar: setup, imagery, Kobo, the map, page 1, offline and low bandwidth, a response checklist and questions, with screenshots. A static page ([`frontend/public/guide/`](frontend/public/guide/index.html)) in the kobotoolbox.org style shared with kobo-dash, kobo-field-forms and kobo-in-a-box (`home.css`, fonts bundled), so it works offline.
- **Walkthrough**: each page (home, response, site) has a short tour that highlights its parts in turn. It starts by itself the first time someone opens that kind of page, and again from **Tour** in the header, or with `?tour` on any link for demos. The wording is in [`frontend/src/tours.ts`](frontend/src/tours.ts).
- **Export**: a GeoPackage of every vector layer (opens in QGIS and ArcGIS Pro), the COG and the original upload per layer.
- **Response bundles**: a whole response in one zip, to move it between instances (cloud → box → cloud, by USB drive when there's no link) and to archive it: sites, layers, features (review decisions included), COGs, Kobo field maps (not tokens), products, page 1 versions and their PDFs, detector versions, and a GeoPackage per site. **Bundle** on a response's page, **Import bundle** on the home page, or `manage.py bundle export <response> <file>` and `manage.py bundle import <file>`. Imagery can be left out to send only the work done on it. A manifest written last lists every file with its SHA-256, so a cut-off or damaged copy is refused. Import merges by UUID: the bundle's rows are created or updated, others are kept, each vector layer's features are replaced by the bundle's, and importing again changes nothing. Importing into a response that's already there needs its edit key; a new one keeps the edit key it had. [`risa/bundles.py`](backend/risa/bundles.py). Not yet encrypted or incremental (planned for federation).

Not yet: pages 2 and 3, QML styles inside the GeoPackage, offline content packs (`pack build/load`), swipe between imagery dates, generated OpenAPI client. See the plan.

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
scripts/e2e.sh                       # the production image with the internet cut off
```

`scripts/e2e.sh` builds the production image and runs it on a Docker network with no way out, as on an offline kobo-in-a-box. [`scripts/e2e.py`](scripts/e2e.py) then checks that no online basemaps are offered, the frontend and guide are served, imagery becomes a COG and vector is processed, page 1 renders to PDF, the site exports as a GeoPackage, and the response goes out as a bundle and back in. CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs it on every push, with ruff, the backend tests and the frontend build.

`scripts/shot.py` screenshots a page in the worker's headless Chromium (no GPU, like printing). [`scripts/guide-shots.py`](scripts/guide-shots.py) retakes the user guide's screenshots of the home page and the bundle dialogs from the sample response; the others were taken by hand with the box's demo Kobo project connected.

## Self-hosting and offline

```sh
cp deploy/.env.example deploy/.env      # set SECRET_KEY, POSTGRES_PASSWORD, ALLOWED_SERVERS…
docker compose -f deploy/compose.yaml --env-file deploy/.env up -d --build
```

Files go on a volume (`STORAGE=filesystem`) and are served with range requests. Nothing calls the internet at runtime except the online basemaps, which `ONLINE_BASEMAPS=false` hides, and the map label fonts (`GLYPHS_URL`, OpenFreeMap by default), which offline point at a local tile server's fonts with `MAP_FONT` and `MAP_FONT_BOLD` set to names it has. Offline basemaps are PMTiles extracts under `basemaps/` in the media volume. **[`docs/self-hosting.md`](docs/self-hosting.md)** covers an install on your own server: HTTPS behind a proxy, object storage, no internet, access, bundles from the command line, backups and upgrades. On a kobo-in-a-box, use the box's RISA component instead (`remote/risa/` in kobo-in-a-box, with `risa.sh`), which wires it to the box's Kobo, map and fonts.

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
| `GLYPHS_URL` | OpenFreeMap | Map label fonts (`{fontstack}`, `{range}`); a local tile server's offline |
| `MAP_FONT`, `MAP_FONT_BOLD` | Noto Sans Regular, Noto Sans Bold | Label font names on `GLYPHS_URL`; comma-separated for a fallback stack. `Noto Sans Medium` for bold with Protomaps' fonts |
| `PRINT_BASE_URL` | `PUBLIC_URL` | Where the worker's Chromium opens the print route |
| `MAX_BUNDLE_SIZE` | 64 GB | Largest bundle an import accepts |
| `BUNDLE_KEEP_DAYS` | 7 | Exported bundles are deleted after this, as are unfinished bundle uploads |
| `FEEDBACK_URL` | empty | Feedback form (e.g. a Kobo form's web link): a QR code on printed maps and a Feedback link online. Responses can set their own. `{response}`, `{site}`, `{product}`, `{version}` and `{source}` are filled in. The printed QR code points to the short `/f/<product>/<version>`, which redirects to the form, so it stays scannable at its printed size |

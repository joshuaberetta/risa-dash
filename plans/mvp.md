# RISA Dashboard: MVP plan

Status: draft, not started. Decisions of 29/10/2026 included (section 8).

A web tool for RISA responses. It puts drone imagery, satellite imagery, KoboCollect observations and analysis layers on one interactive map, prints page 1 of the RISA product (the Common Operational Picture) to PDF, and exports the data for QGIS and ArcGIS. During a response the web tool is the main interface, and the PDF is the reference for low-connectivity settings. It turns the "Interactive version" mock on the RISA product page (`~/code/risa/site/themes/*/product.html`) into a working product.

The consortium runs it first, at **https://risa-dash.kobolabs.dev**. It must also be **self-hostable** by an NDMA or anyone else who needs the data held in-country, and run **fully offline** on a kobo-in-a-box (`~/code/kobo-in-a-box`, see `RISA-PLAN.md` R4, R5 and R8) next to a local Kobo server.

Stack: Django + GeoDjango on the backend, React + Vite + Mantine on the frontend. No user accounts: a shared edit key per response.

---

## 1. What the MVP has to do

The test for the MVP is the Venezuela response (MapAction is sharing the data). From the raw inputs (the drone orthomosaic and the Kobo export of Campamento Transitorio Estadio Cesar Nieves), a responder can build a RISA page 1 in under an hour and print it. This has to work both at risa-dash.kobolabs.dev and on a box with the internet cut off.

| # | Capability | In the MVP |
|---|---|---|
| 1 | **Responses and sites** | Create a response (event, country, GLIDE number e.g. `EQ-2026-000093-VEN`, date, language) and one or more sites in it (camp, collective centre, settlement), each with a boundary and a default view |
| 2 | **Drone imagery** | Upload an orthomosaic (GeoTIFF, from WebODM, DroneDeploy, Pix4D or DJI Terra) with a resumable upload. It is converted to a Cloud-Optimised GeoTIFF (COG) and shown as a layer, with capture date and resolution |
| 3 | **Satellite imagery** | Upload a scene (COG or GeoTIFF), or add one by URL (COG, XYZ, WMS) when online, e.g. Maxar Open Data or Copernicus EMS. Before/after swipe between two imagery layers |
| 4 | **Basemaps** | A vector basemap from a local PMTiles extract of the response area, so it works offline and prints sharp at 300 dpi. Online-only extras (Esri World Imagery, OSM raster) can be turned on per instance |
| 5 | **Kobo data** | Connect a project on **kf.kobotoolbox.org, eu.kobotoolbox.org or any server on the instance's allow-list** (a private server, or `http://kf.kobo.local` on a box). Pull submissions, turn geopoints into features, map answers to RISA service type and status, sync on demand and on a schedule. Click a point to see the submission and its photos |
| 6 | **Analysis layers** | Upload vector data (GeoJSON, GeoPackage, zipped Shapefile, KML, CSV with lat/lon). Draw and label features on the map: shelter blocks, services, routes, hazards, and the labelled polygons in MapAction's MA023. Site summary: services by type and status, routes by status, shelters per block |
| 7 | **Styling** | RISA symbology by default: the reserved status set (`--st-ok #1F9A62`, `--st-partial #E9A23B`, `--st-no #A8281A`, `--st-unknown #8C939C`), always shown twice (colour plus line style or symbol shape), OCHA humanitarian icons. Per-layer edits: colour, opacity, label field |
| 8 | **Page 1 product** | Save a view as a product and print it as RISA page 1: header band, map, side panel, footer (section 3). A3 or A4 landscape at 300 dpi. Every render is kept as a version, and the QR code points to the latest one |
| 9 | **GIS export** | Per site or product: a GeoPackage with every vector layer and its styles embedded (opens styled in QGIS, reads in ArcGIS Pro), GeoJSON, CSV and the COGs |
| 10 | **Response bundle** | Export a whole response (data, imagery, products) as one file and import it on another instance. This is how data moves between the cloud, an NDMA server and a box until there is real sync |
| 11 | **Share** | Every site and product has a permalink that restores the view |

### Not in the MVP

User accounts and roles. Pages 2 and 3 of the product (key findings, hotspot); the layout engine is built so they can be added next. Live sync between instances (the bundle covers it for now). Kobo webhooks (polling first). Interface translations; text on the printed product is free text, so Spanish and French maps work from day one. AI analysis of imagery (kobo-in-a-box R11), tent counting, in-browser photogrammetry.

---

## 2. Deployment targets

One codebase and one set of images, three ways to run it. **Nothing is required at runtime that isn't in the stack itself**: no CDN, no Google Fonts, no external tiles, no telemetry unless it is configured. Settings are environment variables, as in kobo-dash.

| | Hosted (consortium) | Self-hosted (NDMA, partner) | Offline box (kobo-in-a-box) |
|---|---|---|---|
| URL | `https://risa-dash.kobolabs.dev` | Their own domain | `http://risa.kobo.local` |
| Runs on | DO App Platform | Any Linux server with Docker | The box, behind its edge nginx |
| Database | DO Managed Postgres + PostGIS | `postgis/postgis` container | `postgis/postgis` container (or the box Postgres, if it moves to a PostGIS image) |
| Files | DO Spaces + CDN (`STORAGE=s3`) | Local volume, or any S3-compatible store | Local volume (`STORAGE=filesystem`), served by nginx with range requests |
| TLS | App Platform | Caddy in the compose file, or their own proxy | None: plain HTTP on the LAN, as the rest of the box |
| Kobo | `ALLOWED_SERVERS=https://kf.kobotoolbox.org,https://eu.kobotoolbox.org` | Plus their own server | `http://kf.kobo.local` |
| Basemap | Bundled PMTiles extracts, optional Esri imagery | Bundled PMTiles extracts | Content pack PMTiles |
| Install | Push to `main` | `docker compose up -d` | Compose services added by the box's install (W9 pattern) |

### Kobo servers

Kobo servers work as in kobo-dash (W9, branch `w9-offline-box`):

- `ALLOWED_SERVERS` lists the Kobo servers this instance may connect to. It defaults to kf and eu. The connect form offers those, plus a custom URL that must be on the list.
- An `http://` server is accepted only when it is listed exactly, and the token is only ever sent to that server. Pages served over https never use an http server or http tiles (the browser would block them as mixed content).
- Tokens are stored encrypted with a key from the environment. They never reach the browser, and photos are proxied through the backend.
- Containers reach the box's Kobo through `extra_hosts`, the way kobo-dash does.

### Offline content pack

A management command, run online before deployment, fills a folder that the box (or an air-gapped server) loads:

```
./manage.py pack build VEN --bbox <w,s,e,n> --out /data/pack
  basemap/VEN.pmtiles            vector extract of the response area (Protomaps daily build, `pmtiles extract`)
  boundaries/VEN_ADM{0,1,2}.geojson  geoBoundaries, same layout as kobo-dash's BOUNDARIES_DIR
  imagery/*.tif                  optional pre-event satellite COGs (Maxar Open Data, Sentinel-2)
./manage.py pack load /data/pack
```

The boundaries folder uses the same layout as kobo-dash's `scripts/fetch_boundaries.py`, so a box needs only one copy. The locator inset uses Natural Earth (bundled, small) plus these boundaries. Fonts (glyphs), sprites and OCHA icons are part of the frontend build.

### Fit with kobo-in-a-box

- **R5 (live RISA dashboard)** and **R4 (imagery)**: this tool covers most of R4's "share, tile, serve" for orthomosaics, and R5's map. kobo-dash stays the Kobo-wide analysis dashboard. Propose to the box plan that RISA imagery goes in through this tool, and that it writes MBTiles for QField alongside the COG (after the MVP).
- **R8 (dissemination)**: the products list doubles as the "RISA products" page on the LAN. The outbox can push the PDF and GeoPackage first and the imagery last.
- **Footprint**: the box also runs Kobo and the local models, so keep this small. About 1 GB RAM for web and worker at rest. Chromium runs only during a render, and GDAL's cache is capped (`GDAL_CACHEMAX`) so COG conversion stays inside a memory limit. Images are built for amd64 and arm64.

---

## 3. The printed product: RISA page 1

The layout follows page 1 of the RISA product (`~/code/risa/site/assets/product.js` `page1()`, `product.css` `.pd-page--1`) at A3 landscape, with A4 as an option:

- **Header band**: the national authority's logo first (RISA is credited as the method), the title ("Common Operational Picture" by default), site and place, and the version (e.g. "Initial assessment · Day 4 · v1.0"), date and time, and page "1 of 1".
- **Map**, about 80% of the width: the product's extent and layers, with a scale bar, north arrow, grid labels and a locator inset in a corner.
- **Side panel**, about 19 em:
  - **Key message**: free text, a sentence or two.
  - **At a glance**: four figures computed from the data (people as an estimate marked TBC, shelters counted, water points working, access routes open). Each one can be overridden by hand and labelled TBC.
  - **Legend**, built from the visible layers: access routes by status, service symbols, working/partly/not working, hazards and site furniture.
- **Footer**: sources (imagery platform, height, resolution and date; Kobo points and dates; basemap credits, taken from each layer's attribution), the disclaimer, "Produced with RISA", technical support credits, and the QR code.

The brand stays **neutral** for now: Mantine defaults, a neutral band colour, system-safe bundled fonts. All brand values sit in one theme file (CSS variables plus a Mantine theme) that the chosen RISA direction can replace later. The reserved status colours and symbols are not part of the brand and don't change.

---

## 4. Architecture

```
 browser ── MapLibre GL, Mantine ──▶  frontend (static build)
                                      web: Django + Ninja API, MVT tiles, uploads, Kobo proxy
                                      worker: Procrastinate jobs + GDAL + Playwright/Chromium
                                         COG conversion · Kobo sync · PDF render · exports · bundles
                                             │                         │
                                   PostgreSQL + PostGIS        file storage: S3 (Spaces) or local volume
                                   (data + job queue)          COGs, uploads, PDFs, GeoPackages, PMTiles
                                             │
                                   Kobo: kf / eu / allow-listed server (http://kf.kobo.local on a box)
```

The same images and settings run all three targets. Cloud and self-hosted installs differ only in env vars.

### Backend

- **Django 5.2 LTS + GeoDjango** on **PostGIS**. Features live in PostGIS with a `geometry` column and `properties` JSONB, so uploads with any schema fit one table and stay queryable.
- **Django Ninja** for the API. Its OpenAPI schema generates the TypeScript client (`openapi-typescript`).
- **Vector tiles straight from PostGIS** (`ST_AsMVT`) at `/api/tiles/...`, for big layers. Small layers go as GeoJSON.
- **Background jobs**: Procrastinate, a Postgres-backed queue. No Redis on the box.
- **Geo tooling** in the image: GDAL 3.9+ (`gdal_translate -of COG`, `ogr2ogr`), `rio-cogeo` to validate, `pyogrio`, `pmtiles`.
- **Storage**: `django-storages` with two backends, S3 or filesystem. Imagery URLs given to the browser are presigned (S3) or `/media/...` served by nginx (filesystem). Both support HTTP range requests, which is all COG reading needs.
- **Uploads**: chunked and resumable through Uppy and the tus protocol, implemented in the web service. Each chunk goes straight to an S3 multipart part, or is appended to a file on the volume. Orthomosaics are often 0.5–5 GB and box Wi-Fi drops, so resuming matters offline as much as online. This also keeps each request small for App Platform's limits.
- **Admin**: Django admin, gated by a superuser created from the CLI, for fixing data during a response.

### Frontend

- **React 19 + Vite + TypeScript + Mantine 8**.
- **MapLibre GL JS** through `react-map-gl/maplibre`, with the PMTiles protocol for basemaps and `@geomatico/maplibre-cog-protocol` to read COGs directly. No tile server, so the cloud, a server and the box behave the same. TiTiler is the fallback if the Phase 0 spike shows client-side COG is too slow.
- **Terra Draw** for drawing and editing points, lines and polygons.
- **TanStack Query** for server state. View state goes in the URL.
- **Map furniture** (legend, scale bar, north arrow, inset, at-a-glance figures) is shared React components, used on screen and in print.
- No runtime requests outside the instance: fonts, glyphs, sprites and icons are bundled. Online-only basemaps appear only when the instance enables them.

### Print pipeline

Server-side rendering in headless Chromium, so the PDF is what the layout shows and uses the same map renderer:

1. The print route `/print/products/:id?v=3` lays out page 1 with CSS (`@page { size: A3 landscape }`, sizes in mm). The map is MapLibre with `pixelRatio` set for 300 dpi. Text is DOM, so it stays vector in the PDF.
2. The worker opens the route in Playwright against the web service's internal URL (it works offline), waits for every map to be idle, then calls `page.pdf()`.
3. Each render is a new, immutable `ProductVersion` holding the PDF and a snapshot of the product and data, so a reprint matches the original.

Chromium on App Platform and on a GPU-less box uses SwiftShader. That's the first spike.

### Data model (first cut)

```
Response      slug, name, hazard, country (ISO3), glide, start_date, language,
              edit_key_hash, private
Site          response, slug, name, kind, boundary (Polygon), default_view, notes
Layer         site, name, kind [raster|vector|kobo|basemap|wms|xyz],
              source (url / storage key), status [processing|ready|failed],
              style (JSON: MapLibre fragment + RISA preset), z_order, visible_default,
              attribution, licence, captured_at, resolution_cm, bbox, online_only
Feature       layer, geom (Geometry, 4326), properties (JSONB),
              risa_type, risa_status [ok|partial|no|unknown], label,
              source_ref (Kobo _uuid or uploaded fid), observed_at
KoboSource    layer, server_url (on ALLOWED_SERVERS), asset_uid, token (encrypted),
              field_map (JSON), last_synced_at, last_submission_id
Product       site, kind [page1], title, version_label, language, page_size, view,
              layers + styles, key_message, glance overrides, logos, sources,
              disclaimer, credits
ProductVersion product, n, rendered_at, pdf_key, snapshot (JSON)
Asset         logos (NDMA, partners)
Export        target, format [gpkg|geojson|csv|bundle], file_key, created_at
Job           kind, target, status, progress, log
```

IDs are UUIDs, so bundles from different instances merge without collisions. `risa_type` and `risa_status` are columns because the symbology, legend, at-a-glance figures and later page 2 all use them.

### Kobo integration

- Pull from `{server}/api/v2/assets/{uid}/data/?format=json`, paging, and filtering on `_id` greater than the last synced one.
- Geometry comes from the first `geopoint` question (or a chosen one), falling back to `_geolocation`. `geotrace` and `geoshape` become lines and polygons.
- **Field map**: a JSON mapping from questions and choices to `risa_type`, `risa_status`, `label` and popup fields. A preset for the standard RISA XLSForm (the one kobo-in-a-box R1 deploys) means a RISA project works with no setup. Other forms get a mapping screen built from `GET /api/v2/assets/{uid}/`. Unmapped answers show as "Not assessed", never as a status.
- Sync with "Sync now" and every 10 minutes while a response is active.
- RISA field data is observation-only (SOP v2). The sync still drops `_submitted_by` and any question marked sensitive.

### GIS export and bundles

- **GeoPackage**: one table per vector layer, with Kobo layers flattened to columns. Each layer's QML style goes in the `layer_styles` table, so QGIS opens it with RISA symbology. A `metadata` table holds sources, dates and the permalink. Orthomosaics are offered as the COG file.
- **Response bundle**: a zip holding the GeoPackage, the COGs, `response.json` (sites, layer settings, styles, products, field maps; Kobo tokens are left out) and the rendered PDFs. Import merges by UUID. Uses: preload a box from the cloud before a mission, send a box's work to the cloud or an NDMA server when a link appears, and archive a response.

### Access with an edit key

- **Viewing** is open at unlisted URLs (`/r/<response>/<site>`), with `noindex`. A response marked private is hidden from the index page.
- **Editing** (uploads, drawing, Kobo connections, renders, imports) needs the response's **edit key**, shown once when the response is created and stored hashed. The browser keeps it in local storage and sends it as a header. Keys can be rotated in the admin.
- Rate limits on edit endpoints and uploads. A setting `READ_ONLY_PUBLIC=false` makes viewing need the key too, for NDMAs who want nothing public.

---

## 5. Hosting the consortium instance on DigitalOcean

App Platform app `risa-dash`, region `fra`, deploys on every push to `main`, the same as the RISA site. The domain `risa-dash.kobolabs.dev` is a record in the `kobolabs.dev` zone on DO.

| Component | Type | Notes | Approx. cost/month |
|---|---|---|---|
| `web` | Service (Dockerfile) | Django + gunicorn: `/api`, `/admin`, `/print`, tiles, uploads | $12 (1 GB) |
| `frontend` | Static site | Vite build, SPA catch-all | $0–3 |
| `worker` | Worker (same image) | Jobs, GDAL, Chromium | $25–50 (2–4 GB) |
| Database | Managed PostgreSQL 16 | Enable `postgis` | $15 |
| Storage | Spaces + CDN | CORS for range requests from the app origin | $5 + transfer |

About **$60–85/month**. Backups: managed Postgres daily, and Spaces versioning on `products/`. Sentry is optional through `SENTRY_DSN`, never on a box.

If a multi-GB orthomosaic exceeds the worker's memory, run that conversion on a temporary Droplet, or ask the drone team for a COG from WebODM.

The self-host path must not rot while the cloud runs on App Platform, so **CI runs the full compose stack** (PostGIS, filesystem storage, an http fake Kobo, outbound network blocked) and does an end-to-end check: upload, sync, render, export, bundle round trip.

---

## 6. Repo layout

```
risa-dashboard/
  backend/
    config/               settings from env (ALLOWED_SERVERS, STORAGE, PUBLIC_URL, BASEMAPS, ...)
    risa/                 responses, sites, layers, features, products (models, api, admin)
    risa/ingest/          tus uploads, COG conversion, vector import
    risa/kobo/            client, allow-list checks, field maps (RISA XLSForm preset), sync
    risa/exports/         GeoPackage + QML, GeoJSON, CSV, bundles (export/import)
    risa/print/           Playwright render job
    risa/pack/            offline content pack build/load
    risa/symbology/       RISA styles defined once → MapLibre JSON, QML, legend CSS
    pyproject.toml        uv
  frontend/
    src/api/              generated client
    src/map/              MapLibre wrapper, PMTiles/COG protocols, swipe, draw, furniture
    src/routes/           index, response, site map, product editor, print
    src/print/            page 1 layout (A3/A4 landscape)
    src/theme/            the one neutral theme file, replaceable by the RISA brand
  deploy/
    Dockerfile            one image, web and worker roles (GDAL + Chromium), amd64/arm64
    compose.yaml          self-host: web, worker, postgis, caddy (profile), volumes
    compose.box.yaml      box overlay: no caddy, edge-nginx snippet, extra_hosts for kf.kobo.local
    nginx/risa.conf       edge snippet for risa.kobo.local (media with range requests, big uploads)
    .env.example
  .do/app.yaml
  docs/self-hosting.md
  plans/
```

---

## 7. Phases

About 7–8 weeks for one developer. Each phase ends deployed to risa-dash.kobolabs.dev, with the compose stack passing in CI.

**Phase 0 · Skeleton and spikes (week 1)**
- Repo, one Dockerfile, compose, CI (ruff, mypy, pytest, eslint, tsc, vitest, compose e2e with no outbound network), App Platform app and DNS.
- **Spike: print.** Render MapLibre over the Venezuela ortho plus a PMTiles basemap to an A3 PDF at 300 dpi, in headless Chromium on App Platform and in a container with no GPU or network. Measure time and memory.
- **Spike: COG in the browser.** Load the Venezuela ortho with `maplibre-cog-protocol` from Spaces and from nginx on a local volume. If it's too slow, switch to TiTiler now.

**Phase 1 · Map viewer (weeks 1–3)**
- Responses, sites and layers; edit keys; generated client.
- Site page: layer panel (toggle, reorder, opacity), basemap switcher, popups, URL view state.
- Resumable uploads, COG job, imagery layers with date and resolution, before/after swipe, satellite layers by URL.
- Vector upload with RISA presets. PMTiles basemap and `pack build`/`pack load`.

**Phase 2 · Kobo (week 4)**
- `ALLOWED_SERVERS` with kf, eu and custom servers, and the exact-match http rule. Connect, RISA preset, mapping screen, sync, photos.
- Site summary panel and at-a-glance figures.
- Test against kf, eu and a local Kobo on http (the kobo-in-a-box droplet with `offline.sh on`).

**Phase 3 · Annotate and style (week 5)**
- Terra Draw annotations with type, status and label. Labelled polygons as in MA023.
- Style editor on the presets. Legend from visible layers.

**Phase 4 · Page 1 print (weeks 6–7)**
- Product editor: frame the extent on a page-shaped overlay, header fields, key message, at-a-glance overrides, logos, sources, inset.
- Page 1 layout at A3 and A4 landscape. Render job, versions, latest permalink and QR code.
- Rebuild the Venezuela site and compare it with MA023 alongside MapAction.

**Phase 5 · Export, bundles, self-hosting (weeks 7–8)**
- GeoPackage with QML styles, GeoJSON, CSV, COG download. Test in QGIS 3.40 LTR and ArcGIS Pro.
- Response bundle export and import; a cloud → box → cloud round trip.
- `docs/self-hosting.md`, `compose.box.yaml` and the edge snippet. Install on the kobo-in-a-box droplet next to Kobo, cut it off with `offline.sh on`, and run the MVP test there.
- A demo response from the fictional sample site on the RISA site, for showing the tool without real data.

**After the MVP**: pages 2 and 3; live sync between instances; Kobo webhooks; MBTiles for QField and KoboCollect; a `.qgz` project export; accounts (Kobo OAuth); interface translations; the RISA brand when chosen; AI candidates from imagery (box R11) as a review layer.

---

## 8. Decisions (29/10/2026)

| Question | Decision |
|---|---|
| Domain | `risa-dash.kobolabs.dev` for now |
| Editing access | A shared edit key per response is enough for now |
| Brand | Neutral, replaceable later through one theme file |
| Print layout | RISA product page 1 |
| Test data | MapAction shares the Venezuela orthomosaic and Kobo export |
| Kobo servers | kf, eu, or a custom server through an allow-list, as kobo-dash does |
| Operators | The RISA consortium for now. Must be self-hostable by NDMAs and others, and run fully offline as on kobo-in-a-box |

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| WebGL in headless Chromium without a GPU is slow or fails at 300 dpi A3 (about 4960 × 3508 px) | Phase 0 spike. SwiftShader, tiled map render, or the map at 200 dpi with vector text |
| Large orthomosaics are slow in the browser, or the conversion exhausts memory (worse on a shared box) | COG with overviews and JPEG/WebP compression; `GDAL_CACHEMAX`; TiTiler fallback; accept COGs from WebODM |
| The cloud and self-host paths drift apart | One image; compose e2e with the network cut in CI on every push |
| Something calls the internet and breaks offline | No runtime external requests by design; CI blocks outbound traffic; online-only layers are flagged and hidden offline |
| Imagery licences (Esri limits export and print; Maxar Open Data is CC BY-NC) | Attribution and licence per layer, printed automatically; open sources for the content pack |
| Open write access gets abused | Edit key, rate limits, upload size limits, cleanup of abandoned uploads |
| Kobo forms vary | RISA preset, mapping screen, unmapped answers shown as "Not assessed" |
| Data protection (where displaced people's shelters and services are) | Observation-only by design; unlisted and `noindex`; private flag; `READ_ONLY_PUBLIC=false`; in-country hosting. Review with the consortium before the first live response |

## 10. Still open

1. **Venezuela data**: who at MapAction sends the orthomosaic and Kobo export, and is it OK to keep them on Spaces (or should they stay on the box/droplet only)?
2. **The box**: should this tool be the box's RISA imagery path (R4), and should the box Postgres become a PostGIS image so it can be shared? To agree with the kobo-in-a-box plan.
3. **Hostname on the box**: `risa.kobo.local`, alongside `dash.` and `mcp.`?
4. **Repo and images**: which GitHub org, and is GHCR fine for the published images that NDMAs pull?
5. ~~Licence~~: decided, AGPL-3.0 like KoboToolbox KPI.

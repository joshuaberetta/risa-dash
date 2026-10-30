# RISA Dashboard: MVP plan

Status: draft, not started. Decisions of 29/10/2026 included (section 8).

A web tool for RISA responses. It puts drone imagery, satellite imagery, KoboCollect observations and analysis layers on one interactive map, prints page 1 of the RISA product (the Common Operational Picture) to PDF, and exports the data for QGIS and ArcGIS. During a response the web tool is the main interface, and the PDF is the reference for low-connectivity settings. It turns the "Interactive version" mock on the RISA product page (`~/code/risa/site/themes/*/product.html`) into a working product.

The consortium runs it first, at **https://risa-dash.kobolabs.dev**. It must also be **self-hostable** by an NDMA or anyone else who needs the data held in-country, and run **fully offline** on a kobo-in-a-box (`~/code/kobo-in-a-box`, see `RISA-PLAN.md` R4, R5, R8, R9 and R11) next to a local Kobo server, with its AI features on **local models** (section 2, Local AI models). Several offline instances can work as a **federation** (field kits, a hub, the cloud), as the box does for Kobo data (section 2, Federated). An **MCP server** lets an AI assistant, such as OpenCode on the box's local model, set up and run the dashboard and its analysis, and act as its support desk (section 4, MCP server).

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
| 12 | **Imagery analysis (simulated)** | One button per site: detect shelters and buildings on the orthomosaic, group shelters into blocks and outline the site. Results are suggestions to accept, reject, re-tag or reshape; only accepted shelters count. A simulated detector stands in for the model until one is chosen (section 4, Imagery analysis) |

### Not in the MVP

User accounts and roles. Pages 2 and 3 of the product (key findings, hotspot); the layout engine is built so they can be added next. Live sync between instances (the bundle covers it for now; federation is planned in section 2). Local text and vision models, the MCP server and the assistant (planned in sections 2 and 4, built after the MVP; the MVP's settings and API are shaped so they fit). Kobo webhooks (polling first). Interface translations; text on the printed product is free text, so Spanish and French maps work from day one. A real segmentation model (the MVP ships the review workflow with a simulated detector), in-browser photogrammetry.

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
| AI models | Detector on a GPU droplet on demand; text model on the same droplet (llama-server) or a provider, if the consortium agrees | Their own llama-server (optional `ai` compose profile), or AI features off | The box's llama-server and GPU, shared with Kobo's AI |
| Assistant | MCP at `/mcp`, any MCP client | MCP at `/mcp` | MCP at `mcp.kobo.local/risa`, OpenCode on the box's agent model |
| Federation | Receives from hubs and NDMA servers | Hub or receiver | Field kit or hub |

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
- **R4 drop folder**: the worker watches the box's imagery drop folder (read-only mount, e.g. `/srv/risa/drop`), so a 5 GB orthomosaic copied over SMB is imported without a browser upload. The import is offered in the dashboard ("New imagery in the drop folder") and through the MCP server.
- **Shared box services, not copies**: the dashboard uses the box's llama-server, GPU, kobo-knowledge and OpenCode when they're there, and runs without them when they aren't (a laptop with Docker, a 16 GB Kobo-only kit). It never starts its own large model on a box.
- **Hostnames and landing page**: `risa.kobo.local` for the dashboard and `mcp.kobo.local/risa` for its MCP server, next to `dash.` and `mcp.`; a tile on the landing page; `firstboot.sh` generates `SECRET_KEY`, `TOKEN_KEY` and the instance ID.
- **R2, R6, R7, R9, R11**: the dashboard's GeoPackage export can be R2's output (or R2's QA checks run against it); R6's agent skills call the dashboard's MCP tools; the dashboard's user guide joins R7's RISA collection in the knowledge base; R9 (multi-site) is the federation below; R11 track B (orthomosaics) is the imagery analysis in section 4, and track A (ground photos) runs on Kobo photos the dashboard already syncs.

### Local AI models

Every AI feature calls a model the instance runs or is pointed at. None needs a cloud AI provider, and no imagery, photo or field data leaves the instance unless an operator configures an outside endpoint.

| Job | Model on a box | Runs as | Without it |
|---|---|---|---|
| Shelter and building detection | The chosen detector (section 4), ONNX, weights in the content pack | Worker job, ONNX Runtime on CPU or the box GPU (ROCm or Vulkan, to test on the W5 unit) | The simulated detector, or drawing by hand |
| Learning from corrections | Same model, PyTorch | A `trainer` job on the box GPU, overnight on mains or solar; a GPU droplet on the hosted instance | The previous version stays in use |
| Situation brief, key message draft, wording of findings | The box's batch model: Gemma 4 26B-A4B, or gpt-oss-120b on the 128 GB unit, through llama-server's OpenAI-compatible API | Worker job, queued behind Kobo's batch work | Computed figures and rule-based findings only; the key message is typed |
| Photo checks (R11 track A): photo matches the category, blurred or dark, faces to blur, hazard hints | Gemma 4 with image input, plus a small face detector | Worker job after each Kobo sync | No hints; photos shown as they are |
| Search across guides and SOPs | bge-m3, through the box's kobo-knowledge | Box-wide service | The assistant answers from the dashboard's own docs only |
| Assistant | The box's agent model (gpt-oss-120b for changes, Gemma 4 26B for questions, per W4) | OpenCode, through the MCP server | The dashboard works as before |

- **Settings**: `LLM_BASE_URL` (OpenAI-compatible: the box's llama-server, a GPU droplet, or a provider), `LLM_MODEL`, `VLM_MODEL`, `DETECTOR_WEIGHTS`, `AI_FEATURES` (which of the above are on). Empty `LLM_BASE_URL` turns the text features off and everything else still works.
- **Without a box**: an optional `ai` compose profile adds llama-server with a Gemma 4 GGUF from the content pack, for an NDMA server or a laptop with a GPU.
- **Same prompts everywhere**: the hosted instance should use the same open models as the box (llama-server on the GPU droplet), so a brief drafted online and one drafted offline read alike and are measured on one test set. A provider is a fallback, only with the consortium's agreement on what it may see.
- **Text models draft, people decide**: the brief and key message are drafts, marked with the model's name, edited and accepted before they reach page 1, as detections are. Figures are never written by the model: it gets the computed summary and the text is checked so every number in it matches a computed figure, or the draft is rejected.
- **Tiers** (kobo-in-a-box PLAN.md): the 128 GB unit runs everything; 64 GB runs the detector and Gemma 4 26B; the 16 GB Kobo-only tier runs the dashboard with AI off.

### Federated: field kits, a hub, the cloud

The same three modes as kobo-in-a-box (concept note, "Three ways to run it"):

```
  field kit A (site A) ──┐
  field kit B (site B) ──┼── cable / LAN / USB ──▶  hub kit at base  ──(when online)──▶  consortium instance
  field kit C (site C) ──┘                          response-wide view                  or the NDMA's server
                    ◀── response setup, field maps, content pack, detector versions ──
```

1. **Standalone**: one instance does everything, and nothing leaves it.
2. **Networked**: a kit per site, each with its own dashboard; a hub at base combines them and shows the whole response, still offline.
3. **Connected**: the hub (or any kit) syncs to the consortium instance or the NDMA's server when a link appears.

What moves, and how:
- **Kobo data doesn't go through the dashboard.** kobo-transfer already copies submissions kit → hub → cloud (safe to repeat, with attachments and validation statuses). Each instance's Kobo layer points at its own local Kobo, so the hub's dashboard reads the hub's combined project, where each kit marks its submissions with its site identifier. The field map travels with the response settings.
- **The dashboard's own data** (sites, drawn and uploaded features, imagery, review decisions and labels, detector versions, products and their versions) travels as the **response bundle, made incremental**: a changeset of everything since the peer last confirmed. IDs are UUIDs already; synced rows add `origin` (the instance that made them) and a revision. Import is idempotent, as kobo-transfer is: sending again changes nothing.
- **Ownership instead of merging.** Each site is owned by one instance, normally the kit that assesses it; others hold read-only copies until ownership is handed over explicitly (the kit leaves, the hub takes over). Response-wide products belong to the hub. With no user accounts this avoids edit conflicts rather than resolving them.
- **One direction for data, the other for setup.** Data flows kit → hub → cloud. Setup flows hub → kits before and during the mission: the response and its sites, field maps, symbology, the content pack and new detector versions.
- **Transport**: the bundle file (USB, or the drop folder), or an HTTP push between instances on the LAN or over the link, with a per-peer sync key and resumable parts, like uploads. Order follows the R8 outbox: changes and PDFs first, then vectors and labels, then reduced-resolution imagery, then full-resolution COGs. Never on by default: the focal point chooses what leaves.
- **Learning across kits**: labels from every kit's reviews reach the hub, the hub (the one with a GPU) trains the response's detector on all of them, and the new version goes back to the kits. Held-out scores are reported per site as well as overall, so a version that is better on average but worse at one site shows up before it is sent.
- **Across responses and organisations**: labels go into a shared base model only with the data owner's consent (section 4). Where labels may not leave, an option to study is sharing model updates instead of labels (federated averaging), so no imagery or labels leave the kit or the country. A research option, not a commitment.
- **The hub's view** shows each site with where and when it came from ("Site B, from kit 2, as of 14:20"), and a response-wide summary across sites.

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

 AI assistant (OpenCode, any MCP client) ──▶ web: /mcp (same services as the API)
 worker ──▶ LLM_BASE_URL: llama-server (the box's, a GPU droplet's, or none) · detector (ONNX)
 web ◀──▶ peers: hub / field kits / consortium instance (incremental bundles)
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

After the MVP, for federation and the assistant:

```
Instance      id (UUID, made at first boot), name, role [standalone|kit|hub|cloud]
Peer          instance, url, sync_key_hash, last_sent_rev, last_received_rev, direction
Site          + origin (Instance), owner (Instance)
(synced rows) + origin, rev
Activity      response, at, actor [browser|assistant], client, action, target, before/after
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

### Imagery analysis (segmentation)

Automatic segmentation of the orthomosaic for each camp or area of interest, built into the dashboard rather than a separate tool. It turns hours of manual digitising into minutes of review, and feeds the figures RISA reports (shelters counted on imagery, shelters per block, people estimates).

**What it produces**, per area of interest, as one "analysis" layer:

| Class | Geometry | Use |
|---|---|---|
| Shelter (tent, tarp, sheet-metal shelter) | Footprint polygon | Count, density, shelters per block, people estimate (× household size) |
| Building | Footprint polygon | Collective centres, services, damage later |
| Block | Polygon round a cluster of shelters, with a count | Planning, page 1 labels, "where do we act first" |
| Site boundary | Polygon | The camp's extent on the map and in exports |
| Later: standing water, debris, latrines, water points, roads and paths | Polygons and lines | Hazards, access, services from imagery to check against Kobo |

**Human in the loop.** Every feature carries `class`, `confidence`, `model` and `review` (suggested, accepted, rejected; `edited` when a person changed it). Suggested features are dashed on the map and in print, accepted ones solid, rejected ones hidden. Review is one at a time (accept, reject, re-tag, reshape with the same tools as drawing) or in bulk by confidence. Only accepted features count in the summary and on page 1. This follows kobo-in-a-box R11: an `ai_candidates` layer reviewed by a GIS specialist, nothing published without review.

**Pipeline** (worker job, one per area of interest): cut the area from the COG at about 25 cm/px → tile with overlap → run the model → merge across tile edges → polygonise and simplify → classify by class and size → write features → derive blocks (DBSCAN over shelter centres, then concave hulls) and the boundary in PostGIS. Progress is reported per step so the interface can show it.

**Model options**, to try on the Venezuela and Mozambique orthomosaics against hand-labelled samples and the Kobo points:
- HOT's fAIr and RAMP (open building-footprint models trained on drone imagery, fine-tunable on a few hundred labelled shelters per context).
- Segment Anything (SAM 2) prompted with Kobo points or a box, for outlining what a person points at.
- A small detector (YOLO family, ONNX) fine-tuned on tents and tarps, for counting at speed on a CPU or a laptop GPU.

Run them with ONNX Runtime on the worker (CPU, slow but simple), on a GPU droplet for big sites, or on the box's GPU offline. The interface, data model and review workflow stay the same whichever model wins: the model replaces one function.

**MVP: simulated.** `risa/analysis.py` implements the whole pipeline and review workflow with a stand-in detector: colour rules on the real image (bright grey roofs and blue tarps as shelter candidates, large bright roofs as buildings). Its outlines sit on real objects, so reviewing them is realistic, but counts are not reliable. Every feature and the layer say "simulated", and the dialog says so before it runs. On the Haiti sample (0.5 km², 3.3 cm/px) it finds about 2,100 shelter candidates, 22 buildings and 15 blocks in about 10 s locally.

### Learning from corrections (fine-tuning)

The people reviewing the detection are labelling training data as they go. Every review is kept as a label: accepted, reshaped (`edited`), re-tagged and hand-drawn missed shelters (`added`) are positives, rejected suggestions are negatives. Over a response this adds up to thousands of labels from the exact imagery, camp layout and shelter types in that context, which is what general-purpose building models lack.

**Loop:** detect → review in the dashboard → learn a new version → detect again, with each version better for that response. Versions are kept per response, because camps in one emergency look alike and differ from the next: the Venezuela stadium camp, a Mozambique resettlement site and Cox's Bazar need different models. Each version records how many reviews it learned from and its accuracy, precision and recall on reviews held back from training, next to the version before, so nobody has to take an improvement on trust. Every detected feature records the model version that made it.

**In the MVP (simulated):** the loop runs end to end with the stand-in detector. "Learn from corrections" in the AI analysis tab (needs 20 reviews each way) fits a small logistic model on simple image features of each candidate (size, shape, brightness, saturation, blue), and widens the colour and size rules towards what people accepted or drew, a step per version. The next detection uses it to re-score candidates and drop the kind people reject. On the Haiti sample, with a reviewer who rejects thin strips and dim patches, version 1 was right on 91% of held-back reviews against 47% for the built-in rules, and the share of results that reviewer would reject fell from 26% to 16%. "Draw missed shelters" adds positives the detector didn't find. "Download training data" exports the imagery for the area plus labels and negatives as GeoJSON, ready for the real thing.

**The real thing (after the MVP, a sizeable piece of work):**
1. **Choose the base model** on the Venezuela and Mozambique orthomosaics (see Imagery analysis): likely a fAIr/RAMP footprint model, or a YOLO-family segmenter, both small enough to fine-tune on one GPU.
2. **Training service:** a job that takes a response's labels, cuts image chips around them (with negatives and unlabelled background sampled inside reviewed areas only), fine-tunes from the base or the previous version, evaluates on a fixed held-out set, and registers the version only if it beats the one before. Runs on a GPU droplet on demand (minutes per version for a few thousand labels) or on the box's GPU offline, where it's slower and runs overnight.
3. **Active learning:** show reviewers the suggestions the model is least sure about first, so each review teaches it the most.
4. **Sharing across responses**, with consent: a consortium base model improved with labels from many responses (fAIr already does this with OSM labels), while each response keeps its own fine-tuned version. Labels go into the base model only with the data owner's agreement; imagery of displacement sites is sensitive.
5. **Safeguards:** a version never replaces the previous one without better held-out scores; counts on page 1 still come only from accepted features; model cards (data, dates, scores, known failure modes) for every version.

Rough size: 4–6 weeks for one ML engineer after the base model is chosen, plus GPU time. The labels the MVP already collects carry over unchanged.

### MCP server: an assistant that builds, runs and supports the dashboard

An MCP server over the same service functions as the API, so an AI assistant can set up a response, run the analysis, prepare page 1 and help people when something goes wrong. Streamable HTTP at `/mcp`, served by the web process (no new container): `http://risa.kobo.local/mcp`, or `mcp.kobo.local/risa` behind the box's edge. On the box it is registered in OpenCode next to kobo-mcp and kobo-knowledge, running on the box's agent model with no internet; online, any MCP client can use it.

**Tools, in profiles** (`MCP_TOOL_PROFILES`, as kobo-mcp's `TOOL_PROFILES`), so a local model only sees what its job needs and the prompt stays short:

| Profile | Tools |
|---|---|
| `view` | `list_responses`, `get_site`, `get_site_summary`, `list_layers`, `query_features` (type, status, area), `get_kobo_status`, `get_detection_status`, `list_detector_versions`, `list_products`, `get_product`, `get_job` (progress and log), `preview_product` (PNG) |
| `build` | `create_response`, `create_site` (boundary from a layer, a drawn area or a box), `import_from_drop_folder` (no multi-GB uploads through a chat), `add_layer_from_url`, `connect_kobo_project`, `set_field_map`, `sync_kobo`, `draw_feature`, `update_feature`, `set_layer_style`, `reorder_layers` |
| `analysis` | `run_detection` (site or area), `get_review_queue` (counts by confidence, least certain first, with links to review them), `train_detector`, `draft_brief`, `draft_key_message`, `compare_visits`, `check_points_against_imagery` (Kobo points with nothing under them, shelters with no observation nearby) |
| `products` | `create_product`, `update_product` (title, version, key message, at-a-glance overrides, extent), `render_product`, `export_gpkg`, `export_bundle`, `sync_push` |
| `support` | `get_health` (failed jobs, storage, Kobo reachability, last sync errors, model endpoints), `explain_job` (a failed job's log in plain words, with the likely cause), `retry_job`, `get_settings` (non-secret) |

**Rules**, carrying over "AI proposes, a person decides":
- **Review stays with people.** No tool accepts or rejects detection suggestions. The assistant can run detection and report the queue, not clear it. The same goes for drafts: `draft_key_message` writes a draft the person accepts in the product editor.
- **Rendering a version** (what the QR code points to) and `sync_push` need confirmation in the client (OpenCode `ask`). Previews are free. Delete tools aren't exposed at all.
- **Keys and tokens**: the assistant sends the response's edit key, as the browser does; without one it is read-only. Kobo tokens never pass through a chat: `connect_kobo_project` uses a connection the user has already authorised in the dashboard (or, on the box, kobo-mcp's sign-in).
- **Logged and undoable**: every change made through MCP is in the response's activity log as "via assistant", with the client, and features and styles can be put back from it.
- **Small enough for local models**: short tool descriptions, measured the way kobo-in-a-box PLAN.md 3h measures kobo-mcp's (target under about 4k tokens for `view,build,analysis`), because OpenCode resends them every turn.

**Skills** (OpenCode skills, kobo-in-a-box R6), narrow, with the heavy work in the tools:
1. *Set up a site*: from the drop folder's orthomosaic and a Kobo project, create the site, map the form, sync, frame page 1.
2. *Daily update*: sync Kobo, import new imagery, run detection on it, report the review queue, draft the key message, preview page 1.
3. *QA before printing*: points outside the boundary, unmapped answers, Kobo points with no shelter under them, figures still marked TBC.
4. *What changed since the last visit* (RISA step 6).

**As a support bot**, the same assistant is the dashboard's help desk, with no internet:
- **Knowledge**: a user guide for the dashboard (to write, `docs/guide/` in English, Spanish and French, starting from the walkthrough text in `tours.ts` and the README), indexed in the box's kobo-knowledge as a `risa-dashboard` collection next to R7's SOP collection, so answers cite pages that open offline.
- **Look before answering**: "my orthomosaic doesn't show" → `get_health` and `explain_job` find the failed COG job and say why (no georeferencing, not a GeoTIFF) and what to do; "Kobo points are missing" → last sync error, field map, submissions with no geopoint.
- **From the dashboard**: a **Help** entry in the header opens the assistant (OpenCode web, later OpenWork) with the current response, site or product in the first message. Shown only when `ASSISTANT_URL` is set. Online, it can point to Kobo's support bot with the same guide indexed.
- **Configuration, not code**: on the 128 GB unit, the coding agent can also write configuration in its workspace (a field-map preset for a new form, a symbology variant, page-1 defaults for an NDMA) and load it through tools after a person checks it. It does not change the running dashboard's code.

**Measured, as W4 was**: 20–30 tasks (set-up, update, product, QA, and support questions with faults planted: a broken upload, a revoked Kobo token, an unmapped form), scored on tools used, answers and the dashboard's state, on gpt-oss-120b and Gemma 4 26B, with the internet blocked. Following W4, changes only on gpt-oss-120b; Gemma for questions and support.

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
    risa/llm/             OpenAI-compatible client, prompts, number checks on drafts (after MVP)
    risa/mcp/             MCP server: tools by profile, skills (after MVP)
    risa/sync/            instances, peers, incremental bundles (after MVP)
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
  docs/guide/             user guide (en, es, fr), also indexed for the assistant
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

**After the MVP: offline AI, assistant and federation.** In this order, each tested on the kobo-in-a-box droplet with `offline.sh on`:

| | Work | Rough size | Depends on |
|---|---|---|---|
| A | **Offline complete**: bundle glyphs, `pack build`/`pack load`, `compose.box.yaml`, edge snippet, drop-folder import; the MVP test on the box with the internet cut | 1 week | Box W9 |
| B | **Local models**: `risa/llm` client and settings; brief and key-message drafts with number checks; photo checks on Kobo sync (R11 track A); the chosen detector through ONNX on the box GPU | 2–3 weeks, plus the ML work below | Box llama-server; R11 spike |
| C | **MCP and assistant**: tools by profile, activity log, skills, the user guide in kobo-knowledge, the Help entry, the 20–30 task evaluation on the box's models | 2–3 weeks | Box W4 and 3i |
| D | **Federation**: instance ID, `origin`/`owner`, incremental bundles, HTTP push between peers, the hub's view, detector versions sent to kits; tested with two kits and a hub, with the links between them cut and restored | 3–4 weeks | Bundles (Phase 5); box hub work (R9) |

**Also after the MVP**: a real segmentation model (spike on the Venezuela orthomosaic: precision and recall against hand-labelled shelters, time per hectare on CPU and GPU), then fine-tuning it on reviewers' corrections (section 4, Learning from corrections; the MVP already collects the labels), and feeding accepted counts into people estimates and the AI analysis brief; pages 2 and 3; Kobo webhooks; MBTiles for QField and KoboCollect; a `.qgz` project export; accounts (Kobo OAuth); interface translations; the RISA brand when chosen; imagery classes beyond shelters and buildings (water, debris, services).

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
| Segmentation counts read as fact (a model, or today the simulation, is wrong in ways people don't see) | Suggestions are dashed and labelled; only accepted features count; confidence and model are kept on every feature and in exports; the simulation is marked everywhere |
| A text model invents or changes figures in the brief or key message | It gets the computed summary; every number in a draft must match a computed figure or the draft is rejected; drafts are accepted by a person |
| The assistant acts wrongly on a smaller local model (W4: Gemma 4 26B got 0/2 changes right) | Changes only on gpt-oss-120b; Gemma on read-only and support profiles; no review, delete or publish without confirmation; every change logged and undoable |
| Tool definitions make local agents too slow (OpenCode resends ~21k tokens a turn) | Profiles; short descriptions with a measured token budget; narrow skills |
| Federated instances disagree about the same site | One owner per site, explicit handover, read-only copies elsewhere; idempotent imports; per-site "as of" shown on the hub |
| Labels or imagery leave a kit or the country without agreement | Sync never on by default; the focal point chooses what leaves; labels into a shared model only with consent; model-update sharing studied as an alternative |
| Data protection (where displaced people's shelters and services are) | Observation-only by design; unlisted and `noindex`; private flag; `READ_ONLY_PUBLIC=false`; in-country hosting. Review with the consortium before the first live response |

## 10. Still open

1. **Venezuela data**: who at MapAction sends the orthomosaic and Kobo export, and is it OK to keep them on Spaces (or should they stay on the box/droplet only)?
2. **The box**: should this tool be the box's RISA imagery path (R4), and should the box Postgres become a PostGIS image so it can be shared? To agree with the kobo-in-a-box plan.
3. **Hostname on the box**: `risa.kobo.local`, alongside `dash.` and `mcp.`?
4. **Repo and images**: which GitHub org, and is GHCR fine for the published images that NDMAs pull?
5. ~~Licence~~: decided, AGPL-3.0 like KoboToolbox KPI.
6. **Text model on the hosted instance**: the box's open models on a GPU droplet (same results online and offline), or a provider, and what it may see under the data agreement?
7. **The hub's hardware**: training detector versions for every kit needs the GPU unit at the hub; can field kits be the budget tier, as for Kobo?
8. **One assistant or several**: one OpenCode with kobo-mcp, kobo-knowledge and this MCP server together (simpler, longer prompt), or a RISA agent profile with only the RISA tools? To measure in the evaluation.
9. **Federation transport first**: bundle files only (USB, drop folder) for the pilot, with HTTP push between peers after, or both from the start?

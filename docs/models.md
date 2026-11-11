# Imagery analysis: models, training data and evaluation

For research partners and model developers. How a model plugs into the RISA Dashboard, what training data the dashboard produces, how models are scored, and where they have to run. The partner-facing summary is [`partner-brief.md`](partner-brief.md).

## What the analysis does

A responder uploads a drone orthomosaic of a displacement site (typically 2–10 cm/px, 0.1–5 km²). **Detect shelters on imagery** cuts the area of interest from it, runs a detector, and stores what comes back as *suggestions*: shelters and buildings, each with a class, a confidence and the model that made it. The dashboard then groups shelters into blocks (DBSCAN on centroids, concave hulls) and outlines the site, both in PostGIS, whatever the detector.

Nothing counts until a person reviews it. Suggestions are dashed on the map and in print; reviewers accept, reject, re-tag or reshape them one at a time or in bulk by confidence, and draw shelters the model missed. Only accepted shelters count towards the figures RISA publishes (shelters counted on imagery, shelters per block, people estimates). Every review is kept: it is a label.

```
orthomosaic (COG) ──read_aoi──▶ RGB array at the detector's GSD ──detector──▶ candidates
   ──▶ suggestions (PostGIS) ──review──▶ accepted / rejected / edited / added
   ──▶ figures, page 1 ─┐
   ──▶ evaluation ◀─────┼── reference shelters
   ──▶ training data ───┘   (Ultralytics YOLO tiles + GeoJSON)
```

## The detector contract

Code: [`backend/risa/detectors/`](../backend/risa/detectors/__init__.py). A detector is a Python class registered at import:

| Attribute / method | |
|---|---|
| `id`, `label`, `short` | Stored on every feature it makes; shown in the dashboard |
| `simulated` | True for stand-ins; their output is marked as such everywhere |
| `gsd` | Metres per pixel it wants the image at (the dashboard resamples) |
| `max_pixels` | Above this, the area is read coarser, to stay within memory |
| `available()` | `""` if it can run on this instance, else why not (missing weights, packages) |
| `detect(rgb, valid, georef, tmp, report)` | Returns a list of `Candidate` |

Inputs: `rgb` is `uint8 [h, w, 3]`; `valid` is `bool [h, w]` (inside the image); `georef` has the GDAL geotransform in EPSG:3857 (`gt`), metres per pixel in Web Mercator units (`tr`) and the Web Mercator scale at the site (`k`, ground metres × k = Web Mercator units); `report(step, pct)` updates the progress the dashboard shows.

Output: `Candidate(geom, cls, confidence, area_m2, stats)`, with `geom` a Polygon in EPSG:4326, `cls` `"shelter"` or `"building"`, `confidence` 0–1, and `stats` anything worth keeping with the feature (the model's own class, the box in pixels).

The dashboard handles tiling the reading, storage, review, blocks, the boundary, figures, print, exports and evaluation. A model only has to turn pixels into scored polygons. Weights live in `MODELS_DIR` (`/opt/models` in the image), fetched and checked by [`scripts/fetch-models.sh`](../scripts/fetch-models.sh) at build time, or copied in for an offline box.

## Detectors today

| id | What | Licence | GSD | Speed (0.5 km², CPU) |
|---|---|---|---|---|
| `simulated` | Colour rules on the image: bright grey roofs and blue tarps. A stand-in, so the workflow could be built before a model | AGPL-3.0 (ours) | 25 cm | 14 s |
| `yolo-shelters` | YOLOv8n fine-tuned on drone imagery of camps around Goma (DRC), in Chad and in Mozambique ([alex6H/RefugeeCampShelterDetection-YOLOv8](https://github.com/alex6H/RefugeeCampShelterDetection-YOLOv8)). 15 classes; dwelling, hut, shelter (formal, informal) and tent count as shelters, building as building. Boxes, axis-aligned | MIT; trained with Ultralytics (AGPL-3.0) | 9 cm | 33 s (multi-core laptop) |

`yolo-shelters` runs with ONNX Runtime on 1024 px tiles overlapping by 192 px, with a confidence floor of 0.05, and suppresses boxes that overlap a more confident one (IoU ≥ 0.4) or lie mostly inside one (≥ 60 % of their area): across tile edges the model returns a roof whole and again in part. 9 cm and the 0.05 floor did best of 5, 7 and 9 cm and floors of 0.05 and 0.15 on the reference chips below.

## Evaluation

Code: [`backend/risa/evaluation.py`](../backend/risa/evaluation.py); in the dashboard, the **Models** card in the AI analysis tab; on the command line, `manage.py evaluate <analysis layer> <reference layer>`.

- **Reference**: a layer of shelters a person marked (one point per shelter) or outlined (polygons), plus, optionally, the areas they looked at (polygons with `properties.role = "area"`), which may hold no shelters at all (open ground, to count false alarms).
- **Scored area**: those areas; else a given box; else the reference's outline grown by 5 m. Detections are in if their point-on-surface is; references if they intersect.
- **Matching**: one to one, most confident detection first. A reference point is matched by a detection that contains it; a reference outline by the detection overlapping it most, if IoU ≥ 0.3.
- **Measures**: precision, recall, F1, count error, and **wrong and confident**: the share of detections at ≥ 0.75 confidence that are wrong, because a model's errors look as sure as its successes to a reviewer. All of them at confidence thresholds 0 to 0.9, so the operating point can be chosen.
- **Raw output** is scored, whatever the reviews, so corrections don't flatter the model.

Point matching is lenient for boxes (a loose box containing the shelter's centre counts); outlines with IoU are the stricter test once a reference has them.

### The Haiti reference (indicative)

[`scripts/sample/haiti-reference-shelters.geojson`](../scripts/sample/haiti-reference-shelters.geojson), on IOM's 2012 orthomosaic of Aviation Camp, Port-au-Prince (3.3 cm/px, CC BY 4.0, via OpenAerialMap): three areas of about 37 × 37 m, shelters marked as points **by eye, by Claude, on 4 cm/px chips, not yet checked by a person**. 99 shelters inside the areas.

| Area | Ground | Shelters | simulated P / R / F1 | yolo-shelters P / R / F1 |
|---|---|---|---|---|
| 1 | Sheet-metal shelters standing apart | 42 | 1.00 / 0.21 / 0.35 | 0.92 / 0.81 / 0.86 |
| 2 | Dense, roofs running together | 57 | 1.00 / 0.16 / 0.27 | 1.00 / 0.60 / 0.75 |
| 3 | Warehouse, concrete, trees, a car | 0 | no false alarms | 1 false alarm, low confidence |
| All, from a whole-image run | | 100 | 0.94 / 0.17 / 0.29 | 0.90 / 0.71 / 0.79 |

What it says: off the shelf, a model trained on plastic-sheeting shelters in DRC transfers to Haitian sheet-metal shelters with high precision but misses about three in ten, mostly where roofs run together. That is the gap fine-tuning on reviewed labels from the context should close. Caveats: a small reference, marked by eye by a model rather than a person, and the settings were picked on the same chips, so the numbers are optimistic until there's a separate, person-checked test set; one site, one season, one image.

## Training data

**Download training data** in an analysis layer's menu (`GET /api/layers/{id}/training-data.zip`):

| File | |
|---|---|
| `image.tif` | The area of interest, a COG (EPSG:3857) |
| `labels.geojson` | Shelters and buildings people accepted, corrected (`source: edited`) or drew (`added`): positives, as polygons |
| `negatives.geojson` | Suggestions people rejected: hard negatives |
| `aoi.geojson` | The area analysed |
| `yolo/images/*.jpg`, `yolo/labels/*.txt`, `yolo/data.yaml` | 1024 px tiles at the detector's GSD with `class cx cy w h` boxes (0 shelter, 1 building): ready for `yolo detect train data=yolo/data.yaml` |
| `meta.json` | The model, GSD, counts and its latest evaluation |

Only **fully reviewed** tiles go into `yolo/`: tiles where every suggestion was accepted, corrected or rejected, so an unlabelled roof in a tile really is background. Bulk review by confidence counts as review, but those labels are the model's own calls confirmed wholesale, not a person's one by one (the dashboard doesn't record which yet). Over a response, the dashboard's reviews add up to thousands of labels from the exact imagery and shelter types of that context.

## Where models have to run

- **Online**, on the consortium's instance (DigitalOcean App Platform; the worker is 1 vCPU, 2 GB today), or an on-demand GPU droplet in the same region for big sites. No outside AI provider: imagery of displacement sites is sensitive.
- **Self-hosted** on a national authority's server, often with no GPU.
- **Fully offline** on a kobo-in-a-box field kit: CPU, or a consumer GPU on the hub (an RTX-class card), shared with Kobo and local language models. Weights travel in the kit's content pack.
- So: CPU inference in minutes for a site is the bar; ONNX (or a small PyTorch) model; a licence that allows redistribution inside an AGPL-3.0 tool by governments and NGOs (no non-commercial or research-only weights); a few hundred MB at most.

## What we'd like to build with a partner

1. **A person-checked benchmark**: outlines of every shelter in reference areas from several sites, contexts and seasons (Haiti, Venezuela's stadium camp, Mozambique resettlement sites, Cox's Bazar), with a fixed test split.
2. **Outlines, not boxes**: a segmenter, or SAM 2 prompted with the detector's boxes, so shelter footprints (and their areas) are right.
3. **Fine-tuning from reviews**: a training service that takes a response's fully reviewed tiles, fine-tunes from the base or previous version on a GPU, evaluates on the fixed test split, and registers the version only if it beats the last (per site and overall); versions per response, with model cards.
4. **Active learning**: reviewers shown the suggestions the model is least sure of first, so each review teaches it most.
5. **More classes**: latrines, water points, standing water, debris, roads and paths, to check against the KoboCollect observations.
6. **Sharing across responses with consent**: a base model improved with labels from many responses, each response keeping its own version; labels pooled only with the data owner's agreement.

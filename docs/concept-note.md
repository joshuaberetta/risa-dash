# RISA Dashboard: concept note

**One map for a displacement site in the first days of a response: drone imagery, field observations and analysis, printed as a product people can brief from in a minute**

Draft for the RISA consortium (HI/Atlas Logistique, MapAction, Kobo), partners and donors · October 2026

---

## Summary

In the first days after an earthquake, flood or cyclone, coordinators need to know three things about each displacement site: can we reach people, which services still work, and where do we act first. RISA (Rapid Infrastructure and Service Assessment) answers them by combining drone or satellite imagery, direct observation recorded in KoboCollect, and GIS. Today that combination is put together by hand in desktop GIS by a small number of specialists, often far from the site, and turned into PDF maps.

The **RISA Dashboard** is a web tool that does most of that assembly on one map. A team uploads the orthomosaic, connects its Kobo project and adds any analysis layers; the dashboard shows them with RISA's standard symbols, works out the key figures, and prints **RISA page 1**, the Common Operational Picture, at A3 or A4 in minutes. The data can go on to QGIS or ArcGIS for deeper analysis at any time.

It is free and open-source software (AGPL-3.0, like KoboToolbox). The consortium runs one instance; a national disaster management authority can run its own, so data stays in the country; and it runs fully offline on a Kobo-in-a-box field kit next to a local Kobo server, with no internet at all.

## What it does

- **Imagery:** drone orthomosaics of any size (uploads resume if the connection drops) and satellite scenes, shown at full resolution.
- **Field data:** KoboCollect observations from the global or EU Kobo servers, a national authority's own server, or the field kit's local server, synced every few minutes, with photos.
- **Mapping:** draw and tag shelter blocks, routes, services and hazards; measure distances and areas.
- **RISA symbology:** status always shown twice, by colour and by shape or line style, so it reads in black and white and for colour-blind readers.
- **The product:** RISA page 1 with the key message, at-a-glance figures, legend, sources and a QR code to the live map, rendered at 300 dpi and small enough to send over WhatsApp. Every version is kept.
- **Open data:** a GeoPackage for QGIS and ArcGIS Pro, and the imagery as a cloud-optimised GeoTIFF.

## Imagery analysis, with people in the loop

Counting shelters and outlining blocks on drone imagery takes a trained person hours per site. The dashboard adds **automatic segmentation**: at the press of a button it finds shelters and buildings on the orthomosaic, groups shelters into blocks and outlines the site.

Everything it finds is a **suggestion**. Reviewers accept, reject, reshape or re-tag each one, or accept in bulk above a confidence level, and draw any shelters it missed. Only what a person has accepted counts in the figures and on the printed product. This follows the principle set for AI in the Kobo-in-a-box plan: AI proposes, a person decides, and nothing is published unreviewed.

### Learning from corrections

Each of those reviews is also a label. Over a response, the people checking the suggestions build up thousands of labelled examples from that context's imagery, camps and shelter types, which is exactly what general-purpose building models lack. The dashboard **learns from them**: a reviewer presses "Learn from corrections", a new version of the detector is trained for that response, and the next detection uses it. Each version reports how often it agrees with reviews held back from training, next to the version before, so improvements are measured rather than assumed.

Over a response, the work changes from drawing shelters to checking them, and checking gets faster as the model improves. With the data owner's consent, labels from many responses can also improve a shared base model for the next emergency, in the way HOT's fAIr already does with OpenStreetMap.

## Where it stands

The MVP is running at **risa-dash.kobolabs.dev** with real drone imagery (IOM's 2012 orthomosaic of a displacement site in Port-au-Prince, CC BY 4.0) and fictional field data.

| Part | Status |
|---|---|
| Map, imagery, Kobo, drawing, measuring, page 1, exports | Working |
| Self-hosting and the offline box | Designed and partly built (Docker, offline settings); offline basemaps and fonts still to bundle |
| Imagery analysis and review | Working end to end, with a **simulated** detector (simple colour rules standing in for a model), so the review workflow can be tried now |
| Learning from corrections | Working end to end on the simulated detector; corrections are kept as training data and can be exported |
| A real segmentation model, and fine-tuning it on corrections | Planned: choose and test a model on the Venezuela and Mozambique orthomosaics, then a training service on a GPU |

## What it needs

1. **Imagery and labels to test with:** orthomosaics and Kobo data from past RISA deployments (Venezuela, Mozambique), shared under an agreement on where they are stored.
2. **Model and training work:** about 4–6 weeks of an ML engineer to choose a base model, build the training service and set its safeguards, plus GPU time, which is modest: minutes per training run.
3. **A pilot** with a national authority and the consortium, ideally alongside the Kobo-in-a-box pilot in early 2027, to test the full loop offline.
4. **Agreement on data sharing** for a shared base model: which labels may leave a response, with whose consent.

## Principles

- **People decide.** AI output is a suggestion until reviewed; counts and products use reviewed data only.
- **Open.** Free and open source; data in open formats; no lock-in to the hosted instance.
- **In-country and offline.** Run where the data is: on a national server or a field kit with no internet.
- **Measured.** Every model version reports its accuracy on held-back reviews; every detection records which version made it.
- **Observation, not people.** RISA records infrastructure and services, not personal data; imagery of displacement sites is still treated as sensitive.

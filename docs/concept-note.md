# RISA Dashboard: concept note

**One map for a displacement site in the first days of a response: drone imagery, field observations and analysis, printed as a product people can brief from in a minute**

Draft for the RISA consortium (HI/Atlas Logistique, MapAction, Kobo), partners and donors · October 2026

---

## Summary

In the first days after an earthquake, flood or cyclone, coordinators need to know three things about each displacement site: can we reach people, which services still work, and where do we act first. RISA (Rapid Infrastructure and Service Assessment) answers them by combining drone or satellite imagery, direct observation recorded in KoboCollect, and GIS. Today that combination is put together by hand in desktop GIS by a small number of specialists, often far from the site, and turned into PDF maps.

The **RISA Dashboard** is a web tool that does most of that assembly on one map. A team uploads the orthomosaic, connects its Kobo project and adds any analysis layers; the dashboard shows them with RISA's standard symbols, works out the key figures, and prints **RISA page 1**, the Common Operational Picture, at A3 or A4 in minutes. The data can go on to QGIS or ArcGIS for deeper analysis at any time.

It is free and open-source software (AGPL-3.0, like KoboToolbox). The consortium runs one instance; a national disaster management authority can run its own, so data stays in the country; and it runs fully offline on a Kobo-in-a-box field kit next to a local Kobo server, with no internet at all. Its AI runs on the kit too, on open models, so no imagery or field data goes to an outside AI company. Several kits can work together, one per site with a hub at base, as Kobo-in-a-box already does for survey data. And an AI assistant on the kit can set the dashboard up, run the analysis, prepare the map and help people when something goes wrong.

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

## Offline, with AI that runs on the kit

RISA teams often work where there is no reliable internet, and the imagery and observations of a displacement site are sensitive. So the dashboard is built to run on a **Kobo-in-a-box** field kit, alongside KoboToolbox, with nothing reaching the internet: maps, fonts, help pages and AI models are all on the kit.

It shares what the kit already has rather than bringing its own copies:
- **The kit's AI models** (open models such as Gemma 4 and gpt-oss, the same ones Kobo-in-a-box uses for translation and analysis) draft the situation brief and the key message, and check field photos: does the photo show what the observation says, is it blurred, are there faces to blur before it is shared.
- **The kit's graphics card** runs shelter detection and, overnight, learning from corrections.
- **The kit's knowledge base** holds the RISA SOP, the dashboard's own guide and sector guidance, so answers cite pages that open offline.
- **The kit's shared imagery folder**: the drone operator copies the orthomosaic there, and the dashboard picks it up, with no multi-gigabyte upload through a browser.

The same rule applies to text as to imagery: AI drafts, a person decides. The brief and key message are drafts until someone accepts them, and the model never writes a figure: every number comes from the data and is checked. On a smaller kit, or a server with no AI at all, the dashboard still works; the AI features are simply off.

## One kit or many

Kobo-in-a-box runs alone, as a network of kits, or connected to the cloud. The dashboard follows the same pattern:

1. **Standalone**: one kit does the whole response, and nothing leaves it.
2. **Networked**: a kit at each site, each with its own dashboard. When a kit comes back to base, or is connected by cable or local Wi-Fi, its work is copied to a **hub** kit, which shows the whole response, still offline. The hub shows when each site was last updated, and from which kit.
3. **Connected**: when there is a link, even briefly or over satellite, the hub sends its work to the consortium's instance or the national authority's server.

Survey data already moves this way through Kobo's own sync tool. The dashboard sends what it adds (imagery, maps drawn, reviews, products) the same way: safe to repeat, smallest and most useful files first (the printed maps, then the data, then the imagery), and only what the focal point chooses. Each site is edited on one kit at a time, so two teams never overwrite each other.

Learning works across kits too. Reviews from every site reach the hub, the hub trains a better detector for the response, and the new version goes back to the kits, with its accuracy reported for each site. Where labels may not leave a kit or a country, a further option is to share only what the model learnt, not the imagery or labels themselves.

## An assistant that can run the dashboard

Through an open standard for connecting AI assistants to tools (MCP), an AI assistant can work the dashboard the way a person does. On a kit this is the assistant Kobo-in-a-box already provides (OpenCode, running on the kit's own model); online, any compatible assistant can use it. Someone can ask, in plain language:

- **To build**: "set up Site B from today's orthomosaic and the Kobo project", and it creates the site, maps the form, syncs and frames page 1.
- **To run the analysis**: "detect shelters on the new imagery and tell me what needs checking", "what changed since the last visit?", "which Kobo points have nothing under them on the imagery?"
- **To prepare the product**: draft the key message, fill the figures, preview page 1, and render it once the person confirms.
- **For help**: "why doesn't my orthomosaic show?" It looks at what went wrong (a failed conversion, an expired Kobo connection, a form it couldn't read), explains it, and says what to do, citing the dashboard's guide. A **Help** button in the dashboard opens it on the page the person is looking at.

The assistant follows the same rules as everyone else, and some stricter ones: it can't accept or reject AI suggestions (only people review), it can't delete anything, publishing a version needs a person's confirmation, and everything it changes is logged and can be undone. As with Kobo-in-a-box's assistant, it will be tested on a set of realistic tasks with the internet cut before anyone relies on it, and changes to data are left to the larger model, which got them right in those tests.

## Where it stands

The MVP is running at **risa-dash.kobolabs.dev** with real drone imagery (IOM's 2012 orthomosaic of a displacement site in Port-au-Prince, CC BY 4.0) and fictional field data.

| Part | Status |
|---|---|
| Map, imagery, Kobo, drawing, measuring, page 1, exports | Working |
| Self-hosting and the offline box | Designed and partly built (Docker, offline settings); offline basemaps and fonts still to bundle |
| Imagery analysis and review | Working end to end, with a **simulated** detector (simple colour rules standing in for a model), so the review workflow can be tried now |
| Learning from corrections | Working end to end on the simulated detector; corrections are kept as training data and can be exported |
| A real segmentation model, and fine-tuning it on corrections | Planned: choose and test a model on the Venezuela and Mozambique orthomosaics, then a training service on a GPU |
| AI on the kit's local models (brief, key message, photo checks) | Planned; an example of the AI analysis output is shown in the dashboard today, made from the site's data without a model |
| Several kits and a hub | Planned; moving a whole response between instances as one file is designed |
| The assistant and support help | Planned, on the tools and models Kobo-in-a-box has already tested offline |

## What it needs

1. **Imagery and labels to test with:** orthomosaics and Kobo data from past RISA deployments (Venezuela, Mozambique), shared under an agreement on where they are stored.
2. **Model and training work:** about 4–6 weeks of an ML engineer to choose a base model, build the training service and set its safeguards, plus GPU time, which is modest: minutes per training run.
3. **Offline AI, the assistant and multi-kit working:** about 8–11 weeks of development after the MVP, built on Kobo-in-a-box's local models, assistant and knowledge base, and tested on its test kit with the internet cut.
4. **A pilot** with a national authority and the consortium, ideally alongside the Kobo-in-a-box pilot in early 2027, to test the full loop offline, with at least one field kit and a hub.
5. **Agreement on data sharing** for a shared base model: which labels may leave a response, with whose consent, and which AI model the online instance may use.

## Principles

- **People decide.** AI output is a suggestion until reviewed; counts and products use reviewed data only.
- **Open.** Free and open source; data in open formats; no lock-in to the hosted instance.
- **In-country and offline.** Run where the data is: on a national server or a field kit with no internet, with AI on open models on the same machine.
- **Assistants follow the rules.** An AI assistant uses the dashboard with the same limits as a person, and stricter ones: it doesn't review, delete or publish on its own.
- **Measured.** Every model version reports its accuracy on held-back reviews; every detection records which version made it.
- **Observation, not people.** RISA records infrastructure and services, not personal data; imagery of displacement sites is still treated as sensitive.

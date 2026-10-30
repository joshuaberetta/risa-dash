# RISA Dashboard: concept note

**One map for a displacement site in the first days of a response: drone imagery, field observations and analysis, printed as a product people can brief from in a minute**

Draft for the RISA consortium (HI/Atlas Logistique, MapAction, Kobo), partners and donors · October 2026

---

## Summary

In the first days after an earthquake, flood or cyclone, coordinators need to know three things about each displacement site: can we reach people, which services still work, and where do we act first. RISA (Rapid Infrastructure and Service Assessment) answers them by combining drone or satellite imagery, direct observation recorded in KoboCollect, and GIS. Today that combination is put together by hand in desktop GIS by a small number of specialists, often far from the site, and turned into PDF maps.

The **RISA Dashboard** is a web tool that does most of that assembly on one map. A team uploads the orthomosaic, connects its Kobo project and adds any analysis layers; the dashboard shows them with RISA's standard symbols, works out the key figures, and prints **RISA page 1**, the Common Operational Picture, at A3 or A4 in minutes. The data can go on to QGIS or ArcGIS for deeper analysis at any time.

It is **free and open-source software** (AGPL-3.0, like KoboToolbox), built only on open-source components and open data formats, so no one needs a licence, an account with a vendor or the consortium's permission to run it. The consortium runs one instance; a national disaster management authority can run its own, so data stays in the country; and it runs fully offline on a Kobo-in-a-box field kit next to a local Kobo server, with no internet at all. Its AI runs on the kit too, on open models, so no imagery or field data goes to an outside AI company. Several kits can work together, one per site with a hub at base, as Kobo-in-a-box already does for survey data. And an AI assistant on the kit can set the dashboard up, run the analysis, prepare the map and help people when something goes wrong.

The organisation that owns the data chooses where it lives: on the consortium's instance, on its own servers in the country, or on a kit that never connects to anything. Moving between them, or leaving, takes files in open formats, not a migration project.

## What it does

- **Imagery:** drone orthomosaics of any size (uploads resume if the connection drops) and satellite scenes, shown at full resolution.
- **Field data:** KoboCollect observations from the global or EU Kobo servers, a national authority's own server, or the field kit's local server, synced every few minutes, with photos.
- **Mapping:** draw and tag shelter blocks, routes, services and hazards; measure distances and areas.
- **RISA symbology:** status always shown twice, by colour and by shape or line style, so it reads in black and white and for colour-blind readers.
- **The product:** RISA page 1 with the key message, at-a-glance figures, legend, sources, optional locator maps (the area round the site and a country overview, as on MapAction's maps) and a QR code to the live map, rendered at 300 dpi and small enough to send over WhatsApp. Every version is kept.
- **Feedback:** a second QR code on the printed map, and a Feedback link on the online map, open a short feedback form (see below).
- **Open data:** a GeoPackage for QGIS and ArcGIS Pro, and the imagery as a cloud-optimised GeoTIFF.

## Open source, wherever it needs to run

The same software runs in four ways, chosen per response by whoever is responsible for the data:

| Way to run it | Where the data is | Internet needed | Status |
|---|---|---|---|
| **The consortium's instance** (risa-dash.kobolabs.dev) | A cloud provider's data centre in Frankfurt, in the EU | Yes | Running |
| **Self-hosted** by a national authority or an organisation | Its own server or cloud account, in the country if required | Only for its users to reach it | Built: one Docker set-up for every target |
| **Offline on a field kit** (Kobo in a box) | The kit, in the team's hands | None | Built, not yet tried on a kit; offline map labels still to bundle |
| **Federated**: several kits, a hub at base, and optionally the cloud | Each kit; then the hub; then the cloud, only what the focal point chooses | None between kits; a link only to reach the cloud | Planned |

What makes this possible:

- **Everything is open source**: the dashboard (AGPL-3.0), and everything it is built on (Django, PostgreSQL and PostGIS, GDAL, MapLibre, Typst, Chromium, KoboToolbox). The offline AI uses open-weight models. Nothing in it needs a commercial licence or a cloud service.
- **AGPL-3.0** means anyone can run, study, change and share it, and anyone who offers a changed version as a service must publish their changes too. Improvements made by one national authority or partner come back to everyone.
- **Open formats in and out**: GeoTIFF imagery, GeoPackage, GeoJSON, Shapefile and KML data, PDF products. Everything the dashboard holds can be taken to QGIS, ArcGIS or another instance.
- **No lock-in to the consortium**: a national authority can start on the hosted instance in the first days and move to its own server later, or the other way round.

## Feedback from the people who use the maps

A RISA map is only useful if it is right, and the people best placed to say what is wrong are the ones using it: camp management, cluster coordinators, the national authority's staff and the teams on the ground. So every product asks for feedback.

- **On paper:** page 1 carries a second QR code, "Scan to give feedback", next to the one for the live map. Anyone holding a printout, or looking at a copy on WhatsApp, can scan it with a phone.
- **Online:** the dashboard has a **Feedback** link on every response and site, going to the same form.
- **A Kobo form:** the feedback form is an ordinary KoboToolbox form, so it works the way the rest of RISA does, offline included. On a field kit it is the kit's own Kobo, reachable from any phone on the kit's Wi-Fi. The consortium can set one form for every response, and a national authority can use its own for a response.
- **It knows which map:** the link fills in the site, the map code and version, and whether it came from the printout or the web, so nobody has to type which map they mean and every comment can be traced to the version it is about.

The form keeps to RISA's rule of recording observations, not people: contact details are an optional question, and the answers stay in the data owner's Kobo project.

Feedback goes into the next update: a water point marked working that has stopped, a route that has reopened, a block that was missed. It also shows the consortium what users need from the product. The assistant can summarise it before each update ("what did people report since version 2?"), but a person decides what changes on the map.

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
- **Shelter detection** runs on every kit. It should be light work: a site of a few square kilometres is expected to take minutes even without a graphics card (to be measured with the real model).
- **The hub's graphics card** does the heavy work: learning from corrections, the larger assistant model, and processing drone photos into orthomosaics when that is done in the field.
- **The kit's knowledge base** holds the RISA SOP, the dashboard's own guide and sector guidance, so answers cite pages that open offline.
- **The kit's shared imagery folder**: the drone operator copies the orthomosaic there, and the dashboard picks it up, with no multi-gigabyte upload through a browser.

The same rule applies to text as to imagery: AI drafts, a person decides. The brief and key message are drafts until someone accepts them, and the model never writes a figure: every number comes from the data and is checked. On a smaller kit, or a server with no AI at all, the dashboard still works; the AI features are simply off.

### What Kobo's offline tests already show

The models are the ones Kobo-in-a-box and Kobo's paper-forms work tested in October 2026, on cloud machines with the internet cut:

| Test | Result | What it means for RISA |
|---|---|---|
| A small model (Gemma 4 E4B) on analysis and translation | Correct in Kobo's own format; 2–17 seconds per answer on an ordinary 8-core computer with no graphics card | Drafting the brief and key message works on every kit, including the cheaper ones |
| The same model reading handwriting from scanned forms (Kobo field forms) | Worked offline on the same computer. Its mistakes looked as sure as its right answers, until every reading was checked against fixed rules (such as the number of letter boxes); after that, **no wrong reading went unflagged** | Photo checks are feasible on a kit without a graphics card, run as a queue after each sync. Every AI answer is checked against the data and flagged, never trusted on the model's own confidence |
| The assistant on 30 realistic requests | The larger model (gpt-oss-120b) got **24 of 30** right, including every change to data; the smaller (Gemma 4 26B) **22 of 30**, reliable for questions but not for changes. Both refused every deletion. Too slow without a graphics card | The hub runs the larger model and makes changes; kits run the smaller one for questions and help |
| Memory | The larger model needs about 63 GB; the small model and transcription fit in 8 GB | The hub needs 128 GB of memory and a graphics card; field kits don't |

Not yet tested, and planned before the pilot: the real shelter detector on RISA orthomosaics, the dashboard's own assistant tasks, and all of it on the field hardware itself rather than cloud stand-ins.

## One kit or many

Kobo-in-a-box runs alone, as a network of kits, or connected to the cloud. The dashboard follows the same pattern:

1. **Standalone**: one kit does the whole response, and nothing leaves it.
2. **Networked**: a kit at each site, each with its own dashboard. When a kit comes back to base, or is connected by cable or local Wi-Fi, its work is copied to a **hub** kit, which shows the whole response, still offline. The hub shows when each site was last updated, and from which kit.
3. **Connected**: when there is a link, even briefly or over satellite, the hub sends its work to the consortium's instance or the national authority's server.

Survey data already moves this way through Kobo's own sync tool. The dashboard sends what it adds (imagery, maps drawn, reviews, products) the same way: safe to repeat, smallest and most useful files first (the printed maps, then the data, then the imagery), and only what the focal point chooses. Each site is edited on one kit at a time, so two teams never overwrite each other.

Learning works across kits too. Reviews from every site reach the hub, the hub trains a better detector on its graphics card for the response, and the new version goes back to the kits, with its accuracy reported for each site. Where labels may not leave a kit or a country, a further option is to share only what the model learnt, not the imagery or labels themselves.

Between emergencies, the hub need not sit in a store: it can be the national authority's own in-country server, ready to travel to a base when a response starts.

## Moving data with little or no internet

Drone imagery is large and field links are slow. An orthomosaic of one site is 1–5 GB and the raw drone photos behind it 5–30 GB; a satellite link might send 10 megabits a second when it is up, a mobile signal often under 1. So the dashboard never relies on the internet to move imagery. It uses whatever is fastest at each step: the kit's local Wi-Fi, a network cable, a USB drive in someone's pocket, and the internet only for what is small and urgent.

| From → to | How | Size and time |
|---|---|---|
| Phones → kit | KoboCollect over the kit's Wi-Fi | Each observation with its photo is a few hundred KB |
| Drone → kit | The drone's memory card or a USB drive into the kit or the drone laptop, then into the kit's shared folder over cable or Wi-Fi | An orthomosaic in 1–2 minutes over a cable or USB |
| Laptops ↔ kit | Over the kit's Wi-Fi: QGIS and the dashboard read the same imagery from the kit, with no copies | Only what is on screen is read |
| Field kit → hub | Bring the kit (or a USB drive with its export) to base and plug it in; or connect by cable when teams meet | A whole site, imagery included, in minutes |
| Hub → cloud or national server | The internet, smallest and most useful first: page 1, then the data, then lower-resolution imagery. Full imagery goes by USB drive or courier, or when a good connection appears | Page 1 (about 1.5 MB) takes seconds even on a weak mobile signal. A full orthomosaic takes about 40 minutes on a good satellite link and most of a day on mobile, so it is never sent automatically |
| Before a mission | A **content pack** (offline maps, boundaries, pre-event satellite imagery, the AI models and the software) prepared online and carried on a USB drive | 20–100 GB, copied in under an hour |
| To the people who need the map | Page 1 by WhatsApp or email; a QR code on page 1 opens the live map on the kit's Wi-Fi or online | Small enough for a weak signal |
| Back from the people who use it | The feedback QR code on page 1, or the online Feedback link, opens a Kobo form: the kit's own on its Wi-Fi, or the online one | A few KB per answer; feedback from a kit reaches the hub and the cloud with the rest of the Kobo data |

Everything that travels on a USB drive is a single file that can be checked: each part has a checksum, so a copy that breaks halfway can resume and a damaged file is caught. The files are **encrypted** with the response's key, because a lost USB drive with imagery of a displacement site is a protection risk. Importing the same file twice changes nothing.

Where phones fail or run out of battery, Kobo's paper-forms tool (Kobo field forms, which runs on the same kit) can collect site-level information on paper, such as the population figures that site management provides and the RISA form doesn't collect. These forms are scanned and read on the kit and sent to Kobo.

## Data protection and data sovereignty

RISA records infrastructure and services, not people. But imagery of a displacement site, and a map of where its water, latrines and access routes are, can still put people at risk if it reaches the wrong hands. So the dashboard is designed for the data to stay with the organisation responsible for it, in the place it must stay, and to move only when a person decides it should.

**Who controls the data.** The responding organisation or national authority that sets up a response controls its data. The field observations stay in its own Kobo project; the dashboard keeps a working copy of the points and answers it maps, and nothing else. Feedback answers go into a Kobo form the data owner chooses.

**Where it lives.** On a field kit, nothing leaves the kit unless the team copies or syncs it. On a self-hosted instance, the data is wherever that organisation runs it. On the consortium's instance, the database and files are with a cloud provider in Frankfurt (EU); imagery is delivered through the provider's content network, and the site sits behind a common security and delivery service. A response whose data must not leave a country belongs on a national server or a kit, not on the hosted instance.

**What it collects, and what it doesn't.**
- No personal accounts, and no tracking or analytics. Editing a response needs a shared edit key, stored only as a hash.
- Questions marked sensitive when a Kobo project is connected (names, phone numbers, anything about a person) are never copied to the dashboard.
- Kobo access tokens are stored encrypted and sent only to their own Kobo server. Photos are fetched through the dashboard when someone opens them, not stored in it.
- No imagery, observation or photo is sent to an outside AI company. Today's analysis is simulated; the planned models run on the kit, the hub or, for the hosted instance, a server rented from the same provider in the same region.

**Who can see it.** Viewing a site is open to anyone with its link, so the map can be shared with partners in the first hours; links aren't listed by search engines. An instance can require the edit key for viewing too. Imagery and printed pages are served at long, unguessable addresses, so a file whose address has been shared can be opened by anyone who has it; for the most sensitive responses, a national server or a kit keeps even that inside the authority's network.

**What reaches third parties online.** When the online basemaps are used, the viewer's browser loads map tiles (and, today, the map's label fonts) from the basemap provider, which sees the request and the area being viewed. Offline basemaps, or none, avoid this; a self-hosted instance can turn the online basemaps off.

**Moving data safely.** Files that travel between kits, hubs and servers are checked part by part, and are to be **encrypted** to the response's key, so a lost USB drive exposes nothing (planned with federation). Only what the focal point chooses leaves a kit. For learning across responses, labels leave a response only with the data owner's consent, and where they may not leave a kit or a country, only what the model learnt needs to.

**Keeping and deleting.** Layers, drawings and products can be deleted by anyone with the edit key, with their files; a whole response is removed by the instance's administrator. When a response closes, its full-resolution imagery is to move from the hosted instance to an offline archive held by the consortium and the national authority (planned).

These choices follow the IASC Operational Guidance on Data Responsibility in Humanitarian Action: collect only what is needed, keep control with the responsible organisation, and share deliberately. Each deployment still needs its own data-sharing agreement and, for drone imagery of sites, a protection review before anything is shared widely.

## An assistant that can run the dashboard

Through an open standard for connecting AI assistants to tools (MCP), an AI assistant can work the dashboard the way a person does. On a kit this is the assistant Kobo-in-a-box already provides (OpenCode, running on the kit's own model); online, any compatible assistant can use it. Someone can ask, in plain language:

- **To build**: "set up Site B from today's orthomosaic and the Kobo project", and it creates the site, maps the form, syncs and frames page 1.
- **To run the analysis**: "detect shelters on the new imagery and tell me what needs checking", "what changed since the last visit?", "which Kobo points have nothing under them on the imagery?", "what feedback came in on version 2?"
- **To prepare the product**: draft the key message, fill the figures, preview page 1, and render it once the person confirms.
- **For help**: "why doesn't my orthomosaic show?" It looks at what went wrong (a failed conversion, an expired Kobo connection, a form it couldn't read), explains it, and says what to do, citing the dashboard's guide. A **Help** button in the dashboard opens it on the page the person is looking at.

The assistant follows the same rules as everyone else, and some stricter ones: it can't accept or reject AI suggestions (only people review), it can't delete anything, publishing a version needs a person's confirmation, and everything it changes is logged and can be undone. As with Kobo-in-a-box's assistant, it will be tested on a set of realistic tasks with the internet cut before anyone relies on it, and changes to data are left to the larger model, which got them right in those tests.

## Where it stands

The MVP is running at **risa-dash.kobolabs.dev** with real drone imagery (IOM's 2012 orthomosaic of a displacement site in Port-au-Prince, CC BY 4.0) and fictional field data.

| Part | Status |
|---|---|
| Map, imagery, Kobo, drawing, measuring, page 1, exports | Working |
| Locator maps and the feedback QR code and link | Working; the consortium's feedback form is still to be written in Kobo |
| Self-hosting and the offline box | Built: one Docker set-up for the cloud, a national server and a kit, with offline basemaps and the user guide on the box. Not yet tried on a kit, and the map's label fonts still come from the internet |
| Encrypted transfer files and an imagery archive | Planned, with several kits and a hub |
| Imagery analysis and review | Working end to end, with a **simulated** detector (simple colour rules standing in for a model), so the review workflow can be tried now |
| Learning from corrections | Working end to end on the simulated detector; corrections are kept as training data and can be exported |
| A real segmentation model, and fine-tuning it on corrections | Planned: choose and test a model on the Venezuela and Mozambique orthomosaics, then a training service on a GPU |
| AI on the kit's local models (brief, key message, photo checks) | Planned; an example of the AI analysis output is shown in the dashboard today, made from the site's data without a model |
| Several kits and a hub | Planned; moving a whole response between instances as one file is designed |
| The assistant and support help | Planned, on the tools and models Kobo-in-a-box has already tested offline |

## Costs

Indicative, at October 2026 prices, not yet quoted. Graphics card prices in particular change quickly. The hardware follows the tiers Kobo-in-a-box has chosen, so RISA and other Kobo work can share kits.

### Running it fully locally: hardware

A **field kit** goes to each site. It runs KoboToolbox, the dashboard, shelter detection, photo checks, brief drafting and an assistant for questions and help. It runs on battery and solar.

| Item | Budget field kit | Recommended field kit |
|---|---|---|
| Computer | Mini PC, 64–96 GB memory: $800–1,200 | Mini PC with 128 GB unified memory (AMD Ryzen AI Max+ 395): $2,000–2,800 |
| Storage for imagery (4 TB solid-state drive) | $250–350 | $250–350 |
| Power: 500–1,000 Wh power station and a 100–200 W solar panel | $500–900 | $500–900 |
| Wi-Fi access point, network switch and cables | $150–300 | $150–300 |
| Rugged case with airflow | $150–300 | $150–300 |
| Two 2 TB portable SSDs for moving data | $250–350 | $250–350 |
| **Total** | **about $2,100–3,400** | **about $3,300–5,000** |

The recommended kit can run the larger assistant model and make changes through it. The budget kit's assistant is for questions and help only.

The **hub** stays at the base, on mains power or a generator. It runs everything the kits do, plus the larger assistant model and learning from corrections. If drone photos are processed into orthomosaics in the field, it does that too. It has a dedicated NVIDIA graphics card, because the training tools and the open-source drone processing software (OpenDroneMap) are reliable on one; on a mini PC's built-in graphics they are still untested.

| Item | Cost |
|---|---|
| Workstation with 128 GB memory and an NVIDIA RTX 5090 (32 GB) | $5,000–6,500 |
| Storage: two 4 TB SSDs, and an 8 TB disk for nightly backups | $700–1,000 |
| Uninterruptible power supply | $250–400 |
| Wi-Fi access point, network switch and cables | $200–400 |
| Transport case | $300–600 |
| Two 2 TB portable SSDs for moving data | $250–350 |
| **Total** | **about $6,700–9,300** |
| Optional: an A3 colour printer for page 1 | $400–800 |

On this card, the larger assistant model runs with part of it in the computer's memory. How fast that is still has to be measured. If it is too slow, a 96 GB card (RTX PRO 6000) holds the model entirely, as in the tests, and adds about $6,000–7,000.

| Deployment | Hardware | About |
|---|---|---|
| Rapid or hybrid RISA (Kobo and satellite imagery, no drone) | One budget field kit | $2,100–3,400 |
| Full RISA at one site (field, drone and GIS at one base, as in Venezuela and Mozambique) | One hub | $6,700–9,300 |
| Several sites | One hub and three budget field kits | $13,000–19,500 |

These figures leave out what RISA teams already carry: drones, phones and the satellite terminal in the ADAK. Kits and hubs are reused from one emergency to the next. Between emergencies a hub can be the national authority's in-country server, instead of a separate server bought for that.

Offline, AI has **no running cost**: no fees per request or per image. What remains is replacing hardware after four to five years, spare parts, and preparing content packs before each mission.

### The hosted option: one instance for many emergencies

The consortium's instance serves many responses a year, each used intensively by a small team for a few weeks. It is not a high-traffic service, so it stays small, and graphics cards are rented only while a response needs them.

| Part | Per month |
|---|---|
| Web service | $12 |
| Background worker (imagery conversion, printing) | $25–50 |
| Website files | $0–3 |
| Database with mapping extension and daily backups | $15–30 |
| File storage and delivery (first 250 GB stored and 1 TB delivered included) | $5 |
| **Base, always on** | **about $60–100 (about $700–1,200 a year)** |

| Per response | Cost |
|---|---|
| Imagery kept online at full resolution, about 50–150 GB | $1–3 a month while it stays online |
| A graphics-card server for detection, learning and drafting. It starts when a job needs it and is deleted afterwards: 1–3 hours a day for 2–4 weeks | about $50–300 |
| The assistant | Nothing for the consortium: people connect their own assistant to the instance |

For **about ten responses a year**, that comes to **about $1,500–4,500 a year**. The graphics-card server is from the same provider and region as the rest of the instance, running the same open models as the kits. Imagery is never sent to an outside AI company, and briefs drafted online and offline read alike.

Storage stays flat because of archiving. Once a response closes, its full-resolution imagery moves to an offline archive held by the consortium and the national authority. Products, data and lower-resolution imagery stay online.

Not counted above, and the largest running cost in practice: **people's time**. Updates, security fixes and help for responding teams need a few days a month of a developer's time. More is needed during a large response.

## What it needs

1. **Imagery and labels to test with:** orthomosaics and Kobo data from past RISA deployments (Venezuela, Mozambique), shared under an agreement on where they are stored.
2. **Model and training work:** about 4–6 weeks of an ML engineer to choose a base model, build the training service and set its safeguards, plus GPU time, which is modest: minutes per training run.
3. **Offline AI, the assistant and multi-kit working:** about 8–11 weeks of development after the MVP, built on Kobo-in-a-box's local models, assistant and knowledge base, and tested on its test kit with the internet cut.
4. **A pilot** with a national authority and the consortium, ideally alongside the Kobo-in-a-box pilot in early 2027, to test the full loop offline, with at least one field kit and a hub. That means one hub and one or two field kits, about $8,800–16,100 (see Costs), and the hosted instance at about $60–100 a month.
5. **Agreement on data sharing** for a shared base model: which labels may leave a response, with whose consent, and which AI model the online instance may use.

## Principles

- **People decide.** AI output is a suggestion until reviewed; counts and products use reviewed data only.
- **Open.** Free and open source, on open-source components only; data in open formats; no lock-in to the hosted instance or to any vendor.
- **In-country and offline.** Run where the data is: on a national server or a field kit with no internet, alone or federated with a hub, with AI on open models on the same machine.
- **The data owner decides.** The organisation responsible for a response chooses where its data lives and what leaves it; nothing is sent onward, to a partner, the cloud or an AI company, by default.
- **Assistants follow the rules.** An AI assistant uses the dashboard with the same limits as a person, and stricter ones: it doesn't review, delete or publish on its own.
- **Measured.** Every model version reports its accuracy on held-back reviews; every detection records which version made it.
- **Observation, not people.** RISA records infrastructure and services, not personal data; imagery of displacement sites is still treated as sensitive.

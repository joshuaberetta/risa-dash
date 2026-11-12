| RISA: Standard Operating Procedure. Rapid Infrastructures & Services Assessment (name pending sign-off) · deployment manual |
| :---- |

*Working draft v3 · 12 November 2026 · technical / SOP document · replaces working draft v2 (file v2.1, based on the draft of 27 July 2026)*

*A joint initiative of Kobo, MapAction and Atlas Logistique. UNDAC/OCHA endorsement: the intended model, clearance pending.*

| NOTE FOR THE WORKING GROUP This is the reference procedure for RISA deployments. It sits under the 2-page "RISA in Brief" for NEMA/NDMA heads. Following the Lyon workshop (29–30 Oct 2026), the main text stays non-technical: it explains why each step is done this way and how it most commonly fails. Field-level detail sits in the annexes, which each partner owns. The SOP is software-neutral; where software is named, it is an example, and we link to existing tutorials rather than write click-by-click guides. The aim is full replicability: any qualified team, or a national authority, can run a deployment from the SOP and annexes alone. |
| :---- |

## **Changes from v2.1**

Every change below comes from the Lyon workshop (29–30 Oct 2026), the template decisions of 12 Nov 2026, or a correction to v2.1.

| # | Section | Change | Basis |
| :---- | :---- | :---- | :---- |
| 1 | Front matter | Version line, this changelog and the open-items box added. | Housekeeping |
| 2 | Title | Name set to "Rapid Infrastructures & Services Assessment", pending sign-off. v2.1 used "Rapid Infrastructure Services Assessment". | Workshop notes |
| 3 | Front matter, §4 | Partnership stated: a joint initiative of Kobo, MapAction and Atlas; UNDAC/OCHA as endorsers; no new organisation. "Kobo specialists" dropped. | Workshop decision 1 |
| 4 | Note, all sections | Two-layer toolbox: 2-page brief for NEMA/NDMA heads, one software-neutral SOP with a non-technical main text, technical detail in annexes, links to existing tutorials instead of click-by-click guides. | Workshop decision 4 |
| 5 | §1 | Pilot scope added: displacement camps in the first days of a sudden-onset response, until a cluster or sector lead takes over around week 3. Wider scope parked as a later phase. | Workshop decision 3 |
| 6 | §1 | Platform-neutral standards: XLSForm and standard field names; open source and low-tech first; ArcGIS not required. | Workshop decision 5 |
| 7 | §1 | Language rule: English reference, AI translation, native-speaker review. | Workshop transcript |
| 8 | §2.1 | Rewritten as non-technical principles. Set-up, device and form instructions moved to Annex A and Annex F. | Workshop decision 4 |
| 9 | §2.1 | One observation per submission replaces the repeat group. | Decision 12 Nov (template) |
| 10 | §2.1 | Status scale added (Working / Partly working / Not working / Can't see), matching the map colours. No earlier form recorded status. | Decision 12 Nov (template) |
| 11 | §2.1 | Category list replaced by the template's sector and feature-type list. The v2.1 list matched neither the Mozambique nor the Venezuela form. | Correction |
| 12 | §2.1 | "Continuous GPS track" removed. The audit log records locations at form events, only when it is configured, only while a form is open, and only in the Android app. | Correction |
| 13 | §2.1 | Photos: up to three per observation (v2.1 said one; the Venezuela form allowed three). Photo protection stated. | Correction, template |
| 14 | §2.1 | Daily sync and review added, with "how this step commonly fails". | Workshop feedback on the SOP |
| 15 | §2.2 | Photogrammetry software named only as examples (v2.1 named PIX4D only). Aircraft-mounted cameras added as an untested third imagery source. | Workshop decision 5, transcript |
| 16 | §2.4 | QGIS template and re-pointable layers referenced (Annex B); ArcGIS not required. | Workshop transcript |
| 17 | §2.5 | Printed map carries a QR code to the online view (the "source of truth"), a feedback QR code, counts of features, and RISA, partner and endorser logos. Key-findings page added. | Workshop decisions 6 and 10, transcript |
| 18 | §2.6 | Static and dynamic outputs: printed map plus an online view, filterable by sector, offline-first. Feedback form (Kobo builds it, end of year). | Workshop decision 6, action plan |
| 19 | §3.2 | New roles: data / Kobo focal point, remote GIS owner, host focal point, handover focal point. | Workshop, Madagascar lesson, GIS continuity risk |
| 20 | §3.5 | Versioning, QA, validation status and exports added. | Correction (missing in v2.1) |
| 21 | §3.7 | New: accounts and ownership. No shared logins, no credentials in documents, organisation-owned projects. | Correction; Madagascar lesson |
| 22 | §3.8 | New: data protection (data-sharing agreement, sensitive locations, access, retention and deletion). | Correction (missing in v2.1) |
| 23 | §3.9 | New: handover and exit, context-agnostic. Mentoring and remote support; no ticketed helpdesk. | Workshop decisions 7 and 8 |
| 24 | §4 | Bahamas pilot, Nairobi and Durban events, Madagascar lesson and new lessons from the forms added. Future development marked as a later phase. | Workshop transcript, roadmap |
| 25 | §5 | Annex list updated with owners. New Annex F (data collection with KoboToolbox) replaces "Kobo for dummies". | Workshop action plan |

| OPEN FOR THE WORKING GROUP Still undecided. Each item is marked TBC where it appears in the text. 1\. **Name**: "Rapid Infrastructures & Services Assessment" needs sign-off; other materials use "Infrastructure Services", "Infrastructure Site" and "Infrastructure and Service". 2\. **Endorsement**: how UNDAC/OCHA endorsement and its logo are cleared (an endorser slot top left and an implementer slot bottom right were floated). 3\. **Logo**: option 10 chosen, tweaks still to make. 4\. **GIS owner**: the MapAction colleague drafting the GIS part cannot continue from December; Annexes B and C need a new named owner. 5\. **Map content**: replace the two inset maps with counts and a legend, or keep an overview map and add the counts. 6\. **Feedback form**: Kobo builds it by end of year; the link to print is TBC. 7\. **Contact point**: the RISA email address and contact form are TBC. 8\. **Handover**: who provides in-country follow-up after the deploying team leaves, and who acts as handover focal point. 9\. **Education**: the v2.1 summary table listed education, but no form or the template collects it. Add it to the template or drop it from the table. 10\. **Population**: no form collects it. Add an optional site-level household estimate, or keep using the response's default. 11\. **Data-sharing agreement**: a template text and a default retention period are TBC. 12\. **Aircraft cameras**: untested; Atlas tests before end of year. 13\. **Combining imagery sources**: when to combine satellite, aircraft and drone imagery is parked. 14\. **Template review**: whether Michael (Atlas) or the Kobo focal point reviews the detail questions before the template is marked v3. 15\. **Past coordination credit**: v2.1 credited "OCHA Canada" with assessment coordination in Mozambique and Venezuela; confirm the wording for §4. 16\. **Online view**: the sector filter is a requirement (§2.5); the RISA dashboard does not have it yet. 17\. **Not Approved records**: the RISA dashboard shows validation status but does not yet leave Not Approved records out of the map. 18\. **Annex E owner**: not assigned. |
| :---- |

**Contents**

**1. Methodology and workflow**

**2. Component SOPs**

2.1 Field data collection

2.2 Aerial imagery: drone (UAV) and aircraft cameras

2.3 Aerial imagery: satellite

2.4 GIS processing

2.5 Products and standard map content

2.6 Dissemination

**3. Deployment requirements**

**4. Lessons learned**

**5. Annexes**

# **1. Methodology and workflow**

RISA follows a standardised yet flexible methodology. It turns direct observation of infrastructure, high-resolution aerial imagery and GIS analysis into an accurate, up-to-date operational picture. It adapts to each context, but every deployment follows one common workflow. This keeps products consistent between deployments, lets field and remote teams work together, and allows rapid delivery of standard products.

## **Scope of the pilot**

The pilot covers **displacement camps and collective centres in the first days of a sudden-onset response**. RISA fills the gap until a cluster or sector lead (such as IOM or CCCM) takes over, usually around week 3. UNDAC missions typically last about three weeks, and many camps are temporary.

Other uses were discussed and deliberately parked for a later phase: other infrastructure types, environmental emergencies, preparedness, anticipatory action and early recovery. Community needs assessment stays with IOM and the clusters. RISA records what physically exists; it does not interview people.

## **Guiding principles**

Every deployment should aim to produce information that is:

* **Rapid**: useful products within the first days of an emergency.

* **Accurate**: based on direct observation and verified geospatial data.

* **Standardised**: consistent between deployments and comparable over time.

* **Operational**: focused on concrete humanitarian decisions.

* **Scalable**: drone, aircraft, satellite or hybrid depending on context.

* **Collaborative**: strengthening coordination between humanitarian actors and national authorities.

## **Standards: open, low-tech, platform-neutral**

* **XLSForm** is the data-collection standard. The RISA template (Annex A) fixes the field names and codes, so any XLSForm platform can run it: KoboToolbox, ODK Central or Ona, for example.

* **Standard field names, symbology and map elements** keep products comparable, whoever makes them.

* **Open source and low-tech first.** Every step can be done with free software and basic equipment. ArcGIS is not required. The partners keep at least one ArcGIS licence to test interoperability.

* **Links, not manuals.** Where a step uses software, the annexes link to the vendor's own tutorials. Software changes faster than this SOP.

* **Language.** This SOP is the English reference. Translations are made with AI and then reviewed by a native speaker, as Kobo already does for its own documentation. The same rule applies to form labels (Annex A).

## **The six-step workflow**

Each step is detailed in Section 2. This section gives the end-to-end sequence; the component SOPs are the authoritative procedure for each stage.

| Step | Purpose |
| :---- | :---- |
| 1. Mission preparation | Define objectives and sites with partners and authorities; adapt the RISA form and prepare imagery; confirm team, equipment, logistics, security clearances, flight authorisations and the data-sharing agreement. |
| 2. Field data collection | Georeferenced observations by direct observation, one per submission; drone flights or satellite imagery for site coverage. |
| 3. Data processing | Review and validate the observations daily; process drone imagery into a georeferenced orthomosaic; check GPS accuracy; prepare datasets for GIS. |
| 4. GIS integration | Overlay observations on imagery with standard symbology; apply the common map layout; quality control. |
| 5. Dissemination | Share the printed map, its online view and the key findings through coordination channels as fast as possible. |
| 6. Updating and handover | Repeat as the site evolves; hand over to the receiving organisation around week 3. |
| **PLACEHOLDER** Insert the RISA workflow diagram (six steps) here. |  |

# **2. Component SOPs**

Each component below is a standalone procedure, so any qualified partner can perform it. Topics appear once, here, and are referenced (not repeated) elsewhere in the document. Each component ends with the ways it most commonly fails.

## **2.1 Field data collection**

Field teams walk the site and record what they see: each water point, latrine block, health post or blocked road, with its status, location and a photo. This is the layer imagery cannot provide. A drone shows a tank; only a person standing next to it can say whether water comes out.

The RISA XLSForm template (Annex A) holds the questions, the codes and the country checklist. How to set up the platform, the accounts and the devices is in Annex F. This section covers the principles.

### **Principles**

**1. Observe, don't ask.** RISA records infrastructure and services by direct observation, not interviews. Collectors note what they can see and check. If a status can only be known by asking someone, record "Can't see" and put what you were told in the note.

**2. One observation per submission.** Each object (a water point, a latrine block, a gate) is one form, sent on its own. Site details (date, organisation, area, site) carry over from the previous form, so collectors fill them once per site. Why: a single lost or unsent form costs one observation, not a whole site visit, and each observation reaches the map as soon as it is sent.

**3. Record the status on one scale.** Every observation records whether the object works, on the same four-point scale used by the map colours:

| Status | Meaning | Map colour |
| :---- | :---- | :---- |
| Working | In use and doing its job. | Green |
| Partly working | Works with limits: damaged, restricted, some units out of order. | Amber |
| Not working | Closed, broken, destroyed or blocked. | Red |
| Can't see | The collector could not check it. | Grey ("Not assessed") |

If the status is Partly working or Not working, the form asks why. "Can't see" is an honest answer and better than a guess.

**4. Use the standard categories.** Each observation has a sector and a feature type. The template fixes the list:

| Sector | What collectors record |
| :---- | :---- |
| WASH | Water points; latrines; bathing areas; handwashing points; solid-waste points |
| Shelter | Shelters (tents, collective shelters) |
| Health | Health facilities |
| Protection | Child-friendly spaces; safe spaces for women and girls; registration, site management, entry points and help desks |
| Food | Kitchens; distribution points |
| Logistics | Storage; landing zones, including helipads; gates |
| Access | Access constraints (choke points, blocked or damaged roads and crossings) |
| Energy | Lighting; energy sources |
| Environment | Hazards (not a service, so not counted as one) |
| Commerce | Markets |
| Other | Anything else, described in the note |

Each type has a few detail questions (for example the water source, or how many beds a health post has) and a count of units at the point (taps, latrines, tents). The full list of questions and codes is in the codebook (Annex A). Education is not in the list (TBC).

**5. Take the GPS point at the object.** Stand at the water point, not across the road from it. Wait for the accuracy to settle; the form warns above 10 m. If the GPS cannot get a good fix, place the point by hand on the map and the form records that it was placed manually.

The form can also keep an audit log, which records the device's location at form events while the form is open. It is not a continuous track of the collector's route, and it only works when configured, and only in the Android app. Tell collectors their location is logged.

**6. Protect people in photos.** Take up to three photos per observation, of the object, not of people. Avoid identifiable faces, children and vulnerable people. Do not photograph inside safe spaces, health consultations or registration desks. A photo is evidence for the map, not a portrait.

**7. Sync daily, review daily.** Send forms whenever there is a connection, and at least once a day. Each evening, the data focal point reviews the day's data, marks each record's validation status, flags duplicates and poor GPS points, and gives collectors feedback before they go out again (Annex F).

**8. Freeze the form before fieldwork.** Test the form on a real device, offline, before the mission. Once data exists, never rename or delete a question or choice; add only, and change the version (Annex A).

### **How this step most commonly fails**

* **The form is changed in the field without rules.** Questions renamed or deleted mid-mission split the data into versions that no longer join. Add only, bump the version, and tell the remote team.

* **One shared login.** Everyone uses the same account, so nobody knows who collected what, and the password ends up in a document. Each collector needs their own account (Section 3.7).

* **Asking instead of looking.** Statuses come from what people say. Use "Can't see" and the note.

* **Points taken from a distance.** Points cluster around the vehicle or the camp entrance. Stand at the object and check the accuracy.

* **Forms never sent.** Finalised forms sit on a tablet for days. Sync every evening and check the count.

* **Nobody reviews the data until the end.** Errors are found when collectors have gone. Review every day.

* **Photos of people.** Faces of children or survivors end up on a printed map. Photograph the object.

* **Local edits to the template.** Each country renames codes, so maps and data cannot be compared. Follow the country checklist in Annex A.

## **2.2 Aerial imagery: drone (UAV) and aircraft cameras**

High-resolution aerial imagery is a core component. Where operationally feasible, drone mapping is preferred: it is accurate, up to date, and improves infrastructure mapping significantly over satellite imagery. Drone operations must always be coordinated with national authorities and humanitarian partners before deployment. This may include flight authorisations from civil aviation, military or other designated entities. Local authorities and camp management should also be informed to ensure transparency and community acceptance.

### **Imagery sources**

| Source | Typical resolution | Status |
| :---- | :---- | :---- |
| Drone | About 5 cm | Preferred where flying is possible. |
| Cameras on helicopters and planes | About 10 cm | Untested. Needs the pilot's agreement and georeferencing. |
| Satellite | About 30 cm | Fallback where access is constrained (Section 2.3). |

When and how to combine these sources is parked for a later phase (TBC).

### **Mission preparation**

Before deployment, the drone team should confirm that:

* all flight authorisations and security clearances are obtained;

* the Area of Interest (AOI) is defined and available satellite imagery reviewed;

* weather conditions are suitable;

* batteries are fully charged and sufficient for the mission;

* all equipment (UAV, controller, tablets, spare batteries, chargers, memory cards, GNSS where applicable) is operational and on the latest firmware.

**Give particular attention to firmware and software updates.** Outdated software can block flight authorisation or cause compatibility issues in restricted airspace.

### **Flight planning**

Plan flights to maximise image quality while minimising duration. General recommendations:

* flight type: nadir (vertical imagery);

* altitude: approximately 80 m AGL, adjusted to context and the required Ground Sampling Distance (GSD);

* image overlap: 80% where possible;

* speed: adapted to weather and image-quality requirements.

Where operationally and legally possible, also capture one or more high-altitude overview photographs from the maximum authorised altitude. They are useful for situation reports, presentations, advocacy and briefings, and complement the detailed orthomosaic.

### **Field operations and post-flight**

Before take-off, the pilot conducts a safety briefing and identifies suitable take-off and landing areas. Maintain visual line of sight (VLOS) in line with national regulations and UNDAC safety procedures. If access restrictions, security, airport proximity or technical limits prevent flying, continue with the best available recent satellite imagery (Section 2.3).

Immediately after the flight, review imagery for complete coverage and quality. Then process it into a georeferenced orthomosaic with the team's photogrammetry software. Open-source and commercial options both work; the per-software workflows are in Annex D. Orthomosaics are large, so optimise the final product to reduce file size while keeping enough resolution, and upload it to a shared cloud platform for remote GIS collaboration. *See Section 3.5 for data-management standards.*

### **Aircraft-mounted cameras (untested)**

The workshop proposed fixing two action cameras (nadir and oblique) to helicopters or planes already flying in the response, with the pilot's agreement. The images would need georeferencing, and a metadata catalogue so analysts request only the areas they need. This is untested; Atlas plans a test before the end of 2026. Do not plan a deployment around it yet.

| TO BE COMPLETED: UAV Confirm reference platform(s); add the per-software auto-mosaic workflows, the country flight-authorisation checklist and the geofencing / firmware pre-deployment checklist. The printable drone checklist stays a separate document. Owner: Atlas UAV focal point. |
| :---- |

### **How this step most commonly fails**

* Firmware or geofencing databases out of date, so the drone will not take off in restricted airspace.

* Authorisation sought too late, especially near airports.

* Orthomosaics too large to upload from the field, so the remote GIS team waits.

## **2.3 Aerial imagery: satellite**

When UAV operations are not feasible (security, flight restrictions, weather, resources, timelines), recent satellite imagery is a valuable alternative. It generally has lower resolution than a drone orthomosaic, but enables rapid mapping in the early stages and can support the first version of an assessment until better imagery is available.

### **Sources**

| Source | Use |
| :---- | :---- |
| Copernicus EMS | Rapid mapping and pre/post-event imagery for major disasters. |
| UNOSAT (UNITAR) | Satellite analysis and imagery for humanitarian emergencies. |
| Maxar Open Data | High-resolution imagery released during major disasters. |
| Planet Labs (Humanitarian) | High-frequency commercial imagery via humanitarian partnerships. |
| Sentinel-2 (Copernicus) | Free multispectral imagery for large-scale assessments. |
| USGS EarthExplorer / NASA Earthdata | Landsat / MODIS and other Earth-observation archives. |
| Google Earth Pro | Preliminary site identification and historical comparison (not a primary mapping source). |

### **Selection and integration**

Prioritise imagery that is acquired after the event, cloud-free or with minimal cloud, of the highest available resolution, and covers the full AOI. Review imagery before field deployment to support mission planning. Satellite imagery is integrated into GIS the same way as an orthomosaic and serves as the base layer. When a drone orthomosaic becomes available, it replaces the satellite layer to improve accuracy and reveal smaller infrastructure.

### **How this step most commonly fails**

* Pre-event imagery used as if it showed the site today.

* Cloud cover over the site, found only after the imagery was ordered.

## **2.4 GIS processing**

GIS processing combines the field observations and the aerial imagery into standard operational maps. The objective is a single geospatial product that accurately represents the site layout, key infrastructure and available services. Any GIS works; the reference template is a QGIS project (Annex B) whose layers are re-pointed to each deployment's data, in a fixed folder structure. ArcGIS is not required.

### **Data preparation**

* Export or connect the field data (Annex F). Use the validation status: leave out records marked Not Approved.

* Check GPS accuracy and remove duplicate observations (the daily review should already have flagged them).

* Prepare the orthomosaic or select the most recent satellite imagery.

* Ensure all datasets share a common coordinate reference system.

* Optimise aerial imagery to balance quality and file size for sharing (see Section 3.5).

### **Integration and quality control**

Overlay the validated observations on the imagery, displaying each with the standard symbols and the status colours. Visually check observations against the imagery to catch GPS errors or misplaced infrastructure. Site outlines and blocks are still mostly drawn by hand; any automated detection is a suggestion that a person checks against the ground truth. Before producing the final map, review completeness, classification consistency, positional accuracy and cartographic readability, and clarify any discrepancies with the field team.

### **Outputs and sharing**

Typical outputs: georeferenced infrastructure datasets; updated orthomosaic or satellite basemap; standard RISA maps; GIS project files; and counts by feature type and status. Archive outputs in the standard folder structure to support updates and comparison over time. Share GIS outputs with the mapping team and partners via agreed storage. Wherever possible, provide editable datasets alongside the final maps, so others can update them and use them in other systems.

| TO BE COMPLETED: GIS Confirm the standard symbology set, layer naming, the QGIS project template and folder structure; attach as Annex B. Owner: MapAction / GIS focal point (new named owner TBC). |
| :---- |

### **How this step most commonly fails**

* The GIS project lives on one person's laptop, and leaves with them.

* Field data are re-coded by hand, so map categories drift from the form.

* Maps go out before the field team has checked the odd points.

## **2.5 Products and standard map content**

The primary output is a standard operational map of the assessed site: a Common Operational Picture understood by users with different technical backgrounds. It combines recent aerial imagery, the field observations, standard symbology and operational information from site management actors.

RISA products come in two linked forms:

* **The printed map (static)**: a dated, versioned snapshot for meetings, walls and places without internet.

* **The online view (dynamic)**: the same data, kept up to date as new observations arrive, filterable by sector. It is the **source of truth**. The printed map carries a QR code that opens it. It must work offline-first: the print and its PDF stand alone, and the online view should still open on a field server or from a cached copy when there is no internet.

### **Minimum standard map content**

To ensure consistency, every RISA map must include:

| Block | Elements |
| :---- | :---- |
| Site information | Site name and location; assessment date; assessment organisation/team; version number and production date. |
| Geographic information | Orthomosaic or satellite imagery; coordinate reference system; north arrow; scale bar; administrative boundaries where relevant. |
| Infrastructure information | Standard symbols, with status shown by colour (and line style or symbol shape); counts on the map of tents, latrines, water points and other features; an infrastructure summary table by feature type and status. |
| Population information | Where available: total population, men, women, children, as context for coverage and gaps. |
| Links | A QR code to the online view; a QR code to the feedback form (Section 2.6). |
| Map furniture | Standard legend; data sources (RISA, field data, UAV/aircraft/satellite, partners); the RISA logo with partner and endorser logos (endorser logo pending clearance, TBC); disclaimer. |

Whether the two inset maps stay, or give way to counts and a legend, is open (TBC). The working leaning is to keep an overview map and add the counts.

### **Additional products**

* **Key findings (page 2)**: one page with the printed map, for decision-makers: access routes and their status, logistics conditions, the services table, and the priority gaps with who acts.

* **Infrastructure inventory**: the georeferenced field database as a structured inventory and baseline for future assessments.

* **Presentation and coordination products**: material for OSOCC briefings, EOC presentations, cluster meetings, situation reports and advocacy.

| TO BE COMPLETED: MAP LAYOUT Confirm the A4 / A3 / A0 templates with legend, counts, QR codes, summary table, population panel and logo slots; attach as Annex C. Owner: MapAction (named owner TBC). |
| :---- |

### **How this step most commonly fails**

* An old print circulates as if it were current. The date, version and QR code to the online view prevent this.

* The map shows symbols but no counts, so readers cannot see the size of a gap.

* Too many layers on one map. Use the sector filter in the online view instead.

## **2.6 Dissemination**

Disseminate products as fast as possible; their value drops by the day. Digital dissemination targets the relevant coordination platforms and stakeholders: UNDAC (OSOCC and Virtual OSOCC); ReliefWeb; humanitarian coordination mailing lists and information-sharing platforms; UNDAC communication groups (Signal, WhatsApp or agreed channels); national authorities and camp management agencies; humanitarian partners and clusters; and MapAction platforms where relevant. Share datasets and orthomosaics through the agreed storage (Section 3.5), and only with the people the data-sharing agreement allows (Section 3.8).

**Printed maps remain essential** where connectivity is limited: A4 colour maps for individuals and field teams; A3 colour maps for coordination meetings; and A0 colour maps for display in OSOCCs, EOCs and coordination rooms.

Every product carries the assessment date, version number, data sources and contact information, so users can tell the latest version. The QR code always points to the online view, so a reader holding an old print can find the current picture. When new assessments are conducted, archive previous versions to allow comparison over time (infrastructure expansion, service improvements, changes in organisation, emerging gaps).

### **Feedback**

Every map carries a second QR code to a short feedback form. Kobo builds the form by the end of 2026 (TBC). The partners also run short interviews with past users. Feedback goes to the working group, not to a helpdesk (Section 3.9).

### **How this step most commonly fails**

* Products sent to a mailing list nobody in the site reads. Ask the site management actors how they get information.

* The online link needs a login that field users do not have.

* Printing is left to the last day and there is no printer.

# **3. Deployment requirements**

A successful deployment combines operational coordination, technical capacity, field resources and appropriate equipment. The methodology is scalable, but a minimum level of capacity is essential for data quality, operational relevance and timely delivery.

## **3.1 Coordination**

Confirm before deployment: priority sites and assessment objectives; coordination with national authorities and site management actors; engagement with humanitarian partners in the area; existing information sources and datasets; the data-sharing agreement and dissemination arrangements (Section 3.8); and who will receive the products and data at handover (Section 3.9). Integrate RISA into existing mechanisms (UNDAC, OSOCC, EOC, clusters, national structures) wherever possible. Early engagement facilitates site access, authorisations and alignment with real information needs.

## **3.2 Human resources**

A deployment needs a multidisciplinary team. Roles are named, not people: one person may hold several roles in a small deployment, but every role has a named holder and a back-up.

| Role | Responsibilities |
| :---- | :---- |
| Team lead / assessment coordinator | Overall coordination; engagement with authorities and partners; assessment priorities; alignment with operational needs. |
| Data / Kobo focal point | Adapts the form from the template (Annex A); owns the data-collection project and its permissions; sets up and tests devices; trains collectors; runs the daily review and validation; manages exports and the connection to the online view; applies the data-protection rules (Annex F). |
| Field assessment team | Direct observation; GPS points; photos; one account each; daily sync. |
| Drone operator (when applicable) | UAV mission preparation; flight authorisation coordination; image acquisition; flight safety; initial imagery review. |
| GIS specialist | Data preparation and integration; map production; quality control; final products. |
| Remote GIS owner | A named person, usually remote, who owns the GIS project, the templates and the product versions for the whole deployment, so work continues when field staff rotate. |
| Remote support team | Parallel processing; map production while field work continues; troubleshooting; product review and QA. |
| Host focal point | A person in the national authority or receiving organisation who joins the work early, has access to the data and products, and takes them over at handover. |
| Handover focal point | Assesses the receiving organisation's capacity and plans the handover (Section 3.9). Who fills this role is TBC. |

## **3.3 Equipment**

**Field data collection:** Android tablets or smartphones with KoboCollect or another ODK-compatible app; spare power (power banks, vehicle chargers). An offline web form on iOS devices or laptops is the fallback (Annex F).

**Drone mapping (when applicable):** UAV system; remote controller; spare batteries; charging equipment; memory cards; tablet/mobile for flight control; appropriate software.

**GIS and processing:** a computer capable of handling geospatial datasets; GIS software (QGIS is enough); photogrammetry software for orthomosaic generation; sufficient storage; reliable backup.

## **3.4 Logistics**

Field deployments require dedicated logistical support: vehicle and driver availability; fuel planning; accommodation; communication equipment; security support; access permissions; and movement planning. Previous deployments show dedicated field assets are essential. Without them, data collection, drone operations, printing and dissemination can be significantly constrained.

## **3.5 Technical requirements and data management**

For interoperability and consistency, RISA requires the standard XLSForm template and field names; common GIS symbology; standard map layouts; and secure storage and sharing. Give particular attention to large orthomosaic datasets, which create challenges for upload and download, remote collaboration, storage and processing on lower-specification computers. Mitigations include optimised image compression, cloud-based storage, tiled imagery formats and dedicated data-sharing platforms.

Four practices keep the data usable:

* **Versioning.** The form carries a version that changes with every deployment of it. Every product carries a version and date. Previous versions are archived, not overwritten.

* **Quality assurance.** The data focal point reviews the data daily, and the GIS specialist checks points against the imagery before each product.

* **Validation status.** Each record is marked Approved, On hold or Not Approved during review. Products leave out Not Approved records. Test data is deleted or marked Not Approved before fieldwork starts.

* **Exports.** Data leaves the platform as a standard export (spreadsheet with the field names from the codebook, or GeoJSON/KML for GIS), or through the platform's API. Export and archive a full copy at the end of each day and at closure.

Technical detail for each is in Annex F.

## **3.6 Deployment scenarios**

| Configuration | Includes | When to use |
| :---- | :---- | :---- |
| Full RISA | Field assessment team + drone mapping + GIS processing + full standard products. | Highest detail and accuracy; conditions allow UAV operations. |
| Hybrid RISA | Field observations + available satellite imagery + GIS processing. | Rapid initial products when drone operations are not possible. |
| Rapid initial RISA | Existing imagery + available datasets + limited field validation. | Early operational support in the first days; updated as data become available. |

## **3.7 Accounts and ownership**

Every system RISA uses (the data-collection project, cloud storage, the online view, the GIS files) must belong to an organisation, not to a person, and must be transferable to the host at handover.

* **Organisation-owned projects.** The data-collection project is owned by an organisation or team account of the deploying partner, or by the host NDMA's own account. Never by a personal account.

* **One account per person.** Each collector has their own account, with permission only to add submissions. Reviewers get permission to view and validate. No shared logins: shared logins hide who collected what, cannot be withdrawn from one person, and end up written down.

* **No credentials in documents.** Never write passwords, API tokens or login QR codes into guides, slides, chats, screenshots or shared spreadsheets. Share access through the platform's permissions instead. A device set-up QR code can contain a password; treat it as one.

* **Server choice.** Choose the server with the host: a global or EU-hosted public server, or a national or organisational server, depending on where the data may be stored (data residency).

* **Dashboards and connections.** Anything that reads the data automatically (an online view, a dashboard, a synced export) uses a dedicated view-only account, not a person's credentials.

*Lesson from Madagascar: a Power BI dashboard was left running on the deploying team's credentials, which became awkward to unwind.* Plan ownership on day one, not at handover.

## **3.8 Data protection**

RISA collects locations of services, not personal data, but some locations and photos are sensitive.

* **Data-sharing agreement.** Agree in writing with the host authority, before collection, who owns the data, who may see it, where it is stored, how long it is kept and how it is deleted. Template text TBC.

* **Sensitive locations.** Some services are sensitive to show: safe spaces for women and girls, child-friendly spaces, and some health and protection services. Agree with the protection actors on site whether each appears on public products, only on restricted ones, or not at all.

* **Photos.** No identifiable faces, children or vulnerable people (Section 2.1). Remove any that slip through during the daily review.

* **Access lists.** Keep a list of who has access to the project, the storage and the online view. Review it at each rotation and remove people who have left.

* **Retention and deletion.** At closure, export and archive the data with the host as agreed, then delete or transfer the working copies (project, storage, devices). Default retention period TBC.

Technical detail is in Annex F.

## **3.9 Handover and exit**

RISA is designed to be handed over, usually to the cluster or sector lead or the national authority, around week 3. The handover is planned from the start and works in any context: it does not assume a particular country, organisation or software.

**Before the deployment**

* Name the receiving organisation and the host focal point.

* The handover focal point assesses the receiving organisation's capacity: people, equipment, connectivity, software, and time.

* Set up accounts and storage so they can be transferred (Section 3.7).

**During the deployment**

* Work alongside the host focal point. Produce at least one map together.

* Where possible, the deploying team stays a few extra days for in-country mentoring, producing the first maps with the receiving team.

**At handover**

* Transfer ownership of the data-collection project, the storage, the online view and the GIS project. Check the transfer worked before leaving.

* Hand over the SOP, the annexes, the current form and codebook, the latest products and the folder of archived versions.

* Remove the deploying team's personal access, keeping only what the receiving organisation asks for.

* Agree what happens to the data at closure (Section 3.8).

**After handover**

* Remote support, webinars and short videos, provided on a best-effort basis by the partners.

* A contact form (TBC), answered on a best-effort basis with no promised response times. There is no ticketed helpdesk.

* In-country follow-up has no guaranteed owner. Atlas has little drone capacity in many countries; MapAction volunteers, Flying Labs or the receiving authority may help (TBC per deployment).

### **How handover most commonly fails**

* The receiving organisation is named on the last day.

* Systems stay on the deploying team's accounts (the Madagascar lesson).

* The receiving team has never made a map before the deploying team leaves.

# **4. Lessons learned**

## **Replicability through SOPs**

The Mozambique (SADC SIMEX) and Venezuela deployments drew on the complementary expertise of several organisations: assessment coordination (TBC, see open items), survey development (Kobo), UAV operations and orthomosaic production (Atlas Logistique) and GIS and map production (MapAction). This model was effective, but future deployments should not depend on specific organisations or individuals. The partners now run RISA as a joint initiative of Kobo, MapAction and Atlas, with UNDAC/OCHA as endorsers (clearance pending), and without creating a new organisation. Standard procedures for each stage let different teams perform each component while keeping outputs consistent.

## **Data sharing**

In both deployments the assessment and GIS teams were co-located, so large datasets moved via external hard drives. Future deployments may have field and GIS teams in different places, which makes robust cloud-based (or alternative secure) data sharing essential for remote work and for large orthomosaics.

## **Venezuela: UAV and imagery**

* Early engagement with aviation authorities is critical near airports or in restricted airspace.

* Always verify that UAV firmware, flight applications and geofencing databases are updated before deployment.

* If a drone cannot be flown immediately, produce a first RISA from recent satellite imagery, then update once an orthomosaic is available.

* The orthomosaic markedly improved final products, revealing handwashing stations, latrines, child-friendly spaces and health services not reliably detectable on satellite imagery.

## **Field forms**

* **The forms diverged.** Mozambique used a repeat group, Venezuela a flat form with a sector filter, and later drafts added detail questions with inconsistent names. Data from different deployments could not be compared directly. The single template (Annex A) fixes this, with a mapping from the old codes.

* **No form recorded status.** The maps showed what existed, but not whether it worked. The template adds the status scale.

* **The deployment guide published a shared login.** A one-account-for-all set-up is quick in the field, but the password ended up in a document. Annex F replaces that guide.

## **Accounts and continuity**

* **Madagascar:** a dashboard left on the deploying team's credentials was hard to unwind (Section 3.7).

* **People move on.** The colleague drafting the GIS part of this SOP cannot continue from December. Name roles, keep project files in shared storage, and give every role a back-up (Section 3.2).

## **Next: pilot and events**

* **Bahamas pilot (Oct 2026 to Apr 2027).** A project building information-management skills in the disaster management authority (3–5 staff, monthly sessions). It is the pilot site to validate this SOP.

* **UNDAC Induction, Nairobi (15–27 Nov 2026).** A RISA inject in the simulation exercise. The aim is to make RISA a standard part of UNDAC simulation exercises.

* **GIS-AI-Drone workshop, Durban (23–27 Nov 2026).** The pilot toolbox is presented to NDMA representatives from about six countries, and their feedback collected.

## **Future development (later phase)**

RISA could extend to other contexts: Emergency Medical Team (EMT) locations, logistics hubs and distribution centres, humanitarian operational bases, critical-infrastructure assessments, debris-management sites, relocation and resettlement sites, environmental emergencies, preparedness and anticipatory action. These are parked on purpose until the camp pilot is proven. Future work should also strengthen interoperability with existing humanitarian information-management tools (such as LogIE and the Virtual OSOCC), so RISA products feed coordination mechanisms rather than duplicate them.

# **5. Annexes**

The annexes hold the reusable, technical assets referenced above. Each has an owner. Annexes link to existing tutorials and stay software-neutral where they can.

| Annex | Content | Owner | Status |
| :---- | :---- | :---- | :---- |
| **A. RISA XLSForm template** | The template, codebook, legacy-code mapping, country adaptation checklist and change rules. File: `RISA_SOP_Annex_A_XLSForm.md`. | Kobo | Draft with this SOP |
| **B. GIS standards** | Standard symbology, layer naming, QGIS project template with re-pointable layers, fixed folder structure. | MapAction (named owner TBC) | To be completed |
| **C. Standard map layout** | A4 / A3 / A0 templates with legend, counts, summary table, population panel, QR codes and logo slots. | MapAction (named owner TBC) | To be completed |
| **D. UAV** | Printable drone checklist (a separate document); country flight-authorisation checklist; firmware / geofencing pre-deployment checklist; flight-plan defaults; auto-mosaic workflows per software. | Atlas UAV | To be completed |
| **E. Deployment checklist** | Consolidated pre-deployment and handover checklist across coordination, roles, accounts, data protection, equipment and logistics (Section 3). | TBC | To be completed |
| **F. Data collection with KoboToolbox** | Accounts, set-up, testing, devices, daily QA, exports and API, media, data protection, closing and handover, troubleshooting. Replaces "Kobo for dummies". File: `RISA_SOP_Annex_Kobo.md`. | Kobo | Draft with this SOP |

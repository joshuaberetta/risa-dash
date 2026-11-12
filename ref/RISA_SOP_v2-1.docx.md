

| RISA — Standard Operating Procedure Rapid Infrastructure Services Assessment  ·  deployment manual |
| :---- |

*Working draft v2  ·  technical / SOP document  ·  based on the draft of 27 July 2026*

| NOTE FOR THE WORKING GROUP This is the technical companion to “RISA in Brief”. It is the reference procedure for deployments and is meant to be built out collaboratively — each partner completing its area of expertise (Data, UAV, GIS). The aim is full replicability: a deployment should be feasible regardless of which individuals or organisations are present, using standardised guidance alone. Sections marked “To be completed” are the areas flagged as still open (UAV, Data, GIS). Naming (“Services” vs “Site” vs “and Service”) is a placeholder pending group sign-off. |
| :---- |

**Contents**

**1\.  Methodology and workflow**

**2\.  Component SOPs**

2.1  Field data collection — KoboToolbox

2.2  Aerial imagery — drone (UAV)

2.3  Aerial imagery — satellite

2.4  GIS processing

2.5  Products and standard map content

2.6  Dissemination

**3\.  Deployment requirements**

**4\.  Lessons learned (Venezuela & Mozambique)**

**5\.  Annexes**

# **1\. Methodology and workflow**

RISA follows a standardised yet flexible methodology that turns direct infrastructure observation, high-resolution aerial imagery and GIS analysis into an accurate, up-to-date operational picture. While it adapts to different contexts, the production process follows one common workflow to ensure consistency between deployments, enable collaboration between field and remote teams, and allow rapid delivery of standardised products.

## **Guiding principles**

Every deployment should aim to produce information that is:

* **Rapid** — useful products within the first days of an emergency.

* **Accurate** — based on direct observation and verified geospatial data.

* **Standardised** — consistent between deployments and comparable over time.

* **Operational** — focused on concrete humanitarian decision-making.

* **Scalable** — drone, satellite or hybrid depending on context.

* **Collaborative** — strengthening coordination between humanitarian actors and national authorities.

## **The six-step workflow**

Each component step is detailed in Section 2\. This section gives the end-to-end sequence; the component SOPs are the authoritative procedure for each stage.

| Step | Purpose |
| :---- | :---- |
| 1\. Mission preparation | Define objectives and sites with partners and authorities; prepare the Kobo survey and imagery; confirm team, equipment, logistics, security clearances and flight authorisations. |
| 2\. Field data collection | Georeferenced Kobo observations by direct observation; UAV flights or satellite imagery for site coverage. |
| 3\. Data processing | Validate and clean Kobo data; process drone imagery into a georeferenced orthomosaic; verify GPS accuracy; prepare datasets for GIS. |
| 4\. GIS integration | Overlay observations on imagery with standardised symbology; apply the common map layout; quality control. |
| 5\. Dissemination | Distribute products digitally and in print through coordination channels as rapidly as possible. |
| 6\. Updating | Repeat as the site evolves to maintain a current Common Operational Picture. |
| **PLACEHOLDER** Insert the RISA workflow diagram (six steps) here. |  |

# **2\. Component SOPs**

Each component below is a standalone procedure so it can be performed by any qualified partner. Topics appear once, here, and are referenced (not repeated) elsewhere in the document.

## **2.1  Field data collection — KoboToolbox**

The RISA Kobo form is the primary tool for collecting standardised, georeferenced observations of infrastructure and services. It keeps all assessments on the same methodology while allowing country-specific customisation. The workflow has four stages: adapt the XLSForm, deploy to KoboToolbox, configure devices, and collect observations.

### **Adapting the RISA XLSForm**

Before each deployment, copy the standard RISA XLSForm and customise it for the country of operation. Rename it with a clear convention (e.g. RISA\_Mozambique.xlsx). In the Choices worksheet, update the administrative divisions to reflect the assessment area:

* Level 1 — first administrative level (province / state / region);

* Level 2 — second administrative level (district / county);

* Accommodation centres — list of displacement sites or camps to assess.

The naming structure uses a hierarchical coding system so Kobo automatically filters districts and camps by the selected province. Save and close the XLSForm before importing.

### **Deploying the form in KoboToolbox**

Upload the customised XLSForm to create the operational survey: import the form, create a new project, enter description / country / sector, and deploy. Once deployed, the form can be tested via the web interface, updated by uploading revised XLSForms, and shared with field teams through permissions or direct links. Complete any questionnaire changes before field deployment wherever possible.

### **Configuring KoboCollect and multiple devices**

Field data are collected with KoboCollect on Android tablets or smartphones. Configure each device to the correct KoboToolbox server, then download the deployed RISA project; the form is then available offline. Because deployments often occur with limited connectivity, observations are collected offline and synchronised once a stable connection is available.

To configure several devices quickly, use the **QR code** method: configure the first device, generate a QR code from project settings, and scan it on the other tablets to copy the server and project configuration — ensuring identical setup and saving deployment time.

### **Collecting field observations**

The form documents infrastructure and services through direct observation, not interviews. Each assessment begins with general site information (assessment date, organisation, administrative location, accommodation centre), then enters a repeat group where each observation records:

* infrastructure or service category and relevant technical attributes;

* one georeferenced GPS point (captured at the infrastructure itself);

* one photograph; and optional comments or voice notes.

The repeat structure allows an unlimited number of observations while maintaining a continuous GPS track.

### **Standard data collection principles**

* Record through direct visual assessment wherever possible.

* Capture the GPS point at the infrastructure, not from a distance.

* Take clear photographs while respecting protection principles (avoid identifiable faces and vulnerable individuals).

* Complete all relevant fields before creating a new observation.

* Add comments where context will help GIS processing.

* Synchronise with KoboToolbox as soon as connectivity allows.

**Current standard categories:** shelter; water supply and distribution; sanitation (latrines, bathing); solid waste; health facilities; child-friendly and protection spaces; distribution points; energy; storage; access constraints and transport bottlenecks; site management information — plus georeferenced photos, GPS, comments and voice notes.

| TO BE COMPLETED — KOBO Confirm the definitive category list and technical attributes per category; attach the current standard XLSForm as an annex (see Annex A). Owner: Kobo focal point / WG 1. |
| :---- |

## **2.2  Aerial imagery — drone (UAV)**

High-resolution aerial imagery is a core component. Where operationally feasible, drone mapping is preferred: it is accurate, up to date, and significantly improves infrastructure mapping over satellite imagery. Drone operations must always be coordinated with national authorities and humanitarian partners before deployment — this may include flight authorisations from civil aviation, military or other designated entities. Local authorities and camp management should also be informed to ensure transparency and community acceptance.

### **Mission preparation**

Before deployment, the drone team should confirm that:

* all flight authorisations and security clearances are obtained;

* the Area of Interest (AOI) is defined and available satellite imagery reviewed;

* weather conditions are suitable;

* batteries are fully charged and sufficient for the mission;

* all equipment (UAV, controller, tablets, spare batteries, chargers, memory cards, GNSS where applicable) is operational and on the latest firmware.

**Give particular attention to firmware and software updates —** outdated software can block flight authorisation or cause compatibility issues in restricted airspace.

### **Flight planning**

Plan flights to maximise image quality while minimising duration. General recommendations:

* flight type: nadir (vertical imagery);

* altitude: approximately 80 m AGL, adjusted to context and required Ground Sampling Distance (GSD);

* image overlap: 80% where possible;

* speed: adapted to weather and image-quality requirements.

Where operationally and legally possible, also capture one or more high-altitude overview photographs from the maximum authorised altitude — useful for situation reports, presentations, advocacy and briefings, complementing the detailed orthomosaic.

### **Field operations and post-flight**

Before take-off, the pilot conducts a safety briefing and identifies suitable take-off / landing areas. Maintain visual line of sight (VLOS) in line with national regulations and UNDAC safety procedures. If access restrictions, security, airport proximity or technical limits prevent flying, continue with the best available recent satellite imagery (Section 2.3).

Immediately after the flight, review imagery for complete coverage and quality, then process into a georeferenced orthomosaic using the selected photogrammetry software (e.g. PIX4D / Pixpro). Because orthomosaics are large, optimise the final product to reduce file size while keeping sufficient resolution, and upload to a shared cloud platform for remote GIS collaboration. *See Section 3.5 for data-management standards.*

| TO BE COMPLETED — UAV Confirm reference platform(s) and photogrammetry software; add a country flight-authorisation checklist and the geofencing / firmware pre-deployment checklist. Owner: Atlas UAV focal point. |
| :---- |

## **2.3  Aerial imagery — satellite**

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

Prioritise imagery that is acquired after the event, cloud-free or with minimal cloud, of the highest available resolution, and covers the full AOI. Review imagery before field deployment to support mission planning. Satellite imagery is integrated into GIS the same way as an orthomosaic and serves as the base layer; when a drone orthomosaic becomes available it should replace the satellite layer to improve accuracy and reveal smaller infrastructure.

## **2.4  GIS processing**

GIS processing combines the Kobo observations and the aerial imagery into standardised operational maps. The objective is a single geospatial product that accurately represents the site layout, key infrastructure and available services.

### **Data preparation**

* Download the Kobo dataset; review and clean attributes.

* Check GPS accuracy and remove duplicate observations.

* Prepare the orthomosaic or select the most recent satellite imagery.

* Ensure all datasets share a common coordinate reference system.

* Optimise aerial imagery to balance quality and file size for sharing (see Section 3.5).

### **Integration and quality control**

Import validated Kobo observations and overlay them on the imagery, displaying each with standardised symbols and categories. Visually verify individual observations against the imagery to catch GPS inaccuracies or misplaced infrastructure. Before producing the final map, run a quality-control review of completeness, classification consistency, positional accuracy and cartographic readability; clarify any discrepancies with the field team.

### **Outputs and sharing**

Typical outputs: georeferenced infrastructure datasets; updated orthomosaic / satellite basemap; standardised RISA maps; GIS project files; and summary statistics by category. Archive outputs in a standardised folder structure to support updates and longitudinal comparison. Share GIS outputs with the mapping team and partners via agreed cloud storage; wherever possible, provide editable datasets alongside the final maps to enable future updates and integration with other systems.

| TO BE COMPLETED — GIS Confirm the standard symbology set, layer naming conventions, project template and folder structure; attach as Annex B. Owner: MapAction / GIS focal point. |
| :---- |

## **2.5  Products and standard map content**

The primary output is a standardised operational map representing the physical organisation of the assessed site — a Common Operational Picture understood by users with different technical backgrounds. It combines recent aerial imagery, georeferenced Kobo observations, standardised symbology and operational information from site management actors.

### **Minimum standard map content**

To ensure consistency, every RISA map must include:

| Block | Elements |
| :---- | :---- |
| Site information | Site name and location; assessment date; assessment organisation/team; version number and production date. |
| Geographic information | Orthomosaic or satellite imagery; coordinate reference system; north arrow; scale bar; administrative boundaries where relevant. |
| Infrastructure information | Standardised symbols and categories; location and distribution of observed services; infrastructure summary table (shelters, water points, latrines, bathing, health, education, protection/community, logistics, other). |
| Population information | Where available: total population, men, women, children — as context for coverage and gaps. |
| Map furniture | Standard legend; data sources (RISA, Kobo, UAV/Satellite, partners); logos and disclaimer. |

### **Additional products**

* **Infrastructure inventory —** the georeferenced Kobo database as a structured inventory and baseline for future assessments.

* **Situation / map brief —** a short document summarising objectives, date, location, methodology, key findings and priority observations for decision-makers who do not need the full GIS dataset.

* **Presentation & coordination products —** material for OSOCC briefings, EOC presentations, cluster meetings, situation reports and advocacy.

## **2.6  Dissemination**

Products should be disseminated as rapidly as possible to maximise operational value. Digital dissemination targets relevant coordination platforms and stakeholders: UNDAC (OSOCC and Virtual OSOCC); ReliefWeb; humanitarian coordination mailing lists and information-sharing platforms; UNDAC communication groups (Signal, WhatsApp or agreed channels); national authorities and camp management agencies; humanitarian partners and clusters; and MapAction platforms where relevant. Share datasets and orthomosaics via secure cloud platforms to enable field/remote collaboration.

**Printed maps remain essential** where connectivity is limited: A4 colour maps for individuals and field teams; A3 colour maps for coordination meetings; and A0 colour maps for display in OSOCCs, EOCs and coordination rooms.

Every product must carry the assessment date, version number, data sources and contact information so users can identify the most recent version. When new assessments are conducted, archive previous versions to allow comparison over time (infrastructure expansion, service improvements, changes in organisation, emerging gaps).

# **3\. Deployment requirements**

A successful deployment combines operational coordination, technical capacity, field resources and appropriate equipment. The methodology is scalable, but a minimum level of capacity is essential to ensure data quality, operational relevance and timely delivery.

## **3.1  Coordination**

Confirm before deployment: priority sites and assessment objectives; coordination with national authorities and site management actors; engagement with humanitarian partners in the area; existing information sources and datasets; and data-sharing and dissemination arrangements. Integrate RISA into existing mechanisms (UNDAC, OSOCC, EOC, clusters, national structures) wherever possible. Early engagement facilitates site access, authorisations and alignment with real information needs.

## **3.2  Human resources**

A deployment requires a multidisciplinary team. Typical roles:

| Role | Responsibilities |
| :---- | :---- |
| Team lead / assessment coordinator | Overall coordination; engagement with authorities and partners; assessment priorities; alignment with operational needs. |
| Field assessment team | Kobo data collection; infrastructure identification; GPS observations; photographic documentation; field validation. |
| Drone operator (when applicable) | UAV mission preparation; flight authorisation coordination; image acquisition; flight safety; initial imagery review. |
| GIS specialist | Data cleaning and validation; GIS integration; map production; quality control; final products. |
| Remote support team | Parallel data processing; map production while field activities continue; troubleshooting; product review and QA. |

## **3.3  Equipment**

**Field data collection:** Android tablets or smartphones with KoboCollect; spare power.

**Drone mapping (when applicable):** UAV system; remote controller; spare batteries; charging equipment; memory cards; tablet/mobile for flight control; appropriate software.

**GIS and processing:** a computer capable of handling geospatial datasets; GIS software; photogrammetry software for orthomosaic generation; sufficient storage; reliable backup.

## **3.4  Logistics**

Field deployments require dedicated logistical support: vehicle and driver availability; fuel planning; accommodation; communication equipment; security support; access permissions; and movement planning. Previous deployments show dedicated field assets are essential — without them, data collection, drone operations, printing and dissemination can be significantly constrained.

## **3.5  Technical requirements and data management**

For interoperability and consistency, RISA requires standardised Kobo forms; agreed data structures and naming conventions; common GIS symbology; standardised map layouts; and secure storage and sharing mechanisms. Give particular attention to large orthomosaic datasets, which create challenges for upload/download, remote collaboration, storage and processing on lower-specification computers. Mitigations include optimised image compression, cloud-based storage, tiled imagery formats and dedicated data-sharing platforms.

## **3.6  Deployment scenarios**

| Configuration | Includes | When to use |
| :---- | :---- | :---- |
| Full RISA | Field assessment team \+ drone mapping \+ GIS processing \+ full standardised products. | Highest detail and accuracy; conditions allow UAV operations. |
| Hybrid RISA | Field Kobo observations \+ available satellite imagery \+ GIS processing. | Rapid initial products when drone operations are not possible. |
| Rapid initial RISA | Existing imagery \+ available datasets \+ limited field validation. | Early operational support in the first days; updated as data become available. |

# **4\. Lessons learned (Venezuela & Mozambique)**

## **Replicability through SOPs**

The Mozambique and Venezuela deployments benefited from the complementary expertise of several organisations — OCHA Canada (assessment coordination), Kobo specialists (survey development), Atlas Logistique (UAV operations and orthomosaic production) and MapAction (GIS and map production). This collaborative model was highly effective, but future deployments should not depend on specific organisations or individuals. Standardised SOPs for each stage — Kobo development and deployment, drone operations or satellite acquisition, orthomosaic processing, GIS integration, map production and dissemination — allow different teams to perform each component while maintaining consistent, standardised outputs.

## **Data sharing**

In both deployments the assessment and GIS teams were co-located, so large datasets moved via external hard drives. Future deployments may have field and GIS teams in different locations, which makes robust cloud-based (or alternative secure) data-sharing solutions essential for remote collaboration and the exchange of large orthomosaics.

## **Venezuela — UAV and imagery**

* Early engagement with aviation authorities is critical near airports or in restricted airspace.

* Always verify that UAV firmware, flight applications and geofencing databases are updated before deployment.

* If a drone cannot be flown immediately, produce a first RISA from recent satellite imagery, then update once an orthomosaic is available.

* The orthomosaic markedly improved final products — revealing handwashing stations, latrines, child-friendly spaces and health services not reliably detectable on satellite imagery.

## **Future development**

Although developed for displacement sites, RISA can extend to other operational contexts: Emergency Medical Team (EMT) locations, logistics hubs and distribution centres, humanitarian operational bases, critical-infrastructure assessments, debris-management sites, relocation and resettlement sites, and operational response hotspots. Future work should strengthen interoperability with existing humanitarian information-management systems so RISA products integrate into coordination mechanisms, operational platforms and decision-support processes.

# **5\. Annexes**

The annexes hold the reusable standard assets referenced above. To be attached as the group completes each component:

| ANNEX A — STANDARD RISA XLSFORM Current master Kobo form \+ category / attribute dictionary. Owner: WG 1 (Kobo). |
| :---- |
| **ANNEX B — GIS STANDARDS** Standard symbology, layer naming, project template and folder structure. Owner: GIS focal point. |
| **ANNEX C — STANDARD MAP LAYOUT** A4 / A3 / A0 templates with legend, summary table and population panel. |
| **ANNEX D — UAV CHECKLISTS** Country flight-authorisation checklist; firmware / geofencing pre-deployment checklist; flight-plan defaults. Owner: Atlas UAV. |
| **ANNEX E — DEPLOYMENT CHECKLIST** Consolidated pre-deployment checklist across coordination, HR, equipment and logistics (Section 3). |


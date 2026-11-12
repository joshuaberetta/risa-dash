| RISA SOP: Annex A. The RISA XLSForm template |
| :---- |

*Working draft v3 · 12 November 2026 · annex to the RISA SOP v3 · owner: Kobo*

| NOTE FOR THE WORKING GROUP This annex describes the RISA field form: what it is, why it is built this way, how a country adapts it, and the rules for changing it. It does not repeat the data dictionary. The full list of questions, codes and settings is in the codebook, generated from the same source as the form. How to run the form on KoboToolbox (accounts, devices, daily review, exports) is in Annex F. Replaces the "Adapting the RISA XLSForm" part of SOP v2.1 §2.1 and the Excel part of "Kobo for dummies". |
| :---- |

# **1. The template package**

| File | What it is |
| :---- | :---- |
| `templates/xlsform/RISA_template_<version>.xlsx` | The form. Sheets: `survey`, `choices`, `settings`, plus `codebook` and `adapt` (the country checklist). Current draft: version 2026111201. |
| `templates/xlsform/codebook.md` | The data dictionary: every question path, type, list, label, logic and constraint, every code list, and the settings. Read this before any analysis. |
| `templates/xlsform/legacy_codes.csv` | The mapping from the old codes (the 47 of the Mozambique and Venezuela forms, the 18 of Michael's draft) to the new sector and feature type, with a detail answer where one applies. |
| `templates/xlsform/spec.py` and `scripts/build_xlsform.py` | The single source of truth and the script that builds the three files above. Change the spec, not the generated files. |

The form is plain XLSForm. It runs on KoboToolbox, ODK Central, Ona and any other XLSForm platform. Only the dashboard connection in Section 5 is specific to the RISA dashboard.

Review status: whether Michael (Atlas) or the Kobo focal point reviews the detail questions before the template is marked v3 is open (TBC).

# **2. Design choices**

Each choice below answers a problem found in the earlier forms.

### **One observation per submission**

One form is one object at one point: a water point, a latrine block, a gate. There is no repeat group. The site details in the `visit` group (date, organisation, admin areas, site) carry over from the last submission, so collectors fill them once per site.

*Why:* in a repeat, nothing reaches the server until the whole visit is finalised and sent. One lost tablet loses the site. With one observation per submission, each object syncs on its own and reaches the map as one feature. This follows the Venezuela pattern.

### **The status scale**

Every observation answers "Is it working?" (`obs/status`):

| Code | Label | Map |
| :---- | :---- | :---- |
| `ok` | Working | green, filled |
| `partial` | Partly working | amber, half |
| `no` | Not working | red, crossed |
| `unknown` | Can't see | grey, outline ("Not assessed") |

The hint is "Observe, don't ask". For an access constraint or a hazard, Working means passable, Partly working restricted and Not working blocked. When the answer is Partly working or Not working, `obs/status_reason` asks what is wrong.

*Why:* none of the earlier forms recorded status, though the maps' colours depend on it.

### **Sector, then feature type**

The collector picks a sector (`obs/sector`), then a feature type filtered by sector (`obs/feature_type`). The feature-type codes are the RISA dashboard's map-symbol codes, so a code means the same symbol everywhere.

| Sector code | Feature type codes |
| :---- | :---- |
| `wash` | `water`, `latrine`, `bathing`, `hand`, `waste` |
| `shelter` | `shelter` |
| `health` | `health` |
| `protection` | `cfs`, `safe_space` (women and girls, other groups), `registration` (site management, registration, reception) |
| `food` | `kitchen`, `dist` |
| `logistics` | `storage`, `landing` (incl. helipad), `gate` |
| `access` | `choke` (access constraint) |
| `energy` | `lighting`, `energy` |
| `environment` | `hazard` (not a service; left out of service counts) |
| `commerce` | `market` |
| `other` | `other`, with a text question |

*Why:* the v2.1 SOP category list matched neither form. The Venezuela form tagged shelters as health and access constraints as storage. A short list of map types, with detail held in separate questions, keeps the map consistent.

### **Feature ID**

`obs/feature_id` is a short label such as WP-03. It is the label on the map, and lets a later visit refer to the same object.

### **Detail questions**

Each feature type has a few detail questions, shown only for that type. Examples: latrine permanence, features and accessibility; water source, storage, volume, distribution and tap count; shelter type and capacity; health level of care, manager, cost, services and beds; storage type and capacity in m³; access constraint type, road hotspot, crossing and last-mile services; lighting type and power; energy source and uses. Each "other" answer has its own `<question>_other` text question. Full list: codebook, "Questions".

*Why:* Michael's drafts added these questions, but with random list names (`bp0fd95`), typos, and logic that could never show. The template keeps the content and fixes the names and logic.

### **Counts**

`obs/count` is the number of units at this point: taps on a stand, latrines in a block, tents in a cluster. The map and its summary table add them up.

*Why:* the workshop asked for counts on the map. One point can stand for many units.

### **Location**

`obs/location` is a geopoint. The form captures automatically at 5 m accuracy and warns above 10 m. `obs/location_method` records whether the point was taken by GPS at the object or placed by hand on the map. `obs/location_accuracy` keeps the accuracy in metres.

The `audit` metadata logs each question opened and changed, with the device location every 10 seconds while a form is open. It works only in KoboCollect / ODK Collect, not in web forms. It is not a continuous GPS track between forms.

### **Photos**

`obs/photo`, then optional `obs/photo_2` and `obs/photo_3`, each shown once the one before is taken. Images are capped at 1600 pixels on the long side to keep uploads small. The hint reminds collectors to avoid faces.

### **The note**

`note` (text) and `note_audio` (voice) sit outside any group, at the top level. The dashboard's key-findings page and the brief read `note` directly.

### **Names in exports**

Calculations (`visit/level_1_label`, `visit/level_2_label`, `visit/site_label`) store the names as well as the codes, so exports are readable without the choices sheet.

### **Settings**

| Setting | Value |
| :---- | :---- |
| `form_title` | RISA site observation |
| `form_id` | `risa_obs` (a country may append its ISO3 code: `risa_obs_bhs`) |
| `version` | yyyymmddNN, e.g. 2026111201 |
| `instance_name` | site, feature type, feature ID and time, so each record has a readable name |
| `style` | `pages theme-grid` |
| `default_language` | English (en) |

# **3. Country adaptation checklist**

Do this before every deployment. The `adapt` sheet in the template holds the same list. Work on a copy named for the country, e.g. `RISA_BHS_2026112001.xlsx`.

| # | Topic | Step |
| :---- | :---- | :---- |
| 1 | Settings | Keep `form_id` as `risa_obs`, or append the ISO3 code (`risa_obs_bhs`). Add the country to `form_title`. Set `version` to today's date and 01. |
| 2 | Admin areas | Replace the placeholder `level_1` and `level_2` lists with the country's COD-AB (Common Operational Datasets, administrative boundaries) from HDX: the P-code as `name`, the admin name as label. Each `level_2` row carries its parent P-code in the `level_1` column. Delete every placeholder XX row. Relabel the questions if the country uses other terms (island, parish). |
| 3 | Site list | Replace the placeholder `site` list with the camps and collective centres to assess. Use the CCCM or DTM site code if one exists; otherwise build one from the district P-code. Each site row carries its district P-code in the `level_2` column. Keep the `other` row last. |
| 4 | Organisations | Add the agencies working on site to the `org` list. Keep the seven existing codes. |
| 5 | Feature types | Do not rename a feature-type code. To add a type, add a row with its sector and tell the dashboard team, so it gets a map symbol. A type the country does not need can be deleted before the first deployment, or left in. |
| 6 | Labels and languages | English is the reference. To add a language, add `label::<Language> (xx)`, `hint::<Language> (xx)` and `constraint_message::<Language> (xx)` columns on both `survey` and `choices`. Every label column must carry a language suffix. Translate with AI, then have a native speaker review. Set `default_language` to the language most collectors read. |
| 7 | Extra questions | A country may add detail questions inside the `obs` group, shown only for the relevant feature type, after the existing ones. Each question with an "other" choice gets its own `_other` text question. |
| 8 | Server | Choose the server with the host authority, for data residency: the global or EU KoboToolbox server, or a national or organisational server (Annex F §2). |
| 9 | Check | Convert the form (upload to a test project, or kobo-mcp `convert_xlsform`). Fill one observation of each type you use on a real device, offline, then look at the data. Testing before fieldwork: Annex F §4. |

Links:

* Common Operational Datasets (COD-AB) on HDX: https://data.humdata.org/ (search "<country> subnational administrative boundaries")

* XLSForm reference: https://xlsform.org/en/

* Choice filters in XLSForm (KoboToolbox): https://support.kobotoolbox.org/choice_filters_xls.html

* Adding translations in XLSForm (KoboToolbox): https://support.kobotoolbox.org/language_xls.html

* Form settings in XLSForm (KoboToolbox): https://support.kobotoolbox.org/form_settings_xls.html

# **4. Change rules**

These rules apply from the moment the first real observation exists.

1. **Never rename or delete a question name or a choice code.** The data already collected uses them. A rename splits one column into two; a delete orphans the old answers.

2. **Add only.** New questions, new choices and new languages are safe. To stop offering a choice, leave it in the list and agree with the template owner how to hide it.

3. **Bump the version** with every change you deploy: yyyymmddNN, e.g. 2026111201, then 2026111202 for a second change the same day.

4. **Keep the contract paths.** The paths marked `contract` in the codebook (`visit/...`, `obs/sector`, `obs/feature_type`, `obs/feature_id`, `obs/status`, `obs/status_reason`, `obs/count`, `obs/location`, `obs/location_method`, the photos, `note`, `note_audio`) are read by the dashboard with no mapping step. Do not move them to another group.

5. **Naming.** snake_case ASCII, 32 characters or fewer, unique across the form. `other` is the only code for "other".

6. **Record the change.** Note what changed and why in the deployment log, and tell the remote GIS owner. How to deploy a change mid-mission: Annex F §7.

7. **Changes to the global template** go through the template owner (Kobo), so every country can pick them up.

# **5. How the form feeds the RISA dashboard**

The RISA dashboard reads observations straight from KoboToolbox. When a project is connected, a RISA form maps itself: if the `form_id` starts with `risa_obs`, or the form has `obs/feature_type` and `obs/status`, the dashboard takes the location, type, status and label from the contract paths, with no mapping step. Any other form gets the "Map form to RISA" dialog, where someone picks the questions by hand. (The automatic mapping is being added to the dashboard with this template, November 2026. Until it is released, check the mapping in the dialog.)

| Form path | Dashboard |
| :---- | :---- |
| `obs/location` | map position |
| `obs/feature_type` | map symbol |
| `obs/status` | map colour and the page 1 figures |
| `obs/feature_id` | map label |
| `obs/count` | counts on the map and page 1 |
| `obs/status_reason`, `note` | the popup and the key-findings page |
| `obs/location_method` | data-quality checks |
| `end` | when the observation was made |

The connection uses a token from a dedicated view-only account (Annex F §10). Exports for QGIS or other tools use the same names, so the codebook is the reference for any analysis.

# **6. Legacy code mapping**

`templates/xlsform/legacy_codes.csv` converts data from the earlier forms to the template. Each row gives the source (`mozambique_venezuela` or `michael_draft`), the old code and label, the new `sector` and `feature_type`, and, where the old code carried a detail, the detail question and answer. For example:

| Old code | New sector / type | Detail |
| :---- | :---- | :---- |
| `wash_latrine_emergency` | `wash` / `latrine` | `obs/permanence` = `emergency` |
| `wash_water_tap_stand` | `wash` / `water` | `obs/water_distribution` = `tap_stand` |
| `prot_safe_space_women` | `protection` / `safe_space` | `obs/space_users` = `women_girls` |
| `shlt_shelter_collective` | `shelter` / `shelter` | `obs/shelter_type` = `collective` |
| `wash_lighting_solar` | `energy` / `lighting` | `obs/lighting_power` = `solar` |
| `access_constraint` | `access` / `choke` | none |

Some old codes carry less detail than the new questions (for example "improved water source" does not say which). The `note` column says so. The codebook also lists how each question in Michael's draft maps to a template question.

The old forms recorded no status. Converted records have status `unknown` (Can't see) unless someone re-checks them.

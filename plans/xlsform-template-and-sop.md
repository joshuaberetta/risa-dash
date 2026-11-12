# RISA XLSForm template, SOP v3 and Brief v3

Status: plan, not started (12/11/2026). Sources in `ref/`: SOP v2.1, RISA in Brief v2.1, the Lyon workshop notes (29–30/10/2026), the Mozambique and Venezuela deployment forms, Michael's drafts (`Risa 2.0.xlsx`, `RISA_XXX.xlsx`, the later of the two) and "Kobo for dummies".

Deadline: SOP and annexes are due 14/11 (workshop action list). Kobo owns the XLSForm template and the data-collection annex.

## Decisions (12/11/2026)

| # | Decision |
|---|---|
| 1 | **One observation per submission** (the Venezuela pattern). Site details carry over with `${last-saved#…}`. Each observation syncs on its own and reaches the dashboard as one feature. No repeat. |
| 2 | **Feature codes are the dashboard's RISA type codes** (`symbology/risa.json` `types`), with new types added where needed. A mapping table converts the 47 Mozambique/Venezuela codes and Michael's 18. |
| 3 | **SOP v3 and Brief v3 in Markdown only**, edited from the `ref/` files. |
| 4 | **English only.** Countries add their own `label::<Language> (xx)` columns. Translation follows the workshop rule (English reference, AI translation, native-speaker review). |

## Problems the plan fixes

- **No form records status.** The dashboard, the site and the map colours use working, partly working, not working and not assessed, but none of the four forms ask for it.
- **The dashboard has no RISA preset.** It guesses the location, type, status and label questions from names and choices (`backend/risa/kobo.py` `guess_field_map`). It cannot read repeats. Page 2 reads `properties["note"]`, so a comment inside a group never reaches it.
- **The forms have diverged.** Mozambique uses a repeat, Venezuela a flat group with a sector filter, and Michael's drafts add detail questions with random list names (`bp0fd95`), typos and broken logic (`how_many` can never show). Venezuela tags shelters as health and access constraints as storage.
- **"Kobo for dummies" publishes a shared login.** Change that password now. The new annex replaces the document.
- **The SOP and brief are behind the workshop.** They lack the partnership model, the two-layer toolbox, handover, the QR code to the online view, the feedback form and the pilot scope. The SOP's "continuous GPS track" claim is wrong, and its category list matches neither form.

## Data contract (fixed 12/11/2026, shared by every phase)

Paths are the submission keys Kobo sends (`group/name`).

| Path | Type | Notes |
|---|---|---|
| `start`, `end`, `today`, `username`, `deviceid`, `start_geopoint`, `audit` | metadata | the dashboard reads `end` as `observed_at` |
| `visit/date` | date | |
| `visit/org`, `visit/org_other` | select_one `org` | |
| `visit/level_1`, `visit/level_2` | select_one, P-codes | |
| `visit/site`, `visit/site_other` | select_one `site` | camp or collective centre |
| `obs/sector` | select_one `sector` | |
| `obs/feature_type` | select_one `feature_type`, filtered by `sector` | choice names are RISA type codes |
| `obs/feature_id` | text | map label, e.g. WP-03 |
| `obs/status` | select_one `status`: `ok` `partial` `no` `unknown` | Working, Partly working, Not working, Can't see |
| `obs/status_reason` | text | shown when status is partial or no |
| `obs/count` | integer | units at this point |
| `obs/<detail>` | various | relevant on `feature_type` |
| `obs/location` | geopoint | |
| `obs/location_method` | select_one `gps` `manual` | |
| `obs/photo`, `obs/photo_2`, `obs/photo_3` | image | |
| `note` | text, **ungrouped** | page 2 and the brief read `properties["note"]` |
| `note_audio` | audio, ungrouped | |

**`sector` → `feature_type` codes.** `*` marks a new RISA type for `symbology/risa.json`.

| Sector | Feature types |
|---|---|
| `wash` | `water`, `latrine`, `bathing`*, `hand`, `waste`* |
| `shelter` | `shelter` |
| `health` | `health` |
| `protection` | `cfs`, `safe_space`* (women and girls), `registration` (site management, entry point, help desk) |
| `food` | `kitchen`, `dist` |
| `logistics` | `storage`, `landing` (incl. helipad), `gate` |
| `access` | `choke` (access constraint) |
| `energy` | `lighting`*, `energy`* |
| `environment` | `hazard`* |
| `commerce` | `market`* |
| `other` | `other` |

`hazard` is not a service; it is excluded from service counts in the same way as `flood` and `debris`. Settings: `form_id` `risa_obs` (countries may append `_<iso3>`).

## Phase 1: template (`templates/xlsform/`)

One spec file is the source of truth. `scripts/build_xlsform.py` produces:

- `RISA_template_<version>.xlsx`, with sheets `survey`, `choices`, `settings`, `codebook` and `adapt` (country checklist). Check that Kobo accepts the extra sheets; if it doesn't, ship them as a separate dictionary file.
- `codebook.md`, the data dictionary for SOP Annex A.
- `legacy_codes.csv`, mapping the Mozambique/Venezuela and Michael codes to the new ones.

### Form outline (names are the data contract)

**Settings**
- `form_title` "RISA site observation"
- `form_id` `risa_obs` (countries may append `_<iso3>`)
- `version` yyyymmddNN
- `instance_name` from site, type, feature ID and end time
- `style` `pages theme-grid`
- `default_language` English (en)

**Metadata**
- `start`, `end`, `today`, `username`, `deviceid`, `start_geopoint`
- `audit`, with location priority and `track-changes=true`
- A note telling collectors their location is tracked

**`visit` group**, carried over from the last submission:
- `date` (no later than today and no more than 60 days ago)
- `org` with codes `ndma iom unhcr un_agency ngo undac other`, and `org_other`
- `level_1`, `level_2`: required; choices have explicit parent columns and use `choice_filter level_1=${level_1}`; P-code names
- `site` and `site_other`
- `*_label` calculates, so exports carry names as well as codes

**`obs` group:**
- `sector`, with codes wash, shelter, health, protection, food, logistics, access, energy, environment, commerce, other
- `feature_type`, filtered by sector. Codes are dashboard type codes: water, latrine, hand, health, cfs, dist, storage, shelter, registration, kitchen, gate, landing, choke, plus new ones such as lighting, energy, market, hazard, waste and bathing.
- `feature_id`, e.g. WP-03; this is the label on the map
- `status`, with choices `ok partial no unknown` labelled Working / Partly working / Not working / Can't see. The hint is "Observe, don't ask".
- `status_reason`, shown when status is partial or no
- `count`, the number of units at this point (taps, latrines, tents)
- Detail questions, one list each and relevant on `feature_type`. They are Michael's, cleaned up: latrine permanence, features and accessibility; water source, storage and distribution; tap count; storage type and capacity in m³; health management, cost and beds; lighting type; shelter type and capacity; energy source and uses; access constraint type, road hotspot, crossing and last-mile approach. Each "other" gets its own `<field>_other` question.
- `location` (geopoint): the accuracy constraint warns above 10 m; `location_method` records gps or manual
- `photo`, plus optional `photo_2` and `photo_3`, each gated on the one before; `max-pixels=1600`; the faces hint is kept

**Ungrouped:**
- `note`, the free-text comment. It stays top level so page 2 and the brief read it with no change.
- `note_audio`

**Naming rules**
- snake_case ASCII, 32 characters or fewer, unique across the form
- list names readable
- `other` is the only code for "other"

Write these rules into the `adapt` sheet: "never rename or delete a name or choice once data exists; add only; bump the version".

## Phase 2: dashboard preset

- **`backend/risa/kobo.py`**
  - When `form_id` starts with `risa_obs`, or the form has `obs/feature_type` and `obs/status`, set `field_map` straight from the contract: no heuristics, no mapping step.
  - Read `note` and `count` through the field map.
  - Read `select_multiple` answers.
  - Keep `_submitted_by` out of properties.
- **`symbology/risa.json`**: add the new types and their synonyms, plus a cluster for each in `page2.py` `WHO`.
- **`backend/risa/ingest.py`**: recognise Kobo CSV export columns (`_location_latitude` / `_longitude`, group-prefixed headers) for uploaded exports.
- **Tests**: a fixture generated from the template's asset content, plus submission JSON for every feature type and status.
- **Guide** (`frontend/public/guide/index.html`, `#kobo`), new flow: download the template, adapt it, deploy, connect. A RISA form maps itself; another form gets the mapping dialog.

## Phase 3: end-to-end check

1. Run kobo-mcp `convert_xlsform`, which matches Kobo's own import (formpack + pyxform 3.0).
2. `deploy_form` to a test project. Confirm which account first (the kobo-in-a-box local Kobo or a kf test account).
3. Fill in each path with `preview_form`.
4. Create about 40 dummy submissions across types and statuses with `create_submissions`.
5. Connect the project to a dashboard site. Check the map symbols, page 1 figures, the page 2 questions and gaps, and the brief's data-quality checks.
6. Check that the XLS/CSV and GeoJSON exports open in QGIS.

## Phase 4: SOP v3 and Brief v3 (`ref/`, Markdown)

Write them in parallel with phases 1–2, against the field names fixed in phase 1.

**SOP v3**

Header and front matter:
- Version and date
- Changelog table
- Name: "Rapid Infrastructures & Services Assessment", flagged pending sign-off
- Partners: joint initiative of Kobo, MapAction and Atlas, with UNDAC/OCHA as endorsers

Main text, kept non-technical: the why, how each step usually fails, and links to existing tutorials.

- §1: pilot scope (displacement camps in the first days, handover to the cluster lead around week 3); open source and low-tech first; XLSForm standard.
- §2.1 Data collection:
  - direct observation
  - one observation per submission
  - the status scale
  - the category list from the codebook
  - fixed GPS-track wording (the audit log, if enabled)
  - photo protection
  - daily sync and review
- §2.5–2.6:
  - printed map with a QR code to the online view (source of truth), filterable by sector
  - feedback QR code and form
  - counts on the map
  - RISA and partner logos
- §3:
  - roles: a data/Kobo focal point and a remote GIS owner
  - account ownership
  - data protection (data-sharing agreement, sensitive locations, retention)
  - new §3.x Handover and exit, context-agnostic
- §4: Bahamas pilot; wider scope parked as a later phase.

Annexes:
- **Annex A**: the template package (template, codebook, legacy mapping, country checklist: P-codes from COD-AB, labels, server choice).
- **New Kobo annex.** Topics, each linking to Kobo/ODK documentation:
  - accounts and permissions: organisation-owned project, one account per collector, no shared logins, server choice for data residency
  - testing before fieldwork
  - KoboCollect set-up: QR code, auto-update, Wi-Fi-only send
  - Enketo offline as the fallback
  - changes mid-mission
  - validation status and daily QA
  - exports and the API, including tokens never written in documents
  - media sizes
  - closing and archiving
  - common failures
  - optional kobo-mcp section (deploy, clone, QA review)

**Brief v3**
- Audience: NEMA/NDMA heads
- Partnership and endorsement
- The pilot scope and timeline (3–5 days, follow-up, handover around week 3)
- Products: print plus QR code to the online view
- The toolbox: SOP, annexes, template, dashboard
- Updated "where used"
- Drop "Kobo specialists" and the stale partner line

## Phase 5: website (`~/code/risa`)

- `site/assets/library.js` `action()`: add a `file` field that renders a download link, with files in `site/downloads/`.
- `site/assets/content.js`:
  - the `xlsform` entry becomes `available` with version and file, and a details line on statuses (`ok partial no unknown`, matching the reserved status colours)
  - add a codebook entry
  - point the SOP entry's Kobo note at the new annex
- Do not publish "Kobo for dummies".

## Order and owners

Phases 1 and 4 start together (SOP due 14/11). Phase 2 follows the phase 1 field names. Phase 3 needs a test Kobo account. Commits go to `main` and are pushed by the user. The website is a separate repo, and its pushes deploy straight to risa.kobolabs.dev.

## Open items

- The test Kobo account for phase 3.
- Whether Michael or the Kobo focal point reviews the cleaned detail questions before the template is marked v3.
- Population: no form collects it. Add an optional site-level household estimate, or keep using the Response default.
- The RISA name and logo are still pending sign-off; the documents flag both.

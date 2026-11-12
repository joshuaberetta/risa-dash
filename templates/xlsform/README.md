# RISA XLSForm template

The base Kobo form for a RISA site visit. Responders download it from the RISA website,
adapt it per country and deploy it. A form built from it feeds the RISA dashboard with no
field mapping. One submission is one observation: one feature at one point.

Version 2026111201. English only; countries add languages.

## Files

| File | What it is |
|---|---|
| `spec.py` | The source of truth: survey, choices, settings, the adapt checklist and the legacy codes. Edit this, never the .xlsx. |
| `RISA_template_2026111201.xlsx` | The XLSForm. Sheets `survey`, `choices`, `settings`, plus `codebook` (one row per question) and `adapt` (country checklist and change rules). Kobo and pyxform ignore the last two. |
| `codebook.md` | The data dictionary, for SOP Annex A. |
| `legacy_codes.csv` | The 47 Mozambique/Venezuela `infra_services` codes and the 18 in Michael's draft, mapped to `sector`, `feature_type` and a detail answer where one applies. |
| `check_with_kobo_mcp.py` | Checks the .xlsx with kobo-mcp's converter (formpack + pyxform 3.0, as Kobo imports it) and pyxform. |
| `live_test.py` | Deploys the .xlsx to a Kobo test account, posts 40 dummy observations and saves the fixtures. |
| `fixtures/asset.json` | The deployed asset from kf.kobotoolbox.org (`content` holds survey and choices). |
| `fixtures/data.json` | Its 40 submissions from `/api/v2/assets/<uid>/data/`: all 21 feature types, 10 of each status, around one fictional camp. |

Test project: `aDwoMTyEm5ndfWSh3JCUqS` ("RISA template test (delete me)") on
kf.kobotoolbox.org, account `bob_kobo`.

## Rebuild

```sh
uv run scripts/build_xlsform.py
```

It checks the spec first: names, lists, every `${...}` reference, every code compared in a
`relevant`, the choice filters, a `<name>_other` for each `other`, and the data contract.

Then check it the way Kobo imports it, from a kobo-mcp checkout:

```sh
cd ~/Desktop/work/repos/kobo-mcp
uv run python -I ~/code/risa-dashboard/templates/xlsform/check_with_kobo_mcp.py \
    ~/code/risa-dashboard/templates/xlsform/RISA_template_<version>.xlsx
```

`live_test.py` runs the same way. It reads `KOBO_TOKEN` and `KOBO_BASE_URL` from
kobo-mcp's `.dev.vars` and stops unless the account is `bob_kobo`.

## Adapt for a country

The `adapt` sheet is the checklist. In short:

1. Settings: `form_id` `risa_obs` or `risa_obs_<iso3>`, a country `form_title`, today's `version`.
2. Replace the placeholder `level_1`, `level_2` and `site` lists (XX codes) with COD-AB
   P-codes and the site list. Keep the parent columns (`level_1` on level_2 rows, `level_2`
   on site rows) and the `other` site.
3. Add organisations to `org`. Add languages as `label::<Language> (xx)` columns.
4. Check, test one observation per type, deploy.

By hand: Kobo > New project > Upload an XLSForm > Deploy.

With kobo-mcp:
- `convert_xlsform` to check the file (the same conversion Kobo uses);
- `deploy_form` with `xlsx_base64` to create and deploy the project;
- `clone_project` to start from an existing RISA project, then edit it.

## Change rules

- Never rename or delete a question name or a choice code once data exists. Add only.
- Bump `version` (yyyymmddNN) on every change.
- Names are snake_case ASCII, 32 characters or fewer, unique across the form. `other` is
  the only code for "other".
- Keep the paths marked `contract` in the codebook. The dashboard reads them directly.
- Every label, hint and constraint message column has a language suffix. Kobo refuses a
  form that mixes `label` with `label::English (en)`.

## Notes from the live test (12/11/2026)

- Kobo keeps the `codebook` and `adapt` sheets inside the asset's `content` (as
  `content.codebook`, `content.adapt`) and deploys without complaint.
- Kobo moves the metadata rows to the top of the survey, and fills `_geolocation` from
  `start_geopoint`, the first geopoint. Read `obs/location` for the feature.
- On kf, OpenRosa submissions go to `kc.kobotoolbox.org/submission`. KPI's own
  `/submission` answered 404.
- The import stores `form_id` as `settings.id_string`, and names the project after
  `form_title` (`live_test.py` renames it back).

# /// script
# requires-python = ">=3.12"
# dependencies = ["openpyxl>=3.1"]
# ///
"""Build the RISA XLSForm template from templates/xlsform/spec.py.

    uv run scripts/build_xlsform.py

Writes, in templates/xlsform/:
- RISA_template_<version>.xlsx: survey, choices, settings, plus codebook and adapt sheets
  (Kobo and pyxform ignore sheets they don't know)
- codebook.md: the data dictionary (SOP Annex A)
- legacy_codes.csv: Mozambique/Venezuela and Michael's codes → sector and feature_type

It checks the spec first (names, lists, references, the data contract) and stops on the
first set of problems.
"""

import csv
import importlib.util
import re
import sys
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

sys.dont_write_bytecode = True  # no __pycache__ next to spec.py

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "templates" / "xlsform"

# The data contract (plans/xlsform-template-and-sop.md). Paths are submission keys.
CONTRACT = {
    "start": "start", "end": "end", "today": "today", "username": "username",
    "deviceid": "deviceid", "start_geopoint": "start-geopoint", "audit": "audit",
    "visit/date": "date", "visit/org": "select_one org", "visit/org_other": "text",
    "visit/level_1": "select_one level_1", "visit/level_2": "select_one level_2",
    "visit/site": "select_one site", "visit/site_other": "text",
    "obs/sector": "select_one sector", "obs/feature_type": "select_one feature_type",
    "obs/feature_id": "text", "obs/status": "select_one status", "obs/status_reason": "text",
    "obs/count": "integer", "obs/location": "geopoint",
    "obs/location_method": "select_one location_method",
    "obs/photo": "image", "obs/photo_2": "image", "obs/photo_3": "image",
    "note": "text", "note_audio": "audio",
}
CONTRACT_CODES = {
    "status": ["ok", "partial", "no", "unknown"],
    "location_method": ["gps", "manual"],
    "org": ["ndma", "iom", "unhcr", "un_agency", "ngo", "undac", "other"],
    "sector": ["wash", "shelter", "health", "protection", "food", "logistics", "access",
               "energy", "environment", "commerce", "other"],
}
CONTRACT_TYPES = {
    "wash": ["water", "latrine", "bathing", "hand", "waste"], "shelter": ["shelter"],
    "health": ["health"], "protection": ["cfs", "safe_space", "registration"],
    "food": ["kitchen", "dist"], "logistics": ["storage", "landing", "gate"],
    "access": ["choke"], "energy": ["lighting", "energy"], "environment": ["hazard"],
    "commerce": ["market"], "other": ["other"],
}

SURVEY_COLUMNS = [
    ("type", "type"), ("name", "name"), ("label", "label::{lang}"), ("hint", "hint::{lang}"),
    ("required", "required"), ("relevant", "relevant"), ("constraint", "constraint"),
    ("constraint_message", "constraint_message::{lang}"), ("appearance", "appearance"),
    ("default", "default"), ("parameters", "parameters"), ("choice_filter", "choice_filter"),
    ("calculation", "calculation"),
]
CODEBOOK_ONLY = {"use", "notes"}
NAME = re.compile(r"^[a-z][a-z0-9_]*$")
CODE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
REF = re.compile(r"\$\{(?:last-saved#)?([^}]*)\}")
EQUALS = re.compile(r"\$\{(\w+)\}\s*!?=\s*'([^']*)'")
SELECTED = re.compile(r"selected\(\s*\$\{(\w+)\}\s*,\s*'([^']*)'\s*\)")
GROUPS = {"begin_group", "begin_repeat"}
ENDS = {"end_group", "end_repeat"}
METADATA = {"start", "end", "today", "username", "deviceid", "start-geopoint", "audit"}


def load_spec():
    path = OUT / "spec.py"
    spec = importlib.util.spec_from_file_location("risa_xlsform_spec", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def with_paths(survey):
    """Each question row with its submission path (`group/name`)."""
    stack, out = [], []
    for row in survey:
        t = row["type"]
        if t in ENDS:
            stack.pop()
            continue
        path = "/".join(stack + [row["name"]])
        out.append((path, row))
        if t in GROUPS:
            stack.append(row["name"])
    return out


def list_of(row):
    parts = row["type"].split()
    return parts[1] if parts[0] in ("select_one", "select_multiple") and len(parts) > 1 else None


def check(spec):
    """Every problem in the spec, as text."""
    errors = []
    survey, choices = spec.SURVEY, spec.CHOICES
    rows = with_paths(survey)
    by_name = {}
    for path, row in rows:
        name = row["name"]
        if not NAME.match(name) or len(name) > 32:
            errors.append(f"{path}: name must be snake_case ASCII, 32 characters or fewer.")
        if name in by_name:
            errors.append(f"{path}: duplicate name.")
        by_name[name] = row
        unknown = set(row) - {k for k, _ in SURVEY_COLUMNS} - CODEBOOK_ONLY
        if unknown:
            errors.append(f"{path}: unknown keys {sorted(unknown)}.")
        lst = list_of(row)
        if lst and lst not in choices:
            errors.append(f"{path}: list {lst!r} is not in CHOICES.")
        if row["type"] not in METADATA | GROUPS | {"calculate"} and not row.get("label"):
            errors.append(f"{path}: needs a label.")
        if "constraint" in row and "constraint_message" not in row:
            errors.append(f"{path}: a constraint needs a constraint_message.")
        if row["type"] in ("integer", "decimal") and "constraint" not in row:
            errors.append(f"{path}: numbers need a constraint.")
    depth = 0
    for row in survey:
        depth += row["type"] in GROUPS
        depth -= row["type"] in ENDS
        if depth < 0:
            errors.append("an end_group has no begin_group.")
    if depth:
        errors.append("a group is never closed.")

    used = {list_of(r) for _, r in rows} - {None}
    for lst, items in choices.items():
        if not NAME.match(lst) or len(lst) > 32:
            errors.append(f"list {lst!r}: name must be snake_case ASCII, 32 characters or fewer.")
        if lst not in used:
            errors.append(f"list {lst!r} is not used by any question.")
        codes = [c[0] for c in items]
        if len(codes) != len(set(codes)):
            errors.append(f"list {lst!r}: duplicate codes.")
        for code in codes:
            if not CODE.match(code) or len(code) > 32:
                errors.append(f"list {lst!r}: code {code!r} must be ASCII, 32 characters or fewer.")
            if code != "other" and "other" in code:
                errors.append(f"list {lst!r}: {code!r}; `other` is the only code for other.")

    def codes(name):
        lst = list_of(by_name[name]) if name in by_name else None
        return {c[0] for c in choices.get(lst, [])} if lst else None

    for path, row in rows:
        for key in ("relevant", "constraint", "default", "calculation", "choice_filter", "label"):
            text = row.get(key) or ""
            for ref in REF.findall(text):
                if ref not in by_name:
                    errors.append(f"{path} {key}: ${{{ref}}} is not a question.")
            for pattern in (EQUALS, SELECTED):
                for ref, value in pattern.findall(text):
                    known = codes(ref)
                    if known is not None and value and value not in known:
                        errors.append(f"{path} {key}: {value!r} is not a code of {ref}.")
        cf = row.get("choice_filter")
        if cf:
            lst = list_of(row)
            for column, ref in re.findall(r"(\w+)\s*=\s*\$\{(\w+)\}", cf):
                parent = codes(ref) or set()
                for item in choices[lst]:
                    extra = item[2] if len(item) > 2 else {}
                    if item[0] == "other" and column not in extra:
                        continue
                    if extra.get(column) not in parent:
                        errors.append(f"{path}: choice {item[0]!r} has no valid `{column}` value.")
        lst = list_of(row)
        if lst and "other" in (codes(row["name"]) or set()) and row["name"] != "sector":
            if f"{row['name']}_other" not in by_name:
                errors.append(f"{path}: offers `other` but has no {row['name']}_other.")

    paths = {p: r for p, r in rows}
    for path, rtype in CONTRACT.items():
        if path not in paths:
            errors.append(f"contract: {path} is missing.")
        elif paths[path]["type"] != rtype:
            errors.append(f"contract: {path} is {paths[path]['type']!r}, not {rtype!r}.")
    for lst, want in CONTRACT_CODES.items():
        if [c[0] for c in choices[lst]] != want:
            errors.append(f"contract: list {lst} must be {want}.")
    got = {}
    for code, _, extra in choices["feature_type"]:
        got.setdefault(extra["sector"], []).append(code)
    if got != CONTRACT_TYPES:
        errors.append(f"contract: feature_type codes by sector are {got}.")

    types = {c[0] for c in choices["feature_type"]}
    for source in (spec.LEGACY_MZ_VE, spec.LEGACY_MICHAEL):
        for code, _, ftype, field, value, _ in source:
            if ftype not in types:
                errors.append(f"legacy {code}: {ftype!r} is not a feature_type.")
            if field and value not in (codes(field) or set()):
                errors.append(f"legacy {code}: {value!r} is not a code of {field}.")
    if len(spec.LEGACY_MZ_VE) != 47 or len(spec.LEGACY_MICHAEL) != 18:
        errors.append("legacy: expected 47 Mozambique/Venezuela codes and 18 of Michael's.")
    return errors


# Writers.

HEAD = Font(bold=True)
FILL = PatternFill("solid", fgColor="E8EEF4")


def sheet(wb, title, header, rows, widths=None):
    ws = wb.create_sheet(title)
    ws.append(header)
    for cell in ws[1]:
        cell.font = HEAD
        cell.fill = FILL
    for row in rows:
        ws.append(["" if v is None else v for v in row])
    ws.freeze_panes = "A2"
    for i, h in enumerate(header, 1):
        width = (widths or {}).get(h) or min(60, max(10, len(str(h)) + 2))
        ws.column_dimensions[get_column_letter(i)].width = width
    return ws


def extra_columns(choices):
    cols = []
    for items in choices.values():
        for item in items:
            for key in item[2] if len(item) > 2 else {}:
                if key not in cols:
                    cols.append(key)
    return cols


def codebook_rows(spec):
    """One row per question: path, type, list, label, relevant, required, constraint,
    contract, dashboard use, notes."""
    out = []
    for path, row in with_paths(spec.SURVEY):
        if row["type"] in GROUPS or row["type"] == "note":
            continue
        rtype = row["type"].split()[0]
        out.append({
            "path": path,
            "type": rtype,
            "list": list_of(row) or "",
            "label": row.get("label", ""),
            "relevant": row.get("relevant", ""),
            "required": "yes" if row.get("required") else "",
            "constraint": row.get("constraint", "") or row.get("calculation", ""),
            "contract": "contract" if path in CONTRACT else "",
            "use": row.get("use", ""),
            "notes": row.get("notes", ""),
        })
    return out


def write_xlsx(spec, path):
    lang = spec.LANG
    wb = Workbook()
    wb.remove(wb.active)
    header = [col.format(lang=lang) for _, col in SURVEY_COLUMNS]
    rows = []
    for row in spec.SURVEY:
        values = []
        for key, _ in SURVEY_COLUMNS:
            v = row.get(key)
            values.append("true" if v is True else v)
        rows.append(values)
    sheet(wb, "survey", header, rows, {"type": 32, "name": 24, f"label::{lang}": 50,
                                       f"hint::{lang}": 40, "relevant": 50, "constraint": 30})
    extras = extra_columns(spec.CHOICES)
    crow = []
    for lst, items in spec.CHOICES.items():
        for item in items:
            extra = item[2] if len(item) > 2 else {}
            crow.append([lst, item[0], item[1]] + [extra.get(c) for c in extras])
    sheet(wb, "choices", ["list_name", "name", f"label::{lang}"] + extras, crow,
          {"list_name": 20, "name": 22, f"label::{lang}": 50})
    settings = spec.SETTINGS
    sheet(wb, "settings", list(settings), [list(settings.values())], {"instance_name": 60})
    cb = codebook_rows(spec)
    keys = ["path", "type", "list", "label", "relevant", "required", "constraint", "contract",
            "use", "notes"]
    ws = sheet(wb, "codebook", keys, [[r[k] for k in keys] for r in cb],
               {"path": 28, "label": 40, "relevant": 50, "constraint": 30, "use": 30, "notes": 50})
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws = sheet(wb, "adapt", ["topic", "step"], spec.ADAPT, {"topic": 18, "step": 110})
    for row in ws.iter_rows(min_row=2):
        row[1].alignment = Alignment(wrap_text=True, vertical="top")
    stamp = datetime.strptime(spec.VERSION[:8], "%Y%m%d")
    wb.properties.creator = "RISA"
    wb.properties.title = settings["form_title"]
    wb.properties.created = wb.properties.modified = stamp
    wb.save(path)


def md_cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def write_codebook(spec, path):
    v = spec.VERSION
    lines = [
        f"# RISA site observation: codebook (version {v})",
        "",
        "Generated by `scripts/build_xlsform.py` from `templates/xlsform/spec.py`. Do not edit by hand.",
        "",
        "One submission is one observation: one feature at one point. The `visit` answers carry "
        "over from the last submission. Paths are the keys Kobo sends (`group/name`) and the "
        "column headers of a Kobo export with group names kept.",
        "",
        "Rows marked `contract` are read by the RISA dashboard with no mapping step. Never rename "
        "or delete a name or a choice code once data exists; add only, and bump the version.",
        "",
        "## Status",
        "",
        "| Code | Label | Map |",
        "|---|---|---|",
    ]
    status_map = {"ok": "green, filled", "partial": "amber, half", "no": "red, crossed",
                  "unknown": "grey, outline (not assessed)"}
    for code, label in spec.CHOICES["status"]:
        lines.append(f"| `{code}` | {label} | {status_map[code]} |")
    lines += [
        "",
        "Observe, don't ask. For an access constraint or a hazard, Working means passable, "
        "Partly working restricted and Not working blocked. `hazard` is not a service: the "
        "dashboard leaves it out of service counts.",
        "",
        "## Sectors and feature types",
        "",
        "Feature type codes are the dashboard's RISA type codes (`symbology/risa.json`).",
        "",
        "| Sector | Code | Feature type |",
        "|---|---|---|",
    ]
    sectors = dict(spec.CHOICES["sector"])
    for code, label, extra in spec.CHOICES["feature_type"]:
        lines.append(f"| {sectors[extra['sector']]} (`{extra['sector']}`) | `{code}` | {label} |")
    lines += ["", "## Questions", "",
              "| Path | Type | List | Label | Shown when | Req. | Constraint / calculation | Contract | Dashboard | Notes |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for r in codebook_rows(spec):
        cells = [f"`{r['path']}`", r["type"], f"`{r['list']}`" if r["list"] else "",
                 r["label"], f"`{r['relevant']}`" if r["relevant"] else "", r["required"],
                 f"`{r['constraint']}`" if r["constraint"] else "", r["contract"], r["use"], r["notes"]]
        lines.append("| " + " | ".join(md_cell(c) for c in cells) + " |")
    lines += ["", "## Code lists", ""]
    for lst, items in spec.CHOICES.items():
        if lst in ("feature_type", "status"):
            continue
        lines += [f"### `{lst}`", "", "| Code | Label |", "|---|---|"]
        for item in items:
            extra = item[2] if len(item) > 2 else {}
            note = " (" + ", ".join(f"{k} {val}" for k, val in extra.items()) + ")" if extra else ""
            lines.append(f"| `{item[0]}` | {md_cell(item[1])}{note} |")
        lines.append("")
    lines += [
        "`level_1`, `level_2` and `site` are placeholders (XX codes). Each country replaces them "
        "with COD-AB P-codes and its own site list.",
        "",
        "## Settings",
        "",
        "| Setting | Value |",
        "|---|---|",
    ]
    for k, val in spec.SETTINGS.items():
        lines.append(f"| `{k}` | `{md_cell(val)}` |")
    lines += [
        "",
        "## Country adaptation",
        "",
        "| Topic | Step |",
        "|---|---|",
    ]
    for topic, step in spec.ADAPT:
        lines.append(f"| {topic} | {md_cell(step)} |")
    lines += [
        "",
        "## From Michael's draft (RISA_XXX.xlsx)",
        "",
        "| Draft name | Template name |",
        "|---|---|",
    ]
    for old, new in spec.MICHAEL_RENAMES:
        lines.append(f"| `{old}` | `{new}` |")
    lines += [
        "",
        "## Legacy codes",
        "",
        "`legacy_codes.csv` maps the 47 `infra_services` codes of the Mozambique and Venezuela "
        "forms, and the 18 of Michael's draft, to `sector` and `feature_type`, with a detail "
        "answer where one applies.",
        "",
    ]
    path.write_text("\n".join(lines))


def write_legacy(spec, path):
    sector_of = {code: extra["sector"] for code, _, extra in spec.CHOICES["feature_type"]}
    with path.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["source", "legacy_code", "legacy_label", "sector", "feature_type",
                    "detail_field", "detail_value", "note"])
        for source, rows in (("mozambique_venezuela", spec.LEGACY_MZ_VE),
                             ("michael_draft", spec.LEGACY_MICHAEL)):
            for code, label, ftype, field, value, note in rows:
                w.writerow([source, code, label, sector_of[ftype], ftype,
                            f"obs/{field}" if field else "", value, note])


def main():
    spec = load_spec()
    errors = check(spec)
    if errors:
        print("The spec has problems:", *errors, sep="\n- ", file=sys.stderr)
        sys.exit(1)
    xlsx = OUT / f"RISA_template_{spec.VERSION}.xlsx"
    for old in OUT.glob("RISA_template_*.xlsx"):
        if old != xlsx:
            old.unlink()
    write_xlsx(spec, xlsx)
    write_codebook(spec, OUT / "codebook.md")
    write_legacy(spec, OUT / "legacy_codes.csv")
    print(f"Wrote {xlsx.relative_to(ROOT)}, codebook.md and legacy_codes.csv.")


if __name__ == "__main__":
    main()

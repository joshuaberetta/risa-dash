"""Deploy the template to a Kobo test account, add dummy observations, save fixtures.

Run from a kobo-mcp checkout (it uses kobo-mcp's OpenRosa builder and dummy answers):

    cd ~/Desktop/work/repos/kobo-mcp
    uv run python -I /path/to/templates/xlsform/live_test.py \
        /path/to/templates/xlsform/RISA_template_<version>.xlsx [--uid <asset uid>]

KOBO_TOKEN and KOBO_BASE_URL are read from kobo-mcp's .dev.vars into this process only;
the token is never printed. The account must be `bob_kobo`, or nothing is sent.

Steps: create the project "RISA template test (delete me)", import the XLSForm through
Kobo's own /api/v2/imports/ (so Kobo itself reads the extra codebook and adapt sheets),
deploy, post about 40 observations (every feature type and status) around one fictional
camp, then write fixtures/asset.json and fixtures/data.json. --uid <asset uid> only
saves the fixtures again from that project; add --submit to post the observations to it
first.
"""

import json
import os
import random
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

sys.path.insert(0, str(Path.cwd() / "src"))  # see check_with_kobo_mcp.py

from kobo_mcp.formcontent import mock, openrosa, xlsform  # noqa: E402

ACCOUNT = "bob_kobo"
NAME = "RISA template test (delete me)"
HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"

# A fictional camp ("Placeholder camp A", XX010101) on open ground in central Mozambique.
CAMP = (-19.0412, 34.4986)

# (feature_type, sector, ID prefix, count range, comments)
TYPES = {
    "water": ("wash", "WP", (1, 4), "Queue of about 30 people at midday. Apron cracked."),
    "latrine": ("wash", "LT", (4, 12), "Block of cubicles, doors on most. Smell from the pit."),
    "bathing": ("wash", "BA", (2, 8), "Screened with tarpaulin, no roof."),
    "hand": ("wash", "HW", (1, 4), "Tippy taps next to the latrines, soap on one."),
    "waste": ("wash", "WS", (1, 6), "Bins overflowing, flies."),
    "shelter": ("shelter", "SH", (10, 60), "Rows of family tents, some on low ground."),
    "health": ("health", "HC", (1, 2), "Mobile clinic in a tent, run every morning."),
    "cfs": ("protection", "CF", (1, 1), "Tent with mats, games and two facilitators."),
    "safe_space": ("protection", "SS", (1, 1), "Fenced area with a women's committee meeting."),
    "registration": ("protection", "RG", (1, 2), "Desk under a tree, long queue for registration."),
    "kitchen": ("food", "KT", (1, 3), "Communal cooking with firewood, smoke inside."),
    "dist": ("food", "DP", (1, 1), "Distribution of food rations by the food cluster."),
    "storage": ("logistics", "ST", (1, 2), "Mobile storage unit, half full of kits."),
    "landing": ("logistics", "LZ", (1, 1), "Football field, flat and dry, clear of wires."),
    "gate": ("logistics", "GT", (1, 1), "Main entrance with a guard post."),
    "choke": ("access", "AC", (1, 1), "Road under water after the rain."),
    "lighting": ("energy", "LI", (2, 12), "Solar street lights along the main path."),
    "energy": ("energy", "EN", (1, 2), "Generator with a charging point for phones."),
    "hazard": ("environment", "HZ", (1, 1), "Stagnant water next to the shelters."),
    "market": ("commerce", "MK", (5, 30), "Small stalls selling vegetables and charcoal."),
    "other": ("other", "OT", (1, 1), "School building used as an office."),
}
# 40 observations: every type once, the common ones more often.
PLAN = list(TYPES) + [
    "water", "water", "water", "latrine", "latrine", "latrine", "shelter", "shelter",
    "shelter", "hand", "bathing", "health", "dist", "storage", "choke", "lighting",
    "waste", "kitchen", "hazard",
]
STATUSES = ["ok", "partial", "no", "unknown"]
REASONS = {
    "water": "2 of 6 taps broken", "latrine": "Pit full, 3 cubicles locked",
    "bathing": "No water in the tank", "hand": "No soap, one tap missing",
    "waste": "Not emptied for a week", "shelter": "Flooded after the rain",
    "health": "No staff in the afternoon", "cfs": "Tent torn", "safe_space": "Fence broken",
    "registration": "Only open two days a week", "kitchen": "No firewood",
    "dist": "Stock ran out", "storage": "Door damaged, roof leaking",
    "landing": "Tall grass and a fallen tree", "gate": "Gate locked at night",
    "choke": "Water 50 cm deep, only trucks pass", "lighting": "4 of 10 lights off",
    "energy": "Out of fuel", "hazard": "Spreading towards the latrines",
    "market": "Few stalls open", "other": "Roof damaged",
}
TEXTS = {
    "obs/health_ngo": "MSF",
    "obs/access_description": "Only trucks pass. 300 m detour by the school road.",
}
ORGS = [("iom", None), ("unhcr", None), ("ngo", "MSF"), ("ndma", None), ("un_agency", "WFP")]


def load_env() -> None:
    path = Path(os.environ.get("KOBO_DEV_VARS", Path.cwd() / ".dev.vars"))
    for line in path.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            if key.strip() in ("KOBO_TOKEN", "KOBO_BASE_URL"):
                os.environ[key.strip()] = value.strip().strip('"').strip("'")


def client() -> httpx.Client:
    return httpx.Client(
        base_url=os.environ["KOBO_BASE_URL"].rstrip("/"),
        headers={"Authorization": f"Token {os.environ['KOBO_TOKEN']}", "Accept": "application/json"},
        timeout=120,
    )


def ok(resp: httpx.Response, what: str) -> dict:
    if resp.status_code >= 400:
        sys.exit(f"{what} failed: HTTP {resp.status_code} {resp.text[:800]}")
    return resp.json() if resp.content else {}


def deploy(kobo: httpx.Client, xlsx: Path) -> str:
    asset = ok(kobo.post("/api/v2/assets/", json={"name": NAME, "asset_type": "survey", "settings": {}}),
               "create project")
    uid = asset["uid"]
    print("created", uid)
    dest = f"{kobo.base_url}/api/v2/assets/{uid}/"
    with xlsx.open("rb") as f:
        task = ok(kobo.post("/api/v2/imports/", data={"destination": dest},
                            files={"file": (xlsx.name, f, "application/vnd.ms-excel")}), "import")
    for _ in range(60):
        state = ok(kobo.get(f"/api/v2/imports/{task['uid']}/"), "import status")
        if state.get("status") in ("complete", "error"):
            break
        time.sleep(1)
    messages = state.get("messages") or {}
    messages.pop("audit_logs", None)
    print("import:", state.get("status"), json.dumps(messages)[:600])
    if state.get("status") != "complete":
        sys.exit("The import did not complete.")
    asset = ok(kobo.patch(f"/api/v2/assets/{uid}/", json={"name": NAME}), "rename")
    vid = asset["version_id"]
    dep = kobo.post(f"/api/v2/assets/{uid}/deployment/", json={"active": True, "version_id": vid})
    ok(dep, "deploy")
    print("deployed", uid, "version", vid)
    return uid


def compare(content: dict, xlsx: Path) -> None:
    """Kobo's stored content against kobo-mcp's own conversion of the same file."""
    ours = xlsform.to_content(xlsform.sheets_from_file(xlsx.read_bytes()))

    def rows(c, sheet):
        return [{k: v for k, v in r.items() if not k.startswith("$")} for r in c.get(sheet, [])]

    for sheet in ("survey", "choices"):
        a, b = rows(content, sheet), rows(ours, sheet)
        print(f"{sheet}: Kobo {len(a)} rows, kobo-mcp {len(b)}, identical: {a == b}")
    extra = sorted(set(content) - {"schema", "survey", "choices", "settings", "translations",
                                   "translated"})
    print("other keys in Kobo's content:", extra or "none")
    print("settings identical:", {k: v for k, v in content["settings"].items()} == ours["settings"],
          content["settings"])


def answers_for(i: int, ftype: str, status: str, now: datetime, rng: random.Random) -> dict:
    sector, prefix, (lo, hi), comment = TYPES[ftype]
    org, org_other = ORGS[i % len(ORGS)]
    end = now - timedelta(days=i // 20, hours=(i % 20) * 0.3)
    start = end - timedelta(minutes=rng.randint(2, 7))
    lat = CAMP[0] + rng.uniform(-0.0022, 0.0022)
    lon = CAMP[1] + rng.uniform(-0.0022, 0.0022)
    manual = rng.random() < 0.15
    acc = 0.0 if manual else round(rng.uniform(2.5, 14.0), 1)
    a = {
        "start": start.isoformat(timespec="milliseconds"),
        "end": end.isoformat(timespec="milliseconds"),
        "today": end.date().isoformat(),
        "start_geopoint": f"{lat + 0.0003:.6f} {lon - 0.0002:.6f} 18 {acc or 6.0}",
        "visit/date": end.date().isoformat(),
        "visit/org": org,
        "visit/level_1": "XX01",
        "visit/level_2": "XX0101",
        "visit/site": "XX010101",
        # Collect computes these; kobo-mcp's dummy filler can't evaluate jr:choice-name.
        "visit/level_1_label": "Placeholder province 1",
        "visit/level_2_label": "Placeholder district 1.1",
        "visit/site_label": "Placeholder camp A",
        "obs/sector": sector,
        "obs/feature_type": ftype,
        "obs/feature_id": f"{prefix}-{i + 1:02d}",
        "obs/status": status,
        "obs/count": str(rng.randint(lo, hi)),
        "obs/location": f"{lat:.6f} {lon:.6f} {rng.randint(14, 22)} {acc}",
        "obs/location_method": "manual" if manual else "gps",
        "note": comment,
    }
    if org_other:
        a["visit/org_other"] = org_other
    if status in ("partial", "no"):
        a["obs/status_reason"] = REASONS[ftype]
    if ftype == "other":
        a["obs/feature_type_other"] = "School building"
    if ftype in ("hazard", "choke", "landing", "gate", "registration"):
        a.pop("obs/count")
    return a


def submission_url(kobo: httpx.Client) -> str:
    """OpenRosa submissions go to the KoboCAT host. On kf (12/11/2026) KPI's own
    /submission answered 404, while kc.kobotoolbox.org/submission took them (201)."""
    if os.environ.get("KOBO_SUBMIT_URL"):
        return os.environ["KOBO_SUBMIT_URL"]
    return str(kobo.base_url).replace("://kf.", "://kc.").replace("://eu.", "://kc-eu.") + "/submission"


def submit(kobo: httpx.Client, uid: str, n: int) -> None:
    asset = ok(kobo.get(f"/api/v2/assets/{uid}/"), "asset")
    versions = asset.get("deployed_versions") or {}
    results = versions.get("results") or []
    vid = asset.get("deployed_version_id") or results[0]["uid"]
    latest = next((v for v in results if v.get("uid") == vid), {})
    deployed = str(latest.get("date_deployed") or "")[:19].replace("T", " ")
    label = f"{versions.get('count', len(results))} ({deployed})"
    tree = openrosa.parse(asset["content"])
    rng = random.Random(20261112)
    now = datetime.now(UTC).replace(microsecond=0)
    plan = PLAN[:n]
    codes = {"created": 0, "failed": 0}
    for i, ftype in enumerate(plan):
        status = STATUSES[i % len(STATUSES)]
        raw = answers_for(i, ftype, status, now, rng)
        answers, errors, _ = openrosa.check(tree, raw)
        if errors:
            sys.exit(f"submission {i}: {errors}")
        filled = mock.fill(tree, answers, rng, now).answers
        # The filler writes lorem ipsum in free text; use plain field wording instead.
        for key in list(filled):
            if key.endswith("_other") and key not in raw:
                filled[key] = "Not in the list, see the comment"
        filled.update({k: v for k, v in TEXTS.items() if k in filled})
        if "obs/count" not in raw:
            filled.pop("obs/count", None)  # not countable
        # Keep the optional extras rare, as in the field.
        if rng.random() > 0.3:
            for key in ("obs/photo_2", "obs/photo_3"):
                filled.pop(key, None)
        elif rng.random() > 0.5:
            filled.pop("obs/photo_3", None)
        if rng.random() > 0.2:
            filled.pop("note_audio", None)
        if rng.random() < 0.1:
            for key in ("obs/photo", "obs/photo_2", "obs/photo_3"):
                filled.pop(key, None)
        instance = str(uuid.uuid4())
        xml = openrosa.build_xml(tree, filled, uid=uid, version=label, version_uid=vid,
                                 formhub_uuid=asset["deployment__uuid"],
                                 instance_id=f"uuid:{instance}")
        parts = [("xml_submission_file", (f"{instance}.xml", xml, "text/xml"))] + [
            (f.filename, (f.filename, f.data, f.mimetype)) for f in openrosa.attachments(filled)
        ]
        resp = kobo.post(submission_url(kobo), files=parts, headers={"X-OpenRosa-Version": "1.0"})
        if resp.status_code in (201, 202):
            codes["created"] += 1
        else:
            codes["failed"] += 1
            print(f"submission {i} ({ftype}, {status}): HTTP {resp.status_code} {resp.text[:300]}")
    print("submissions:", codes)


def save(kobo: httpx.Client, uid: str) -> None:
    FIXTURES.mkdir(exist_ok=True)
    asset = ok(kobo.get(f"/api/v2/assets/{uid}/", params={"format": "json"}), "asset")
    data = ok(kobo.get(f"/api/v2/assets/{uid}/data/", params={"format": "json", "limit": 1000}),
              "data")
    (FIXTURES / "asset.json").write_text(json.dumps(asset, indent=1, ensure_ascii=False) + "\n")
    (FIXTURES / "data.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    types = sorted({s.get("obs/feature_type") for s in data["results"]})
    statuses = sorted({s.get("obs/status") for s in data["results"]})
    print(f"saved fixtures: {data['count']} submissions, {len(types)} types {types}, statuses {statuses}")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    xlsx = Path(args[0]).resolve()
    uid = sys.argv[sys.argv.index("--uid") + 1] if "--uid" in sys.argv else None
    load_env()
    with client() as kobo:
        me = ok(kobo.get("/me/"), "whoami (/me/)")
        if me.get("username") != ACCOUNT:
            sys.exit(f"Signed in as {me.get('username')!r}, not {ACCOUNT!r}. Nothing sent.")
        print("account:", me["username"], kobo.base_url)
        fresh = uid is None
        if fresh:
            uid = deploy(kobo, xlsx)
            content = ok(kobo.get(f"/api/v2/assets/{uid}/"), "asset")["content"]
            compare(content, xlsx)
        if fresh or "--submit" in sys.argv:
            submit(kobo, uid, len(PLAN))
        save(kobo, uid)
        print("uid:", uid)


if __name__ == "__main__":
    main()

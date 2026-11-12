"""The RISA XLSForm template: the source of truth.

`scripts/build_xlsform.py` reads this module and writes the XLSForm, the codebook and the
legacy code table. Edit this file, never the generated .xlsx.

Names are the data contract (plans/xlsform-template-and-sop.md, "Data contract"). Once a
form is in use: never rename or delete a name or a choice code; add only; bump VERSION.

Each survey row is a dict with XLSForm columns (type, name, label, hint, required,
relevant, constraint, constraint_message, appearance, default, parameters,
choice_filter, calculation) and two codebook-only keys: `use` (what the dashboard does
with the answer) and `notes`.
"""

VERSION = "2026111201"  # yyyymmddNN
LANG = "English (en)"

SETTINGS = {
    "form_title": "RISA site observation",
    "form_id": "risa_obs",
    "version": VERSION,
    "instance_name": (
        "concat(${site_label}, ' - ', jr:choice-name(${feature_type}, '${feature_type}'), ' ', "
        "${feature_id}, ' - ', format-date-time(${end}, '%Y-%m-%d %H:%M'))"
    ),
    "style": "pages theme-grid",
    "default_language": LANG,
}


def ft(*codes):
    """relevant: the observation is one of these feature types."""
    return " or ".join(f"${{feature_type}} = '{c}'" for c in codes)


def picked(field, *codes, multi=False):
    """relevant: `field` has one of these codes (selected() for select_multiple)."""
    if multi:
        return " or ".join(f"selected(${{{field}}}, '{c}')" for c in codes)
    return " or ".join(f"${{{field}}} = '{c}'" for c in codes)


def between(low, high, unit=""):
    unit = f" {unit}" if unit else ""
    return {
        "constraint": f". >= {low} and . <= {high}",
        "constraint_message": f"Enter a number from {low} to {high}{unit}.",
    }


NONE_ALONE = {
    "constraint": "not(selected(., 'none') and count-selected(.) > 1)",
    "constraint_message": "\"None\" can't be combined with other answers.",
}


def other(field, label="Specify other", multi=False, relevant_extra=None):
    """The `<field>_other` text question for a question that offers `other`."""
    rel = picked(field, "other", multi=multi)
    if relevant_extra:
        rel = f"({relevant_extra}) and ({rel})"
    return {
        "type": "text",
        "name": f"{field}_other",
        "label": label,
        "required": True,
        "relevant": rel,
        "appearance": "w2",
        "use": "popup",
    }


SURVEY = [
    # Metadata. Kobo fills these in; the collector sees none of them.
    {"type": "start", "name": "start"},
    {"type": "end", "name": "end", "use": "observed_at (when the observation was saved)"},
    {"type": "today", "name": "today"},
    {"type": "username", "name": "username"},
    {"type": "deviceid", "name": "deviceid"},
    {
        "type": "audit",
        "name": "audit",
        "parameters": (
            "location-priority=high-accuracy location-min-interval=10 "
            "location-max-age=20 track-changes=true"
        ),
        "notes": (
            "KoboCollect only. Logs each question opened and changed, with the device "
            "location every 10 s while the form is open. It is not a continuous GPS track "
            "between forms."
        ),
    },
    {
        "type": "start-geopoint",
        "name": "start_geopoint",
        "notes": (
            "Where the form was opened. Kobo fills `_geolocation` (its own map) from this "
            "point, not from obs/location; read obs/location for the feature."
        ),
    },
    # Visit: the same for every observation on one site visit, carried over.
    {
        "type": "begin_group",
        "name": "visit",
        "label": "Visit",
        "appearance": "field-list",
    },
    {
        "type": "note",
        "name": "location_notice",
        "label": (
            "**This form records your location** while it is open (KoboCollect). It is used to "
            "check where observations were made. Form version " + VERSION + "."
        ),
    },
    {
        "type": "date",
        "name": "date",
        "label": "Date of observation",
        "required": True,
        "default": "today()",
        "constraint": (
            ". <= today() and decimal-date-time(.) >= decimal-date-time(today()) - 60"
        ),
        "constraint_message": "The date can't be in the future or more than 60 days ago.",
        "appearance": "w2",
    },
    {
        "type": "select_one org",
        "name": "org",
        "label": "Organisation",
        "required": True,
        "default": "${last-saved#org}",
        "appearance": "w2 minimal",
    },
    {
        "type": "text",
        "name": "org_other",
        "label": "Which organisation?",
        "hint": "Its usual short name, e.g. WFP or MSF.",
        "required": True,
        "relevant": picked("org", "un_agency", "ngo", "other"),
        "default": "${last-saved#org_other}",
        "appearance": "w2",
    },
    {
        "type": "select_one level_1",
        "name": "level_1",
        "label": "Province / state",
        "required": True,
        "default": "${last-saved#level_1}",
        "appearance": "w2 minimal",
        "notes": "P-code (COD-AB admin 1).",
    },
    {
        "type": "select_one level_2",
        "name": "level_2",
        "label": "District / municipality",
        "required": True,
        "default": "${last-saved#level_2}",
        "appearance": "w2 minimal",
        "choice_filter": "level_1=${level_1}",
        "notes": "P-code (COD-AB admin 2). Filtered by the `level_1` column in choices.",
    },
    {
        "type": "select_one site",
        "name": "site",
        "label": "Site (camp or collective centre)",
        "required": True,
        "default": "${last-saved#site}",
        "appearance": "w2 minimal",
        "choice_filter": "level_2=${level_2} or name='other'",
        "use": "the dashboard site",
        "notes": "Site code. Filtered by the `level_2` column in choices.",
    },
    {
        "type": "text",
        "name": "site_other",
        "label": "Site name",
        "hint": "The name people use for it.",
        "required": True,
        "relevant": picked("site", "other"),
        "default": "${last-saved#site_other}",
        "appearance": "w2",
    },
    {
        "type": "calculate",
        "name": "level_1_label",
        "calculation": "jr:choice-name(${level_1}, '${level_1}')",
        "notes": "The province name, so exports carry names as well as codes.",
    },
    {
        "type": "calculate",
        "name": "level_2_label",
        "calculation": "jr:choice-name(${level_2}, '${level_2}')",
        "notes": "The district name.",
    },
    {
        "type": "calculate",
        "name": "site_label",
        "calculation": "if(${site} = 'other', ${site_other}, jr:choice-name(${site}, '${site}'))",
        "notes": "The site name (the typed name for `other`).",
    },
    {"type": "end_group"},
    # Observation: one feature per submission.
    {
        "type": "begin_group",
        "name": "obs",
        "label": "Observation",
        "appearance": "field-list",
    },
    {
        "type": "select_one sector",
        "name": "sector",
        "label": "Sector",
        "required": True,
        "appearance": "w2",
    },
    {
        "type": "select_one feature_type",
        "name": "feature_type",
        "label": "What is it?",
        "required": True,
        "appearance": "w2",
        "choice_filter": "sector=${sector}",
        "use": "map symbol (RISA type code)",
        "notes": "Filtered by the `sector` column in choices. Codes are RISA type codes.",
    },
    {
        "type": "text",
        "name": "feature_type_other",
        "label": "What is it?",
        "hint": "A few words, e.g. school, church, playground.",
        "required": True,
        "relevant": ft("other"),
        "use": "popup",
    },
    {
        "type": "text",
        "name": "feature_id",
        "label": "Feature ID",
        "hint": "Short and unique on this site, e.g. WP-03. Use the same ID when you come back to this point.",
        "constraint": "string-length(.) <= 12",
        "constraint_message": "Keep the ID to 12 characters or fewer.",
        "appearance": "w2",
        "use": "map label",
    },
    {
        "type": "integer",
        "name": "count",
        "label": "How many units are at this point?",
        "hint": "e.g. 6 latrine cubicles, 20 tents, 2 water tanks. Leave empty if it can't be counted.",
        "appearance": "w2",
        **between(0, 1000),
        "use": "counts on the map and page 1",
    },
    {
        "type": "select_one status",
        "name": "status",
        "label": "Is it working?",
        "hint": "Observe, don't ask.",
        "required": True,
        "use": "map colour, page 1 figures",
    },
    {
        "type": "note",
        "name": "status_access_note",
        "label": (
            "For an access constraint or a hazard: Working = passable, Partly working = "
            "restricted, Not working = blocked."
        ),
        "relevant": ft("choke", "hazard"),
    },
    {
        "type": "text",
        "name": "status_reason",
        "label": "What is wrong?",
        "hint": "What you saw, e.g. 2 of 6 taps broken, flooded, locked.",
        "relevant": picked("status", "partial", "no"),
        "use": "popup, page 2",
    },
    # Detail questions, one set per feature type (cleaned from Michael's draft).
    # Latrines and bathing.
    {
        "type": "select_one permanence",
        "name": "permanence",
        "label": "How permanent is it?",
        "relevant": ft("latrine", "bathing"),
        "appearance": "w2",
    },
    {
        "type": "select_multiple wash_features",
        "name": "wash_features",
        "label": "What does it have?",
        "relevant": ft("latrine", "bathing"),
        "appearance": "w2",
        **NONE_ALONE,
    },
    {
        "type": "select_multiple wash_access",
        "name": "wash_access",
        "label": "Who can use it safely?",
        "relevant": ft("latrine", "bathing"),
        "appearance": "w2",
        **NONE_ALONE,
    },
    # Water.
    {
        "type": "select_one water_source",
        "name": "water_source",
        "label": "Water source",
        "relevant": ft("water"),
        "appearance": "w2",
    },
    other("water_source", "Specify the water source"),
    {
        "type": "select_multiple water_storage",
        "name": "water_storage",
        "label": "Water storage",
        "relevant": ft("water"),
        "appearance": "w2",
        **NONE_ALONE,
    },
    other("water_storage", "Specify the water storage", multi=True),
    {
        "type": "decimal",
        "name": "water_storage_m3",
        "label": "Storage volume (m³)",
        "hint": "All tanks at this point together. 1 m³ = 1,000 litres.",
        "relevant": (
            f"({ft('water')}) and ${{water_storage}} != '' and "
            "not(selected(${water_storage}, 'none'))"
        ),
        "appearance": "w2",
        **between(0, 5000, "m³"),
    },
    {
        "type": "select_one water_distribution",
        "name": "water_distribution",
        "label": "How is water handed out?",
        "relevant": ft("water"),
        "appearance": "w2",
    },
    other("water_distribution", "Specify how water is handed out"),
    {
        "type": "integer",
        "name": "tap_count",
        "label": "Number of taps",
        "hint": "All taps at this point, working or not.",
        "relevant": f"({ft('water')}) and ({picked('water_distribution', 'tap_stand', 'single_tap')})",
        "appearance": "w2",
        **between(0, 200, "taps"),
    },
    # Waste.
    {
        "type": "select_one waste_disposal",
        "name": "waste_disposal",
        "label": "Type of waste point",
        "relevant": ft("waste"),
        "appearance": "w2",
    },
    other("waste_disposal", "Specify the waste point"),
    # Shelter.
    {
        "type": "select_one shelter_type",
        "name": "shelter_type",
        "label": "Type of shelter",
        "hint": "Count similar shelters in this area in the count question above.",
        "relevant": ft("shelter"),
        "appearance": "w2",
    },
    other("shelter_type", "Specify the shelter type"),
    {
        "type": "integer",
        "name": "shelter_capacity",
        "label": "How many people can one shelter hold?",
        "relevant": ft("shelter"),
        "appearance": "w2",
        **between(0, 2000, "people"),
    },
    # Health.
    {
        "type": "select_one health_level",
        "name": "health_level",
        "label": "Level of care",
        "relevant": ft("health"),
        "appearance": "w2",
    },
    {
        "type": "select_one health_manager",
        "name": "health_manager",
        "label": "Who runs it?",
        "relevant": ft("health"),
        "appearance": "w2",
    },
    {
        "type": "text",
        "name": "health_ngo",
        "label": "Which NGO?",
        "relevant": f"({ft('health')}) and ({picked('health_manager', 'ngo_international', 'ngo_national')})",
        "appearance": "w2",
    },
    other("health_manager", "Specify who runs it"),
    {
        "type": "select_one health_cost",
        "name": "health_cost",
        "label": "Do patients pay?",
        "relevant": ft("health"),
        "appearance": "w2",
    },
    {
        "type": "select_multiple health_services",
        "name": "health_services",
        "label": "Services offered",
        "relevant": ft("health"),
        "appearance": "w2",
    },
    other("health_services", "Specify the other services", multi=True),
    {
        "type": "integer",
        "name": "observation_beds",
        "label": "Observation beds",
        "relevant": ft("health"),
        "appearance": "w2",
        **between(0, 500, "beds"),
    },
    {
        "type": "integer",
        "name": "inpatient_beds",
        "label": "Inpatient beds",
        "relevant": ft("health"),
        "appearance": "w2",
        **between(0, 2000, "beds"),
    },
    # Protection and site management.
    {
        "type": "select_multiple site_management",
        "name": "site_management",
        "label": "What happens here?",
        "relevant": ft("registration"),
        "appearance": "w2",
    },
    other("site_management", "Specify what else happens here", multi=True),
    {
        "type": "select_multiple space_users",
        "name": "space_users",
        "label": "Who is the space for?",
        "relevant": ft("cfs", "safe_space"),
        "appearance": "w2",
    },
    other("space_users", "Specify who the space is for", multi=True),
    {
        "type": "select_multiple space_setting",
        "name": "space_setting",
        "label": "What is the space like?",
        "relevant": ft("cfs", "safe_space"),
        "appearance": "w2",
    },
    other("space_setting", "Specify what the space is like", multi=True),
    # Food.
    {
        "type": "select_multiple distribution_items",
        "name": "distribution_items",
        "label": "What is distributed?",
        "relevant": ft("dist"),
        "appearance": "w2",
    },
    other("distribution_items", "Specify what is distributed", multi=True),
    # Logistics.
    {
        "type": "select_one storage_type",
        "name": "storage_type",
        "label": "Type of storage",
        "relevant": ft("storage"),
        "appearance": "w2",
    },
    other("storage_type", "Specify the storage type"),
    {
        "type": "decimal",
        "name": "storage_capacity_m3",
        "label": "Storage capacity (m³)",
        "hint": "Usable volume. A 10 × 24 m mobile storage unit is about 700 m³.",
        "relevant": ft("storage"),
        "appearance": "w2",
        **between(0, 50000, "m³"),
    },
    # Access.
    {
        "type": "select_one access_constraint",
        "name": "access_constraint",
        "label": "Type of constraint",
        "relevant": ft("choke"),
        "appearance": "w2",
    },
    other("access_constraint", "Specify the constraint"),
    {
        "type": "select_multiple road_hotspot",
        "name": "road_hotspot",
        "label": "What is on the road?",
        "relevant": f"({ft('choke')}) and ({picked('access_constraint', 'road')})",
        "appearance": "w2",
    },
    other("road_hotspot", "Specify what is on the road", multi=True),
    {
        "type": "select_multiple crossing_structure",
        "name": "crossing_structure",
        "label": "Which crossing?",
        "relevant": f"({ft('choke')}) and ({picked('access_constraint', 'crossing')})",
        "appearance": "w2",
    },
    other("crossing_structure", "Specify the crossing", multi=True),
    {
        "type": "select_multiple last_mile_services",
        "name": "last_mile_services",
        "label": "Which services can't be reached?",
        "relevant": f"({ft('choke')}) and ({picked('access_constraint', 'last_mile')})",
        "appearance": "w2",
    },
    other("last_mile_services", "Specify the services", multi=True),
    {
        "type": "text",
        "name": "access_description",
        "label": "Describe the constraint",
        "hint": "Which vehicles can pass, water depth, length, detour.",
        "relevant": ft("choke"),
    },
    # Energy and lighting.
    {
        "type": "select_one lighting_type",
        "name": "lighting_type",
        "label": "Type of lighting",
        "relevant": ft("lighting"),
        "appearance": "w2",
    },
    {
        "type": "select_one energy_source",
        "name": "lighting_power",
        "label": "Power source",
        "relevant": ft("lighting"),
        "appearance": "w2",
    },
    other("lighting_power", "Specify the power source"),
    {
        "type": "select_one energy_source",
        "name": "energy_source",
        "label": "Energy source",
        "relevant": ft("energy"),
        "appearance": "w2",
    },
    other("energy_source", "Specify the energy source"),
    {
        "type": "select_multiple energy_uses",
        "name": "energy_uses",
        "label": "What is the power used for?",
        "relevant": ft("energy"),
        "appearance": "w2",
    },
    other("energy_uses", "Specify the other uses", multi=True),
    # Where and what it looks like.
    {
        "type": "geopoint",
        "name": "location",
        "label": "Location",
        "hint": "Stand at the point and wait for the accuracy to drop below 10 m, or place the pin on the map.",
        "required": True,
        "appearance": "placement-map",
        "parameters": "capture-accuracy=5 warning-accuracy=10",
        "use": "map position",
    },
    {
        "type": "calculate",
        "name": "location_accuracy",
        "calculation": "if(${location} = '', '', selected-at(${location}, 3))",
        "notes": "GPS accuracy in metres (0 when the pin was placed by hand).",
    },
    {
        "type": "note",
        "name": "location_warning",
        "label": (
            "GPS accuracy is ${location_accuracy} m. Wait for a better fix, or place the pin "
            "by hand and choose \"Placed on the map\" below."
        ),
        "relevant": "${location_accuracy} != '' and number(${location_accuracy}) > 10",
    },
    {
        "type": "select_one location_method",
        "name": "location_method",
        "label": "How was the location taken?",
        "required": True,
        "default": "gps",
        "appearance": "w2",
        "use": "data-quality checks",
    },
    {
        "type": "image",
        "name": "photo",
        "label": "Photo",
        "hint": "Avoid faces, children and people in vulnerable situations. Skip the photo if it isn't safe or allowed.",
        "parameters": "max-pixels=1600",
        "use": "popup",
    },
    {
        "type": "image",
        "name": "photo_2",
        "label": "Second photo (optional)",
        "hint": "Avoid faces, children and people in vulnerable situations.",
        "parameters": "max-pixels=1600",
        "relevant": "${photo} != ''",
    },
    {
        "type": "image",
        "name": "photo_3",
        "label": "Third photo (optional)",
        "hint": "Avoid faces, children and people in vulnerable situations.",
        "parameters": "max-pixels=1600",
        "relevant": "${photo_2} != ''",
    },
    {"type": "end_group"},
    # Ungrouped, so page 2 and the brief read `note` with no change.
    {
        "type": "text",
        "name": "note",
        "label": "Comments",
        "hint": (
            "What the map should say about this point: what is wrong, who runs it, what is "
            "missing, other organisations present."
        ),
        "appearance": "multiline",
        "use": "popup, page 2, the brief",
    },
    {
        "type": "audio",
        "name": "note_audio",
        "label": "Voice note (optional)",
        "hint": "Instead of, or as well as, typing the comment.",
    },
    {
        "type": "note",
        "name": "next_note",
        "label": (
            "**Save and send this observation.** Then open a new form for the next point. "
            "The organisation, place and site carry over."
        ),
    },
]


# Choices. Each list: [(code, label)] or [(code, label, {filter column: value})].
CHOICES = {
    "org": [
        ("ndma", "National disaster management agency (NDMA / NEMA)"),
        ("iom", "IOM"),
        ("unhcr", "UNHCR"),
        ("un_agency", "Other UN agency"),
        ("ngo", "NGO"),
        ("undac", "UNDAC"),
        ("other", "Other"),
    ],
    # Placeholders. Countries replace them with COD-AB P-codes (see the adapt sheet).
    "level_1": [
        ("XX01", "Placeholder province 1"),
        ("XX02", "Placeholder province 2"),
    ],
    "level_2": [
        ("XX0101", "Placeholder district 1.1", {"level_1": "XX01"}),
        ("XX0102", "Placeholder district 1.2", {"level_1": "XX01"}),
        ("XX0201", "Placeholder district 2.1", {"level_1": "XX02"}),
        ("XX0202", "Placeholder district 2.2", {"level_1": "XX02"}),
    ],
    "site": [
        ("XX010101", "Placeholder camp A", {"level_2": "XX0101"}),
        ("XX010102", "Placeholder camp B", {"level_2": "XX0101"}),
        ("XX010201", "Placeholder collective centre C", {"level_2": "XX0102"}),
        ("XX020101", "Placeholder camp D", {"level_2": "XX0201"}),
        ("XX020201", "Placeholder collective centre E", {"level_2": "XX0202"}),
        ("other", "Other site (not in the list)"),
    ],
    "sector": [
        ("wash", "Water, sanitation and hygiene (WASH)"),
        ("shelter", "Shelter"),
        ("health", "Health"),
        ("protection", "Protection and site management"),
        ("food", "Food"),
        ("logistics", "Logistics"),
        ("access", "Access"),
        ("energy", "Energy and lighting"),
        ("environment", "Environment and hazards"),
        ("commerce", "Markets"),
        ("other", "Other"),
    ],
    "feature_type": [
        ("water", "Water point", {"sector": "wash"}),
        ("latrine", "Latrine", {"sector": "wash"}),
        ("bathing", "Bathing facility", {"sector": "wash"}),
        ("hand", "Handwashing station", {"sector": "wash"}),
        ("waste", "Waste point (bins, pit)", {"sector": "wash"}),
        ("shelter", "Shelter", {"sector": "shelter"}),
        ("health", "Health facility", {"sector": "health"}),
        ("cfs", "Child-friendly space", {"sector": "protection"}),
        ("safe_space", "Safe space (women and girls, other groups)", {"sector": "protection"}),
        ("registration", "Site management, registration, reception", {"sector": "protection"}),
        ("kitchen", "Kitchen / communal dining", {"sector": "food"}),
        ("dist", "Distribution point", {"sector": "food"}),
        ("storage", "Storage", {"sector": "logistics"}),
        ("landing", "Landing zone / helipad", {"sector": "logistics"}),
        ("gate", "Gate / entrance", {"sector": "logistics"}),
        ("choke", "Access constraint", {"sector": "access"}),
        ("lighting", "Lighting", {"sector": "energy"}),
        ("energy", "Energy point (power, charging)", {"sector": "energy"}),
        ("hazard", "Environmental hazard", {"sector": "environment"}),
        ("market", "Market", {"sector": "commerce"}),
        ("other", "Other", {"sector": "other"}),
    ],
    "status": [
        ("ok", "Working"),
        ("partial", "Partly working"),
        ("no", "Not working"),
        ("unknown", "Can't see"),
    ],
    "permanence": [
        ("emergency", "Emergency (first days)"),
        ("temporary", "Temporary"),
        ("semi_permanent", "Semi-permanent"),
        ("permanent", "Permanent"),
    ],
    "wash_features": [
        ("hand_washing", "Handwashing point"),
        ("light_inside", "Light inside"),
        ("light_outside", "Light outside"),
        ("lock_inside", "Lock on the inside"),
        ("none", "None of these"),
    ],
    "wash_access": [
        ("gender_separated", "Separate for women and men"),
        ("child_accessible", "Usable by children"),
        ("disability_accessible", "Usable by people with disabilities"),
        ("none", "None of these"),
    ],
    "water_source": [
        ("piped", "Piped network"),
        ("borehole", "Borehole"),
        ("well", "Well"),
        ("spring", "Spring"),
        ("rainwater", "Rainwater"),
        ("river", "River"),
        ("surface", "Other surface water (lake, pond)"),
        ("trucked", "Water trucking"),
        ("other", "Other"),
    ],
    "water_storage": [
        ("tank", "Tank"),
        ("bladder", "Bladder"),
        ("open_tank", "Open tank (onion tank, pool)"),
        ("none", "No storage"),
        ("other", "Other"),
    ],
    "water_distribution": [
        ("tap_stand", "Tap stand, several taps"),
        ("single_tap", "Single tap"),
        ("continuous_flow", "Constant flow, no tap"),
        ("other", "Other"),
    ],
    "waste_disposal": [
        ("bin", "Bin"),
        ("pit", "Pit"),
        ("pile", "Pile"),
        ("other", "Other"),
    ],
    "shelter_type": [
        ("emergency", "Emergency (plastic sheeting)"),
        ("tent", "Tent"),
        ("semi_permanent", "Semi-permanent (wood frame, corrugated sheet)"),
        ("permanent", "Permanent (built shelter, house)"),
        ("collective", "Collective (school, hall, church)"),
        ("other", "Other"),
    ],
    "health_level": [
        ("primary", "Primary care: basic, first-contact services"),
        ("secondary", "Secondary care: specialist care at hospital level"),
        ("tertiary", "Tertiary care: highly specialised hospital care"),
    ],
    "health_manager": [
        ("government", "Government"),
        ("ngo_international", "International NGO"),
        ("ngo_national", "National NGO"),
        ("other", "Other"),
    ],
    "health_cost": [
        ("free", "Free"),
        ("paid", "Paid"),
    ],
    "health_services": [
        ("consultation", "Consultations"),
        ("first_aid", "First aid, trauma"),
        ("vaccination", "Vaccination"),
        ("maternal", "Maternal and newborn care"),
        ("reproductive", "Sexual and reproductive health"),
        ("mental_health", "Mental health, psychosocial support"),
        ("nutrition", "Nutrition"),
        ("referral", "Referral to hospital"),
        ("other", "Other"),
    ],
    "site_management": [
        ("camp_management", "Camp management, coordination"),
        ("registration", "Registration"),
        ("reception", "Entry point, reception"),
        ("assembly_point", "Emergency assembly point"),
        ("information_point", "Information and display point"),
        ("help_desk", "Help desk, complaints"),
        ("other", "Other"),
    ],
    "space_users": [
        ("children", "Children"),
        ("women_girls", "Women and girls"),
        ("older_people", "Older people"),
        ("disability", "People with disabilities"),
        ("lgbtiq", "LGBTIQ+ people"),
        ("other", "Other"),
    ],
    "space_setting": [
        ("indoor", "Indoor"),
        ("outdoor", "Outdoor"),
        ("shade", "Shade"),
        ("play_area", "Play area"),
        ("seating", "Seating"),
        ("other", "Other"),
    ],
    "distribution_items": [
        ("meals", "Daily meals"),
        ("food_rations", "Food rations"),
        ("kits", "Kits (hygiene, shelter, household items)"),
        ("water", "Water"),
        ("cash", "Cash or vouchers"),
        ("other", "Other"),
    ],
    "storage_type": [
        ("permanent_building", "Permanent storage building"),
        ("msu", "Mobile storage unit (MSU)"),
        ("temp_building", "Building used as temporary storage"),
        ("msu_space", "Open space suitable for an MSU"),
        ("other", "Other"),
    ],
    "access_constraint": [
        ("road", "Road"),
        ("crossing", "Crossing (bridge, ford, culvert)"),
        ("last_mile", "Last mile to key services"),
        ("other", "Other"),
    ],
    "road_hotspot": [
        ("debris", "Debris"),
        ("landslide", "Landslide"),
        ("mud", "Mud"),
        ("flooding", "Flooding"),
        ("erosion", "Erosion"),
        ("crack", "Crack, seismic fault"),
        ("pothole", "Hole"),
        ("other", "Other"),
    ],
    "crossing_structure": [
        ("ford", "Ford"),
        ("culvert", "Culvert"),
        ("bridge", "Bridge"),
        ("other", "Other"),
    ],
    "last_mile_services": [
        ("health", "Health facility"),
        ("storage", "Storage"),
        ("site_management", "Site management"),
        ("distribution", "Distribution point"),
        ("other", "Other"),
    ],
    "lighting_type": [
        ("street", "Public or street lighting"),
        ("outdoor", "Lighting of an outdoor area"),
        ("shelter", "Lighting inside shelters"),
        ("individual", "Individual lamps, torches, candles"),
    ],
    "energy_source": [
        ("grid", "Grid"),
        ("generator", "Generator"),
        ("solar", "Solar"),
        ("battery", "Battery"),
        ("other", "Other"),
    ],
    "energy_uses": [
        ("charging", "Phone charging"),
        ("power_strip", "Extension lead, plug hub"),
        ("outdoor_lighting", "Outdoor lighting"),
        ("internet", "Internet, cyber café"),
        ("music", "Music, loudspeaker"),
        ("shop", "Shop"),
        ("other", "Other"),
    ],
    "location_method": [
        ("gps", "GPS, standing at the point"),
        ("manual", "Placed on the map"),
    ],
}


# The country adaptation checklist and the change rules (the `adapt` sheet).
ADAPT = [
    ("Rules", "Never rename or delete a question name or a choice code once data exists. Add only. Bump the version."),
    ("Rules", "Names are snake_case ASCII, 32 characters or fewer, unique across the form. `other` is the only code for \"other\"."),
    ("Rules", "Keep the paths in the codebook marked `contract`. The RISA dashboard maps the form by them, with no mapping step."),
    ("Rules", "Version is yyyymmddNN, e.g. 2026111201, then 2026111202 for a second change on the same day."),
    ("Settings", "form_id: keep `risa_obs`, or append the ISO3 code: `risa_obs_bhs`."),
    ("Settings", "form_title: add the country or operation, e.g. \"RISA site observation - Bahamas\"."),
    ("Settings", "version: set it to today's date and 01."),
    ("Places", "Replace the placeholder lists `level_1`, `level_2` and `site` on the choices sheet. Delete every XX row."),
    ("Places", "level_1 and level_2: use the COD-AB P-codes as `name` and the admin names as labels (data.humdata.org, search \"<country> subnational administrative boundaries\")."),
    ("Places", "Each level_2 row needs its parent P-code in the `level_1` column. Each site row needs its district P-code in the `level_2` column."),
    ("Places", "Sites: use the CCCM or DTM site code if there is one, else make one from the district P-code (BS0101 → BS010101). Keep the `other` row last, with no level_2."),
    ("Places", "Relabel `level_1` and `level_2` on the survey sheet if the country calls them something else (island, parish)."),
    ("Organisations", "Add the agencies working on site to the `org` list, e.g. `wfp`, `unicef`, `redcross`. Keep the seven existing codes."),
    ("Types", "Don't rename a feature_type code: they are the dashboard's map symbols. To add a type, add a row with its sector and tell the dashboard team."),
    ("Types", "To hide a type a country doesn't need, delete its row before the first deployment, or leave it."),
    ("Languages", "Add a column for each language next to the English one: `label::Español (es)`, `hint::Español (es)`, `constraint_message::Español (es)`, on both survey and choices."),
    ("Languages", "Every label, hint and constraint_message column must have a language suffix. Kobo refuses a form that mixes `label` with `label::English (en)`."),
    ("Languages", "Translate from English with AI, then have a native speaker review it. Set default_language to the language most collectors read."),
    ("Detail questions", "A country may add detail questions inside the `obs` group, with `relevant` on ${feature_type}. Put them after the existing ones."),
    ("Detail questions", "Each question with an `other` choice gets its own `<name>_other` text question."),
    ("Check", "Convert and check the file before deploying: kobo-mcp `convert_xlsform`, or upload it to a test project in Kobo."),
    ("Check", "Fill in one observation of each type you use, in KoboCollect and in Enketo, then look at the data table."),
    ("Deploy", "By hand: Kobo > New project > Upload an XLSForm > Deploy. Mid-mission changes: Replace form, then Redeploy (data is kept)."),
    ("Deploy", "With kobo-mcp: `deploy_form` with `xlsx_base64` (the file), or `clone_project` from an existing RISA project and edit it."),
    ("Server", "Pick the server for data residency: kf.kobotoolbox.org (global) or eu.kobotoolbox.org (EU). Use an organisation account, one account per collector, no shared logins."),
]


# Legacy codes: the Mozambique/Venezuela `infra_services` (47, the same in both forms)
# and Michael's draft (18). (legacy code, legacy label, feature_type, detail field,
# detail value, note). The sector follows from feature_type.
LEGACY_MZ_VE = [
    ("wash_latrine_fixed", "Latrines - Fixed/Permanent", "latrine", "permanence", "permanent", ""),
    ("wash_latrine_pit", "Latrines - Pit", "latrine", "", "", "Pit latrine; no detail code."),
    ("wash_latrine_emergency", "Latrines - Emergency/Temporary", "latrine", "permanence", "emergency", "Use temporary if it was past the first days."),
    ("wash_latrine_gender_separated", "Latrines - Gender Separated", "latrine", "wash_access", "gender_separated", ""),
    ("wash_latrine_accessible", "Latrines - Accessible (Disability/Elderly)", "latrine", "wash_access", "disability_accessible", ""),
    ("wash_latrine_child_friendly", "Latrines - Child-Friendly (Reduced Height)", "latrine", "wash_access", "child_accessible", ""),
    ("wash_water_source_improved", "Water Source - Improved (Well/Borehole/Spring)", "water", "", "", "One of borehole, well, spring; not known which."),
    ("wash_water_source_unimproved", "Water Source - Unimproved (Surface/Unprotected)", "water", "water_source", "surface", ""),
    ("wash_water_distribution", "Water Distribution System", "water", "", "", ""),
    ("wash_water_storage_elevated", "Water Storage - Elevated Tank", "water", "water_storage", "tank", ""),
    ("wash_water_storage_ground", "Water Storage - Ground-Level/Underground", "water", "water_storage", "tank", ""),
    ("wash_water_tap_stand", "Water Distribution - Tap stand", "water", "water_distribution", "tap_stand", ""),
    ("wash_bathing", "Bathing facility", "bathing", "", "", ""),
    ("wash_waste_bin", "Waste bin", "waste", "waste_disposal", "bin", ""),
    ("prot_site_management", "Site management", "registration", "site_management", "camp_management", ""),
    ("prot_safe_space_general", "Safe Space - General", "safe_space", "", "", ""),
    ("prot_safe_space_women", "Safe Space - Women/Girls Focused", "safe_space", "space_users", "women_girls", ""),
    ("prot_safe_space_children", "Safe Space - Children/Youth Focused", "cfs", "space_users", "children", ""),
    ("prot_safe_space_persons_with_disabilities", "Safe Space - Persons with Disabilities", "safe_space", "space_users", "disability", ""),
    ("prot_safe_space_lgbtq", "Safe Space - LGBTQ+ Inclusive", "safe_space", "space_users", "lgbtiq", ""),
    ("prot_psosocial", "Psychosocial Support/Recreation Space", "safe_space", "", "", "Psychosocial support; say so in the note."),
    ("prot_women_friendly_facilities", "Women-Friendly Facilities (Bathing/Changing Spaces)", "bathing", "wash_access", "gender_separated", ""),
    ("prot_childcare_friendly_space", "Child-Friendly/Childcare Space", "cfs", "space_users", "children", ""),
    ("prot_community_kitchen", "Communal Kitchen", "kitchen", "", "", ""),
    ("prot_distribution_site", "Distribution Site", "dist", "", "", ""),
    ("prot_entry_point", "Entry Point/Reception Area", "registration", "site_management", "reception", "A gate with no reception desk is `gate`."),
    ("hlth_health_clinic", "Health Facility - Clinic", "health", "health_level", "primary", ""),
    ("hlth_health_post", "Health Facility - Health Post", "health", "health_level", "primary", ""),
    ("hlth_health_referral", "Health Facility - Referral Hospital", "health", "health_level", "secondary", "Tertiary if it is a specialised hospital."),
    ("hlth_reproductive_health", "Reproductive Health Services", "health", "health_services", "reproductive", ""),
    ("hlth_mental_health", "Mental Health/Psychosocial Services", "health", "health_services", "mental_health", ""),
    ("shlt_shelter_transitional", "Shelter - Transitional (Semi-Permanent)", "shelter", "shelter_type", "semi_permanent", "Venezuela tagged it health."),
    ("shlt_shelter_permanent", "Shelter - Permanent Structure", "shelter", "shelter_type", "permanent", "Venezuela tagged it health."),
    ("shlt_shelter_collective", "Shelter - Collective (School/Hall)", "shelter", "shelter_type", "collective", "Venezuela tagged it health."),
    ("wash_lighting_solar", "Lighting - Solar", "lighting", "lighting_power", "solar", ""),
    ("wash_lighting_camp", "Lighting - General / camp / path / street", "lighting", "lighting_type", "street", ""),
    ("wash_lighting_generator", "Lighting - Generator/Fuel-Based", "lighting", "lighting_power", "generator", ""),
    ("wash_lighting_manual", "Lighting - Manual (Lanterns/Candles)", "lighting", "lighting_type", "individual", ""),
    ("storage_facility", "Storage Facility", "storage", "", "", ""),
    ("storage_building", "Storage - Building Suitable for Stock", "storage", "storage_type", "permanent_building", ""),
    ("storage_msu_space", "Storage - Empty Space Suitable for MSU", "storage", "storage_type", "msu_space", ""),
    ("access_constraint", "Access Constraint (add comment)", "choke", "", "", "Venezuela tagged it storage."),
    ("helipad", "Helipad (or Suitable Location)", "landing", "", "", "Venezuela tagged it access."),
    ("environmental_hazard", "Environmental Hazard (add comment)", "hazard", "", "", ""),
    ("energy_available", "Energy Available (source and distribution in comment)", "energy", "", "", ""),
    ("marketplace", "Marketplace (add comment)", "market", "", "", ""),
    ("other_infrastructure", "Other Infrastructure", "other", "", "", ""),
]

LEGACY_MICHAEL = [
    ("prot_site_management", "Site management", "registration", "", "", ""),
    ("wash_latrine", "Latrine", "latrine", "", "", ""),
    ("wash_bathing", "Bathing facility", "bathing", "", "", ""),
    ("wash_water_source", "Water Source / storage / distribution", "water", "", "", ""),
    ("wash_waste", "Waste management", "waste", "", "", ""),
    ("shlt_shelter", "Shelter", "shelter", "", "", ""),
    ("prot_friendly_facilities", "Friendly Spaces", "safe_space", "", "", "cfs when friendly_space is only `child`."),
    ("hlth_health", "Health Facility", "health", "", "", ""),
    ("prot_community_kitchen", "Communal Kitchen", "kitchen", "", "", ""),
    ("prot_distribution_site", "Distribution Site", "dist", "", "", ""),
    ("energy_available", "Energy", "energy", "", "", ""),
    ("wash_lighting", "Lighting", "lighting", "", "", ""),
    ("storage_facility", "Storage Facility", "storage", "", "", ""),
    ("access_constraint", "Access Constraint (add comment)", "choke", "", "", ""),
    ("helipad", "Helipad (or Suitable Location)", "landing", "", "", ""),
    ("environmental_hazard", "Environmental Hazard (add comment)", "hazard", "", "", ""),
    ("marketplace", "Marketplace (add comment)", "market", "", "", ""),
    ("other_infrastructure", "Other Infrastructure", "other", "", "", ""),
]

# Michael's detail questions → template names, for the codebook's history note.
MICHAEL_RENAMES = [
    ("type", "permanence"),
    ("extra", "wash_features"),
    ("friendly_acces", "wash_access"),
    ("how_many", "count"),
    ("water_source", "water_source"),
    ("water_storage", "water_storage"),
    ("storage_capacity (water)", "water_storage_m3"),
    ("water_distribution", "water_distribution"),
    ("number_of_tap", "tap_count"),
    ("waste_management", "waste_disposal"),
    ("shelter_type", "shelter_type"),
    ("shelter_capacity", "shelter_capacity"),
    ("number_of_similar_shelter_in_this_area", "count"),
    ("health_facility", "health_level"),
    ("health_facility_management", "health_manager"),
    ("which_ngo_", "health_ngo"),
    ("services_cost", "health_cost"),
    ("health_facility_services (text)", "health_services (select_multiple)"),
    ("observation_bed", "observation_beds"),
    ("hospitalisation_bed", "inpatient_beds"),
    ("site_management", "site_management"),
    ("friendly_space", "space_users"),
    ("type_of_space (text)", "space_setting (select_multiple)"),
    ("distribution_point", "distribution_items"),
    ("Storage_facility", "storage_type"),
    ("storage_capacity (storage)", "storage_capacity_m3"),
    ("acces_constrain", "access_constraint"),
    ("road_hotspot", "road_hotspot"),
    ("crossing_structure", "crossing_structure"),
    ("last_mile_strategy_services", "last_mile_services"),
    ("describe_the_constraint", "access_description"),
    ("lightning", "lighting_type"),
    ("energy_source", "energy_source"),
    ("energy_outcom", "energy_uses"),
    ("specify_other", "one <name>_other per question"),
    ("comments", "note (ungrouped)"),
    ("comments_audio", "note_audio (ungrouped)"),
]

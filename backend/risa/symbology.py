"""RISA symbology from symbology/risa.json, and mapping free values to RISA types and statuses."""

import json
import re
import unicodedata
from functools import cache

from django.conf import settings


@cache
def symbology() -> dict:
    return json.loads(settings.SYMBOLOGY_FILE.read_text())


def _norm(value) -> str:
    s = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower().strip()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


@cache
def _lookup(kind: str) -> dict[str, str]:
    out = {}
    for key, words in symbology()["synonyms"][kind].items():
        out[_norm(key)] = key
        for w in words:
            out[_norm(w)] = key
    return out


def match_status(value) -> str:
    """'Partly working' -> 'partial'. Unrecognised or empty -> '' (shown as not assessed)."""
    if value in (None, ""):
        return ""
    return _lookup("status").get(_norm(value), "")


def match_type(value) -> str:
    if value in (None, ""):
        return ""
    n = _norm(value)
    table = _lookup("type")
    if n in table:
        return table[n]
    # 'water_point_02', 'letrinas_bloque_a': try each word
    for part in n.split("_"):
        if part in table:
            return table[part]
    return ""


STATUS_KEYS = ("risa_status", "status", "estado", "statut", "condition", "functionality", "functional")
TYPE_KEYS = ("risa_type", "type", "tipo", "category", "categoria", "service", "servicio", "kind")
LABEL_KEYS = ("label", "name", "nombre", "nom", "title", "id", "code")


def classify(props: dict) -> tuple[str, str, str]:
    """Best-effort RISA type, status and label from an uploaded feature's attributes."""
    lower = {str(k).lower(): v for k, v in props.items()}

    def first(keys, fn=None):
        for k in keys:
            v = lower.get(k)
            if v not in (None, ""):
                if fn is None:
                    return str(v)
                m = fn(v)
                if m:
                    return m
        return ""

    return first(TYPE_KEYS, match_type), first(STATUS_KEYS, match_status), first(LABEL_KEYS)[:200]

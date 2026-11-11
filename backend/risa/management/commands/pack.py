"""Offline basemaps (risa/packs.py).

    python manage.py pack build Haiti --country HTI                  # online, into this instance
    python manage.py pack build Haiti --country HTI --out /media/usb/pack
    python manage.py pack build Delmas --bbox=-72.36,18.53,-72.29,18.58   # "=": a west longitude starts with -
    python manage.py pack load /media/usb/pack                       # offline
    python manage.py pack list
"""

from django.core.management.base import BaseCommand, CommandError

from risa import packs


def bbox(value: str) -> list[float]:
    try:
        parts = [float(x) for x in value.split(",")]
    except ValueError:
        parts = []
    if len(parts) != 4:
        raise ValueError("west,south,east,north")
    return parts


class Command(BaseCommand):
    help = "Build (online) or load (offline) a pack of offline basemaps"

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="action", required=True)
        b = sub.add_parser("build", help="cut an area out of Protomaps' OpenStreetMap build (online)")
        b.add_argument("name", help='names the basemap: "Offline: <name>"')
        b.add_argument("--country", action="append", default=[], help="ISO 3166 alpha-3, repeatable")
        b.add_argument("--bbox", type=bbox, help="west,south,east,north in degrees, as --bbox=w,s,e,n")
        b.add_argument("--maxzoom", type=int, default=15, help="deepest zoom (15: streets and buildings)")
        b.add_argument("--out", help="write a pack folder here, to load elsewhere; else into this instance")
        b.add_argument("--source", help="a Protomaps build URL or local .pmtiles, instead of the newest build")
        lo = sub.add_parser("load", help="copy a pack folder's basemaps into this instance")
        lo.add_argument("folder")
        sub.add_parser("list", help="the offline basemaps on this instance")

    def handle(self, *args, **opts):
        try:
            if opts["action"] == "build":
                m = packs.build(opts["name"], [c.upper() for c in opts["country"]], opts["bbox"], opts["maxzoom"],
                                opts["out"], opts["source"])
                size = sum(f["size"] for f in m["files"].values())
                where = opts["out"] or "this instance"
                self.stdout.write(f"{opts['name']}: {size / 1024**2:.1f} MB from {m['source']}, to zoom "
                                  f"{m['maxzoom']}, in {where}")
            elif opts["action"] == "load":
                for rel in packs.load(opts["folder"]):
                    self.stdout.write(f"loaded {rel}")
            else:
                for name, size in packs.installed():
                    self.stdout.write(f"{size / 1024**2:8.1f} MB  {name}")
        except packs.PackError as e:
            raise CommandError(str(e)) from None

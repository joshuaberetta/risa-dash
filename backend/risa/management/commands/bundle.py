"""Export or import a response bundle from the command line, e.g. to or from a USB drive.

    python manage.py bundle export <response-slug> /media/usb/venezuela.risa.zip [--no-imagery]
    python manage.py bundle import /media/usb/venezuela.risa.zip

An import here needs no edit key: whoever runs commands on the server can change it anyway.
"""

import json

from django.core.management.base import BaseCommand, CommandError

from risa import bundles
from risa.models import Response


class Command(BaseCommand):
    help = "Export or import a response bundle (a zip with the response's data, imagery and PDFs)"

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="action", required=True)
        ex = sub.add_parser("export")
        ex.add_argument("response", help="the response's slug")
        ex.add_argument("path")
        ex.add_argument("--no-imagery", action="store_true", help="leave out orthomosaics and satellite scenes")
        ex.add_argument("--originals", action="store_true", help="also the original imagery uploads")
        im = sub.add_parser("import")
        im.add_argument("path")

    def handle(self, *args, **opts):
        if opts["action"] == "export":
            r = Response.objects.filter(slug=opts["response"]).first()
            if not r:
                raise CommandError(f"No response {opts['response']!r}")
            m = bundles.export_bundle(r, opts["path"], imagery=not opts["no_imagery"], originals=opts["originals"])
            size = sum(f["size"] for f in m["files"].values())
            self.stdout.write(f"{opts['path']}: {len(m['files'])} files, {size / 1024**2:.1f} MB")
        else:
            try:
                result = bundles.import_bundle(opts["path"], force=True)
            except bundles.BundleError as e:
                raise CommandError(str(e)) from None
            self.stdout.write(json.dumps(result, indent=1))

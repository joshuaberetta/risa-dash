"""Score an analysis layer against reference shelters (risa/evaluation.py).

    python manage.py evaluate <analysis-layer-id> <reference-layer-id> [--bbox=w,s,e,n] [--json]
"""

import json

from django.core.management.base import BaseCommand, CommandError

from risa import evaluation
from risa.models import Layer


class Command(BaseCommand):
    help = "Precision, recall and F1 of a detection against reference shelters"

    def add_arguments(self, parser):
        parser.add_argument("layer")
        parser.add_argument("reference")
        parser.add_argument("--bbox", type=lambda v: [float(x) for x in v.split(",")], help="west,south,east,north")
        parser.add_argument("--json", action="store_true")

    def handle(self, *args, **o):
        try:
            r = evaluation.evaluate(Layer.objects.get(id=o["layer"]), Layer.objects.get(id=o["reference"]), bbox=o["bbox"])
        except (Layer.DoesNotExist, ValueError) as e:
            raise CommandError(str(e)) from None
        if o["json"]:
            self.stdout.write(json.dumps(r, indent=1))
            return
        self.stdout.write(f"{r['model']} against {r['reference_count']} reference {r['class']}s ({r['reference_kind']}), "
                          f"{r['area_m2']} m²")
        self.stdout.write(" conf≥  found  right  precision  recall    F1  count err  wrong & confident")
        for c in r["curve"]:
            self.stdout.write(f" {c['min_confidence']:4.2f}  {c['detected']:5}  {c['matched']:5}  {c['precision']:9.2f}"
                              f"  {c['recall']:6.2f}  {c['f1']:4.2f}  {c['count_error']:+9.0%}  {c['wrong_confident']:17.0%}")

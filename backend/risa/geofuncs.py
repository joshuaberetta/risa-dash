from django.db.models import CharField, Func


class GeometryType(Func):
    """PostGIS GeometryType(): 'POINT', 'MULTIPOLYGON', ..."""

    function = "GeometryType"
    output_field = CharField()

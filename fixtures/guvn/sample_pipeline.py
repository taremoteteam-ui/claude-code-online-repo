"""A fully GUVN-annotated sample pipeline, used to demonstrate the tracer.

It is a small, realistic place-discovery flow whose units declare their consumed
and produced Globally Unique Names. The tracer (primitives/guvn.py) reads these
declarations and builds a deterministic code map WITHOUT reading any function
body - the names alone determine the wiring. Note the two producers of
`geo.records.entity_record_set`: a GeoJSON path and a CSV path emit the SAME
substitutable contract, so it is classified as a multi-path artifact (the seam
where GUVN meets multiple-path development).

This is a fixture (candidate / illustrative); the units return trivial values.
"""

from __future__ import annotations

from primitives.guvn import unit


@unit("geo.ingest.parse_geojson",
      consumes=["geo.source.geojson_document"],
      produces=["geo.features.point_feature_collection"],
      effects=["none"])
def parse_geojson(doc):
    return {"features": []}


@unit("geo.transform.features_to_records",
      consumes=["geo.features.point_feature_collection"],
      produces=["geo.records.entity_record_set"],
      effects=["none"])
def features_to_records(fc):
    return {"records": []}


@unit("geo.ingest.parse_csv_places",
      consumes=["geo.source.csv_document"],
      produces=["geo.records.entity_record_set"],   # same contract as the geojson path
      effects=["none"])
def parse_csv_places(csv):
    return {"records": []}


@unit("geo.index.build_place_index",
      consumes=["geo.records.entity_record_set"],
      produces=["geo.index.place_index"],
      effects=["none"])
def build_place_index(records):
    return {"index": {}}


@unit("geo.query.nearest_places",
      consumes=["geo.index.place_index", "geo.query.location_point"],
      produces=["geo.result.ranked_place_list"],
      effects=["none"])
def nearest_places(index, point):
    return {"ranked": []}

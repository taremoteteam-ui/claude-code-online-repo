"""Map artifact primitive for the place-discovery-geospatial lane.

:func:`map_artifact_generation` renders a self-contained 600x600 SVG map
(one boundary polygon plus classed points) entirely in memory and returns
it as a string with an ArtifactRef. The primitive performs NO I/O -- the
harness decides whether/where to persist the SVG -- so effects_observed
is ["none"].

Stdlib only. Deterministic: identical payloads yield byte-identical SVG.
"""

from __future__ import annotations

import hashlib

from primitives.core import ArtifactRef, PrimitiveOutcome, ProofResult

WIDTH = 600
HEIGHT = 600
# Inner plotting area leaves room for the title (top) and the legend +
# attribution (bottom) while keeping every rendered mark inside the viewport.
PLOT_X0 = 25.0
PLOT_X1 = 575.0
PLOT_Y0 = 60.0
PLOT_Y1 = 520.0

POINT_STYLE = {
    "covered": {"fill": "#2e7d32", "label": "covered"},
    "uncovered": {"fill": "#c62828", "label": "uncovered"},
    "facility": {"fill": "#1a237e", "label": "facility"},
}


def _escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _fmt(value: float) -> str:
    """Fixed-precision coordinate formatting keeps output deterministic."""
    return f"{value:.2f}"


def map_artifact_generation(payload: dict) -> PrimitiveOutcome:
    """Render a self-contained SVG map artifact.

    payload:
      title:       str
      boundary:    one GeoJSON Feature with Polygon geometry
      points:      [{"id", "lat", "lon",
                     "label_class": "covered"|"uncovered"|"facility"}, ...]
      attribution: str
    """
    errors: list[str] = []
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    title = payload.get("title")
    boundary = payload.get("boundary")
    points = payload.get("points")
    attribution = payload.get("attribution")
    if not isinstance(title, str) or not title.strip():
        errors.append("'title' must be a non-empty string")
    if not isinstance(attribution, str) or not attribution.strip():
        errors.append("'attribution' must be a non-empty string")
    rings: list = []
    if (
        not isinstance(boundary, dict)
        or boundary.get("type") != "Feature"
        or not isinstance(boundary.get("geometry"), dict)
        or boundary["geometry"].get("type") != "Polygon"
    ):
        errors.append("'boundary' must be a GeoJSON Feature with Polygon geometry")
    else:
        rings = boundary["geometry"].get("coordinates") or []
        if not rings or not rings[0]:
            errors.append("boundary polygon has no coordinates")
    if not isinstance(points, list):
        errors.append("'points' must be a list")
        points = []
    for idx, row in enumerate(points):
        if not isinstance(row, dict):
            errors.append(f"points[{idx}] is not an object")
            continue
        if not isinstance(row.get("id"), str) or not row.get("id"):
            errors.append(f"points[{idx}] missing string 'id'")
        for key in ("lat", "lon"):
            val = row.get(key)
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                errors.append(f"points[{idx}] missing numeric '{key}'")
        if row.get("label_class") not in POINT_STYLE:
            errors.append(
                f"points[{idx}] label_class must be one of "
                + "/".join(sorted(POINT_STYLE))
            )
    if errors:
        raise ValueError("schema_validation failed: " + "; ".join(errors))

    # Bounding box over boundary rings + points, with 5% padding per axis.
    lons = [float(pos[0]) for ring in rings for pos in ring]
    lats = [float(pos[1]) for ring in rings for pos in ring]
    lons += [float(p["lon"]) for p in points]
    lats += [float(p["lat"]) for p in points]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)
    lon_span = (max_lon - min_lon) or 0.01
    lat_span = (max_lat - min_lat) or 0.01
    min_lon -= 0.05 * lon_span
    max_lon += 0.05 * lon_span
    min_lat -= 0.05 * lat_span
    max_lat += 0.05 * lat_span
    lon_span = max_lon - min_lon
    lat_span = max_lat - min_lat

    def project(lon: float, lat: float) -> tuple[float, float]:
        px = PLOT_X0 + (lon - min_lon) / lon_span * (PLOT_X1 - PLOT_X0)
        py = PLOT_Y1 - (lat - min_lat) / lat_span * (PLOT_Y1 - PLOT_Y0)  # y inverted
        return px, py

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
        f'height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">'
    )
    parts.append(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#fafafa"/>')

    # Boundary polygon outline (all rings; holes render as inner outlines).
    path_cmds = []
    for ring in rings:
        cmds = []
        for i, pos in enumerate(ring):
            px, py = project(float(pos[0]), float(pos[1]))
            cmds.append(f"{'M' if i == 0 else 'L'} {_fmt(px)} {_fmt(py)}")
        cmds.append("Z")
        path_cmds.append(" ".join(cmds))
    parts.append(
        f'<path class="boundary" d="{" ".join(path_cmds)}" fill="#e8eef7" '
        'fill-opacity="0.6" stroke="#33415c" stroke-width="1.5"/>'
    )

    # Points. Facilities render as squares; covered/uncovered as circles
    # with distinct fills. All real marks carry class "pt" so the nonblank
    # proof does not count legend swatches.
    rendered_coords: list[tuple[float, float]] = []
    points_rendered = 0
    for row in points:
        px, py = project(float(row["lon"]), float(row["lat"]))
        rendered_coords.append((px, py))
        cls = row["label_class"]
        fill = POINT_STYLE[cls]["fill"]
        pid = _escape_xml(row["id"])
        if cls == "facility":
            half = 6.0
            parts.append(
                f'<rect class="pt pt-facility" data-id="{pid}" '
                f'x="{_fmt(px - half)}" y="{_fmt(py - half)}" '
                f'width="{_fmt(2 * half)}" height="{_fmt(2 * half)}" '
                f'fill="{fill}" stroke="#ffffff" stroke-width="1"/>'
            )
        else:
            parts.append(
                f'<circle class="pt pt-{cls}" data-id="{pid}" '
                f'cx="{_fmt(px)}" cy="{_fmt(py)}" r="4.5" '
                f'fill="{fill}" stroke="#ffffff" stroke-width="1"/>'
            )
        points_rendered += 1

    # Title (top) and attribution (bottom).
    parts.append(
        f'<text class="map-title" x="{WIDTH // 2}" y="32" text-anchor="middle" '
        'font-family="sans-serif" font-size="18" fill="#1c2431">'
        f"{_escape_xml(title)}</text>"
    )
    parts.append(
        f'<text class="map-attribution" x="{WIDTH // 2}" y="{HEIGHT - 12}" '
        'text-anchor="middle" font-family="sans-serif" font-size="10" '
        f'fill="#5b6470">{_escape_xml(attribution)}</text>'
    )

    # Simple legend (bottom-left, above attribution). Swatches use class
    # "legend-mark", not "pt".
    legend_y = HEIGHT - 60
    parts.append(
        f'<rect x="20" y="{legend_y - 14}" width="264" height="24" '
        'fill="#ffffff" fill-opacity="0.85" stroke="#c5ccd6" stroke-width="0.5"/>'
    )
    lx = 30.0
    for cls in ("covered", "uncovered", "facility"):
        fill = POINT_STYLE[cls]["fill"]
        if cls == "facility":
            parts.append(
                f'<rect class="legend-mark" x="{_fmt(lx - 4)}" '
                f'y="{legend_y - 6}" width="8" height="8" fill="{fill}"/>'
            )
        else:
            parts.append(
                f'<circle class="legend-mark" cx="{_fmt(lx)}" '
                f'cy="{legend_y - 2}" r="4" fill="{fill}"/>'
            )
        parts.append(
            f'<text x="{_fmt(lx + 8)}" y="{legend_y + 2}" '
            'font-family="sans-serif" font-size="10" fill="#1c2431">'
            f"{POINT_STYLE[cls]['label']}</text>"
        )
        lx += 88.0
    parts.append("</svg>")
    svg = "\n".join(parts)

    content_sha256 = hashlib.sha256(svg.encode("utf-8")).hexdigest()
    output = {
        "svg": svg,
        "artifact_stats": {
            "points_rendered": points_rendered,
            "width": WIDTH,
            "height": HEIGHT,
        },
    }

    has_point_mark = ('<circle class="pt' in svg) or ('<rect class="pt' in svg)
    has_boundary_path = '<path class="boundary"' in svg
    coords_in_viewport = all(
        0.0 <= px <= WIDTH and 0.0 <= py <= HEIGHT for px, py in rendered_coords
    )
    proofs = [
        ProofResult(
            "nonblank_map_artifact_test",
            has_point_mark and has_boundary_path,
            f"boundary path present; {points_rendered} point marks rendered",
        ),
        ProofResult(
            "title_labeled",
            _escape_xml(title) in svg and 'class="map-title"' in svg,
            "title text element present",
        ),
        ProofResult(
            "attribution_present",
            _escape_xml(attribution) in svg and 'class="map-attribution"' in svg,
            "attribution text element present",
        ),
        ProofResult(
            "viewbox_valid",
            coords_in_viewport,
            f"all {len(rendered_coords)} projected point coordinates inside "
            f"0..{WIDTH} x 0..{HEIGHT} viewport",
        ),
    ]
    return PrimitiveOutcome(
        output=output,
        effects_observed=["none"],
        proof_results=proofs,
        artifacts=[ArtifactRef(artifact_type="svg_map", content_sha256=content_sha256)],
    )

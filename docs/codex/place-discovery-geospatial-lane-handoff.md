# Place Discovery + Geospatial Lane Handoff

Last updated: 2026-07-02

Audience: builders picking up the `place-discovery-geospatial` primitive lane of the
Primitive Atlas -- adapter authors, benchmark harness engineers, and pack maintainers.

Status: candidate lane handoff; all generated rows are candidate=true /
serves_truth=false; no metric below is measured unless produced by local scripts and
manifests.

---

## 1. Core thesis

A "place" answer that is just a list of names and pins is not a deliverable. This lane
treats every place (clinic, health center, training provider, facility, POI) as an
**evidence-backed entity**, meaning every emitted record carries:

- **Provenance** -- which source surface produced it, which snapshot, which fetch plan,
  which extraction schema, and a hash chain back to the raw payload.
- **Geocoding confidence** -- how the coordinate was obtained (source-supplied,
  address-geocoded, centroid-fallback), through which policy-approved route, and at
  what stated confidence tier.
- **Freshness** -- when the source published, when we snapshotted, and whether the
  portal change monitor has seen drift since.
- **Coverage gaps** -- what the source explicitly does not cover (state, program,
  facility type) so absence of a record is distinguishable from absence of coverage.
- **Uncertainty** -- unresolved dedupe clusters, low-confidence geocodes, stale
  vintages, and conflicting attributes are surfaced in an UncertaintyReport, never
  silently dropped.
- **Catchment signals** -- spatial context (nearest-facility distance, isochrone
  membership, boundary assignment) computed with a recorded engine, parameters, and
  boundary vintage.

The lane's value proposition is that a route through these primitives produces answers
a downstream consumer can audit claim-by-claim, while a raw model or generic scraper
produces answers that must be trusted blind.

## 2. Canonical visible edge

```
AreaOfInterest + DirectedQuestion + SourcePolicy + ExtractionSchema
  -> EvidenceBackedAnswer + SourceBundle + SpatialArtifacts + UncertaintyReport
```

The caller supplies a geography (AOI), a concrete question, the policy envelope
(allowed endpoints, rate limits, attribution obligations), and the target record
shape. The lane returns an answer whose every claim cites the SourceBundle, plus
spatial artifacts (GeoJSON, maps, tables) and an explicit uncertainty account.

### Hidden internal edges

The visible edge decomposes into this internal chain. Each hop is a typed edge that a
primitive (Section 4) owns:

```
DirectedQuestion
  -> SourceSurfacePlan          (which surfaces, in what order, under what policy)
  -> APIOrBrowseFetchPlan       (concrete requests: endpoints, params, paging, limits)
  -> SourceSnapshots            (raw payloads, hashed, timestamped, policy-logged)
  -> TypedRecords               (schema-validated rows per extraction schema)
  -> NormalizedEntities         (canonical names, addresses, phones, coordinates)
  -> DedupeClusters             (cross-source identity resolution with match evidence)
  -> SpatialAnalysisReceipt     (joins, distances, isochrones: engine + params + vintage)
  -> MapOrDashboardArtifact     (labeled, attributed, non-blank renderings)
  -> EvidenceBackedAnswer       (claims wired to snapshots, gaps, and uncertainty)
```

Rules for the chain:

- No hop may be skipped when its output is cited. An answer that mentions a distance
  must trace to a SpatialAnalysisReceipt; a merged entity must trace to a
  DedupeClusters entry.
- Every hop is replayable: SourceSnapshots plus the recorded plans regenerate
  TypedRecords deterministically.
- Policy checks (SourcePolicy) gate the SourceSurfacePlan -> APIOrBrowseFetchPlan hop
  and the geocoding step; a plan that violates policy fails closed.

## 3. The five source lanes

Official-first ordering matters everywhere: government/registry surfaces define the
authoritative universe (what should exist), and open-map surfaces enrich and
cross-check it (what is observably there). Reversing the order produces registries
polluted by unverifiable POIs and makes coverage-gap claims impossible to defend.

### 3.1 Health facilities (official-first core)

Key surfaces: `src:hrsa.health_center_sites`, `src:hrsa.find_a_health_center`,
`src:cms.nppes_npi_registry`, `src:cms.provider_data_catalog`,
`src:hifld.health_facility_layers`, `src:healthsites.global_registry`,
`src:who.ghfd`, `src:hdx.health_facility_datasets`.

HRSA defines the funded health-center universe; NPPES anchors provider/organization
identity via NPI; HIFLD and CMS catalogs extend facility types; Healthsites, WHO GHFD,
and HDX cover international geographies. Outputs are directory/access/planning
records only -- never patient-level data.

### 3.2 Workforce and training providers

Key surfaces: `src:careeronestop.training_providers_api`,
`src:dol.state_etpl_directories`, `src:ed.college_scorecard_api`, `src:nces.ipeds`,
`src:dol.registered_apprenticeship_rapids`.

CareerOneStop and state ETPL directories list eligible training providers; College
Scorecard and IPEDS supply institution/program structure; RAPIDS covers registered
apprenticeship. These surfaces disagree on names and campuses constantly, which is why
the dedupe primitive is load-bearing here.

### 3.3 Open maps and addresses (enrichment and cross-check)

Key surfaces: `src:osm.overpass_api`, `src:osm.nominatim_geocoder`,
`src:osm.planet_extracts`, `src:overture.maps_places`,
`src:openaddresses.global_collection`, `src:geonames.gazetteer`,
`src:naturalearth.basemap_vectors`.

OSM/Overture/OpenAddresses supply POIs, addresses, and basemap context. Public
Overpass and Nominatim endpoints have strict usage policies (Section 8); scaled use
must go through planet extracts, Overture releases, or self-hosted instances. All OSM
derivatives carry ODbL attribution obligations that the attribution receipt enforces.

### 3.4 Open-data portals and boundaries

Key surfaces: `src:datagov.ckan_api`, `src:socrata.soda_api`,
`src:esri.arcgis_hub`, `src:esri.arcgis_featureserver`, `src:ogc.api_records`,
`src:census.tiger_line`, `src:census.tigerweb`, `src:census.acs_api`,
`src:gcp.bigquery_public_datasets`.

CKAN/Socrata/ArcGIS/OGC Records are the four portal protocols the harvesters must
speak; between them they cover the large majority of US federal, state, and municipal
open-data publishing. TIGER/TIGERweb supply boundary geometries and ACS supplies the
denominators (population, demographics) that catchment analysis needs.

### 3.5 Geospatial analysis tooling

Key surfaces: `src:tooling.geopandas`, `src:tooling.duckdb_spatial`,
`src:tooling.postgis`, `src:tooling.osmnx`, `src:tooling.osrm`,
`src:tooling.openrouteservice`, `src:tooling.h3`, `src:tooling.s2geometry`.

These are execution substrates, not data sources: joins and aggregation in
GeoPandas/DuckDB-spatial/PostGIS, network and isochrone work in OSMnx/OSRM/
openrouteservice, indexing in H3/S2. Every analysis receipt names the engine and
version used so results are reproducible.

## 4. P0 build order: the 18 canonical primitives

Build top-to-bottom; later rows consume earlier rows' output edges.

| # | Primitive ID | Input edge -> Output edge | Behavior (one line) |
|---|--------------|---------------------------|---------------------|
| 1 | `prim:place_discovery.source_surface_registry` | DirectedQuestion+AreaOfInterest+SourcePolicy -> SourceSurfacePlan | Ranks known source surfaces official-first for the question and AOI and emits an ordered, policy-annotated fetch plan. |
| 2 | `prim:place_discovery.ckan_package_resource_harvester` | SourceSurfacePlan+ExtractionSchema -> SourceSnapshots+TypedRecords | Enumerates CKAN packages/resources via package_search, downloads matching resources, and types rows against the schema. |
| 3 | `prim:place_discovery.socrata_soql_dataset_ingester` | SourceSurfacePlan+ExtractionSchema -> SourceSnapshots+TypedRecords | Pages a Socrata dataset with SoQL select/where/limit/offset and validates rows into typed records. |
| 4 | `prim:place_discovery.arcgis_featureserver_layer_ingester` | SourceSurfacePlan+ExtractionSchema -> SourceSnapshots+TypedRecords | Walks ArcGIS FeatureServer/MapServer layer query endpoints with resultOffset paging, preserving geometries. |
| 5 | `prim:place_discovery.hrsa_health_center_ingester` | SourceSurfacePlan+ExtractionSchema -> SourceSnapshots+TypedRecords | Ingests HRSA health center site records with site type, grant program, and service fields typed and snapshotted. |
| 6 | `prim:place_discovery.nppes_provider_identity_resolver` | TypedRecords+DirectedQuestion -> NormalizedEntities | Resolves facility/provider rows against NPPES NPI records (org name, taxonomy, practice address) to confirm identity. |
| 7 | `prim:place_discovery.careeronestop_training_provider_adapter` | SourceSurfacePlan+ExtractionSchema -> SourceSnapshots+TypedRecords | Fetches training providers and programs from the CareerOneStop API for the AOI and types them. |
| 8 | `prim:place_discovery.college_scorecard_ipeds_program_adapter` | SourceSurfacePlan+ExtractionSchema -> SourceSnapshots+TypedRecords | Pulls institution and program records from College Scorecard/IPEDS and aligns them to the extraction schema. |
| 9 | `prim:place_discovery.osm_overpass_bounded_poi_query` | AreaOfInterest+ExtractionSchema+SourcePolicy -> SourceSnapshots+TypedRecords | Runs bounded Overpass QL tag queries under politeness limits and records ODbL attribution on every row. |
| 10 | `prim:place_discovery.overture_openaddresses_place_ingester` | AreaOfInterest+ExtractionSchema -> SourceSnapshots+TypedRecords | Extracts Overture places and OpenAddresses rows for the AOI from bulk releases, with release version recorded. |
| 11 | `prim:place_discovery.dataset_schema_fingerprint` | SourceSnapshots -> DatasetFingerprint | Computes column/type/geometry fingerprints of a snapshot so schema drift is detectable across harvests. |
| 12 | `prim:place_discovery.entity_normalize_and_dedupe` | TypedRecords -> NormalizedEntities+DedupeClusters | Normalizes names/addresses/phones, blocks candidate pairs, and clusters duplicates with per-cluster match evidence. |
| 13 | `prim:place_discovery.geocode_policy_gate` | NormalizedEntities+SourcePolicy -> NormalizedEntities+GeocodeReceipts | Geocodes only through policy-approved routes, records per-point method and confidence, and fails closed on disallowed endpoints. |
| 14 | `prim:place_discovery.point_to_boundary_spatial_join` | NormalizedEntities+BoundarySet -> TypedRecords+SpatialAnalysisReceipt | Joins points to boundaries (tracts, counties, service areas) with boundary vintage and CRS recorded in the receipt. |
| 15 | `prim:place_discovery.nearest_facility_isochrone_catchment_analysis` | NormalizedEntities+AreaOfInterest -> SpatialArtifacts+SpatialAnalysisReceipt | Computes nearest-facility distances, travel-time isochrones, and catchment denominators with engine and parameters receipted. |
| 16 | `prim:place_discovery.map_artifact_generation` | NormalizedEntities+SpatialAnalysisReceipt -> MapOrDashboardArtifact+SpatialArtifacts | Renders labeled, attributed, non-blank maps/dashboards (GeoJSON, tiles, HTML) with legend and attribution blocks. |
| 17 | `prim:place_discovery.evidence_bundle_wrapper` | NormalizedEntities+DedupeClusters+SpatialAnalysisReceipt+SourceSnapshots -> EvidenceBackedAnswer+SourceBundle+UncertaintyReport | Assembles the final answer with per-claim citations, snapshot hashes, freshness stamps, and explicit unknowns. |
| 18 | `prim:place_discovery.portal_change_monitor` | SourceSurfacePlan+DatasetFingerprint -> ChangeReport | Re-fingerprints portals and datasets on a schedule and flags additions, removals, and schema drift for re-runs. |

Notes on the table:

- Rows 2-10 are source adapters; they share the SourceSnapshots+TypedRecords output
  contract so downstream primitives are adapter-agnostic.
- Rows 11-13 are hygiene primitives; nothing spatial should run on un-fingerprinted,
  un-deduped, or un-gated data.
- Rows 14-16 are the analysis spine; row 17 is the only primitive allowed to emit the
  lane's visible output edge; row 18 closes the freshness loop.

## 5. Primitive groups worth building

Groups are named compositions of P0 primitives that match recurring demand shapes.
Each becomes a sellable route once its member primitives pass promotion gates.

1. **Resolved clinic registry** -- HRSA + NPPES + HIFLD adapters, then
   normalize/dedupe, geocode gate, and evidence wrapper: one deduplicated,
   provenance-carrying clinic directory per AOI.
2. **Care access gap analysis** -- resolved registry + boundary join + isochrone/
   catchment analysis + map artifact: which populations in the AOI fall outside
   stated travel-time thresholds, with denominators from ACS.
3. **Workforce training gap report** -- CareerOneStop + ETPL + Scorecard/IPEDS
   adapters, dedupe, boundary join: training supply by program area versus the AOI,
   with coverage gaps stated per source.
4. **Site selection ranking** -- resolved registry + catchment analysis + candidate
   scoring over H3 cells: ranked candidate locations with per-criterion receipts and
   an uncertainty report, planning output only.
5. **Portal harvest to typed artifact** -- source surface registry + CKAN/Socrata/
   ArcGIS harvesters + schema fingerprint: turn "is there a dataset for X on this
   portal" into typed, fingerprinted records.
6. **OSM vs official coverage comparison** -- official adapters + Overpass/Overture
   ingesters + dedupe across the two universes: where open-map data confirms,
   contradicts, or is silent relative to official registries.

## 6. Benchmark plan

Structure (all counts here describe the generated demand set, not results):

- **8 task families x 40 areas of interest = 320 generated task demands.** Families:
  1. resolved-facility-directory (build the clinic/facility registry for an AOI)
  2. single-facility-lookup-and-verify (one entity, cross-source confirmation)
  3. care-access-gap (isochrone/catchment coverage against a threshold)
  4. training-provider-lookup (workforce supply for a program area)
  5. portal-harvest-to-typed-artifact (find and type a portal dataset)
  6. osm-vs-official-coverage (agreement/disagreement report)
  7. site-selection-ranking (ranked candidates with receipts)
  8. freshness-and-change-audit (what changed since a prior fingerprint)
- **Arms A1-A5:**
  - A1: raw model, no tools (floor).
  - A2: model + generic web search only.
  - A3: model + generic fetch/scrape tools, no lane primitives.
  - A4: model + P0 lane primitives, uncomposed.
  - A5: model + primitive groups (Section 5) as composed routes.
- **Scorecard fields (per task, per arm):** answer_correctness_vs_fixture,
  citation_coverage, attribution_complete, geocode_confidence_reported,
  boundary_vintage_recorded, freshness_recorded, artifact_validity
  (nonblank/labeled/attributed), entity_match_precision_on_fixtures,
  policy_violation_count, steps_taken, tool_calls, wall_clock.
- **Depth-to-solution ladder L1-L7** (each task demand is tagged with one level):
  - L1: single-source, single-record lookup.
  - L2: single-source bounded list extraction.
  - L3: two-source join on entity identity.
  - L4: multi-source dedupe into a resolved registry.
  - L5: registry plus boundary join and demographic denominators.
  - L6: catchment/isochrone analysis with an uncertainty report.
  - L7: full gap analysis or site selection with cross-source validation and
    map/dashboard artifacts.

**Explicit status: no benchmark has been run yet.** Every number above (8, 40, 320,
A1-A5, L1-L7) describes the generated demand set and comes from the pack manifest;
recompute any count from
`catalog/knowledge-packs/data/place-discovery-geospatial-seeds/manifest.json`
rather than trusting this document. No arm has produced scores, and this handoff
asserts no performance ordering between arms.

## 7. Proof receipts specific to this lane

Receipts are the machine-checkable claims a route must emit to be promotable. Lane-
specific receipt types:

- **attribution_complete** -- every OSM/Overture/OpenAddresses-derived row and every
  rendered artifact carries the required attribution string (e.g. ODbL for OSM);
  checker fails the bundle if any derived output lacks it.
- **geocode_confidence** -- every coordinate has a method
  (source_supplied | address_geocoded | centroid_fallback), a route (which geocoder,
  under which policy), and a confidence tier; no bare lat/lon pairs.
- **boundary_vintage** -- every spatial join names the boundary set, its vintage year,
  and CRS; joins against unversioned boundaries are rejected.
- **freshness_recorded** -- every snapshot has fetch timestamp and, where the source
  exposes it, source publication/modification date; the evidence bundle surfaces the
  oldest input.
- **map artifact validity** -- rendered maps/dashboards must be non-blank (features
  actually drawn), labeled (title, legend, units), and attributed (source and license
  block present); checked structurally, not by eyeball.
- **entity_match_precision fixtures** -- dedupe is validated against hand-labeled
  match/non-match fixture pairs per source-pair; clusters must reproduce fixture
  labels before a dedupe output is trusted in a bundle.
- **policy_gate receipts** -- each fetch and geocode step logs which SourcePolicy rule
  admitted it; absence of a gate log is itself a failure.

## 8. Hard boundaries

These are lane invariants, not preferences:

- **Directory/access/planning outputs only.** Never patient-level data, never
  individual health records, never anything that identifies a person receiving care.
- **No diagnosis or treatment advice.** The lane locates facilities and analyzes
  access; it never recommends clinical action.
- **No final legal or compliance conclusions.** Outputs may summarize what a source's
  license or policy states and flag obligations; a human owns any legal conclusion.
- **Usage-policy gates are mandatory.** The public Nominatim endpoint and public
  Overpass instances have strict usage policies (rate, attribution, bulk-use
  prohibitions). The geocode_policy_gate and Overpass primitive must enforce them;
  scaled or repeated workloads must move to self-hosted instances, planet extracts,
  Overture releases, or bulk downloads instead of hammering shared public endpoints.
- **Attribution obligations propagate.** ODbL (OSM), CC-BY variants, and portal-
  specific terms attach to derived artifacts, not just raw downloads; the
  attribution_complete receipt enforces propagation.
- **Respect robots/ToS on browse fetches.** APIOrBrowseFetchPlan entries that would
  violate a surface's stated terms fail closed at plan time.

## 9. Repo pointers

- `schemas/` -- schema files for the lane's edge types (AreaOfInterest,
  DirectedQuestion, SourcePolicy, ExtractionSchema, SourceSnapshots, TypedRecords,
  NormalizedEntities, DedupeClusters, SpatialAnalysisReceipt, EvidenceBackedAnswer,
  UncertaintyReport) and for seed row shapes.
- `scripts/build_place_discovery_geospatial_pack.py` -- the single source builder. It
  reads the pure-data seed modules, injects builder-owned fields (candidate=true,
  serves_truth=false, record_type, version), and writes the pack. **Never hand-edit
  pack output files**; change seeds and rebuild.
- `scripts/check_place_discovery_geospatial_pack.py` -- the pack checker; run with
  `--self-test` first, then against the built pack. It validates ID stability,
  cross-reference integrity (every `prim:` and `src:` reference resolves), and the
  no-metrics rule in descriptive text.
- `catalog/knowledge-packs/data/place-discovery-geospatial-seeds/` -- built pack
  output, including `manifest.json`. All counts (rows per constant, task demands,
  primitives, sources) are recomputed from `manifest.json`; never type counts into
  docs, code review comments, or dashboards by hand.

Seed module conventions (repeated here because they are easy to break): pure data,
top-level list-of-dicts constants, no imports/functions, ASCII only, module
docstring first, IDs stable and version-free, and no candidate/serves_truth/
record_type/version fields in seed rows -- the builder injects those.

## 10. Next build slices

Ordered; each slice should land with fixtures and checker coverage before the next
starts.

1. **Source adapter implementation order** -- (a) `source_surface_registry` since
   everything depends on plans; (b) the three portal protocol harvesters (CKAN,
   Socrata, ArcGIS FeatureServer) because they unlock the widest surface set from
   three implementations; (c) HRSA + NPPES for the health lane's official core;
   (d) CareerOneStop + Scorecard/IPEDS for workforce; (e) Overpass + Overture/
   OpenAddresses for enrichment, behind the policy gate from day one.
2. **Fixture capture** -- for each adapter, capture small frozen SourceSnapshots
   fixtures (recorded HTTP payloads) and hand-labeled dedupe match/non-match pairs
   for at least the HRSA-NPPES and CareerOneStop-IPEDS source pairs; fixtures are the
   ground truth for entity_match_precision receipts and for checker self-tests.
3. **Benchmark harness wiring** -- generate the 8x40 task demand set from seeds into
   the pack, wire arms A1-A5 as runnable configurations, implement the scorecard
   fields as pure functions over run transcripts, and dry-run one L1 and one L4 task
   end-to-end without recording scores as truth.
4. **Promotion gates** -- a primitive leaves candidate status only when: its schema
   contracts validate; its receipts (Section 7) are emitted and checker-verified on
   fixtures; its policy gates fail closed under test; and benchmark runs exist as
   local manifests that a reviewer can replay. Until then everything in this lane
   stays candidate=true / serves_truth=false.

---

End of handoff. When in doubt: official sources first, receipts on everything,
recompute counts from `manifest.json`, and never let an unattributed or ungated
artifact into an evidence bundle.

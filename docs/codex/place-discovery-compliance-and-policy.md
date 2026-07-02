# Place Discovery / Geospatial Lane: Compliance and Policy Pack

Last updated: 2026-07-02

Status: candidate policy pack. The policies in this document gate promotion of
primitives in the `place-discovery-geospatial` lane. They are engineering
requirements enforced by gates, tests, and receipts. They are not legal advice
and do not substitute for counsel review where counsel review is required.

Lane edge covered by this pack:

```
AreaOfInterest + DirectedQuestion + SourcePolicy + ExtractionSchema
  -> EvidenceBackedAnswer + SourceBundle + SpatialArtifacts + UncertaintyReport
```

---

## 1. License and Attribution Matrix

Every source surface used by a lane primitive must appear in this matrix (or a
successor registry record under `prim:place_discovery.source_surface_registry`)
before its data may flow past the license gate. Any surface not listed is
treated as license-unknown and is quarantined until reviewed.

| Source surface(s) | License posture | Attribution requirement | Usage-policy notes |
|---|---|---|---|
| `src:osm.overpass_api`, `src:osm.planet_extracts` | ODbL | "(c) OpenStreetMap contributors" on every derived artifact; ODbL share-alike applies to derivative databases | Public Overpass endpoints have published fair-use policies; bulk or scaled extraction must move to planet/regional extracts or a self-hosted instance |
| `src:osm.nominatim_geocoder` | ODbL (data) | Same OSM attribution on any artifact using geocoded results | Public endpoint usage policy is binding: identify the application, respect the published request-rate ceiling, no bulk geocoding, no systematic scraping; bulk/scaled use must self-host or use offline geocoding against extracts |
| `src:overture.maps_places` | ODbL / CDLA mix, varies by theme | Attribution per theme license; verify per theme at ingest time | Do not assume a single license across themes; the license gate records the theme-level license in every receipt |
| `src:openaddresses.global_collection` | Varies by contributing source | Per-source attribution as declared in source metadata | Record the per-source license for every address file ingested; sources with no declared license are quarantined |
| US federal data: `src:hrsa.health_center_sites`, `src:hrsa.find_a_health_center`, `src:cms.nppes_npi_registry`, `src:cms.provider_data_catalog`, `src:hifld.health_facility_layers`, `src:careeronestop.training_providers_api`, `src:ed.college_scorecard_api`, `src:nces.ipeds`, `src:dol.registered_apprenticeship_rapids` | Public domain (US federal work) unless a dataset states otherwise | Cite agency, dataset name, and data vintage on every artifact | Public domain does not remove the receipt requirement; agency terms of service and API keys still apply |
| `src:census.tiger_line`, `src:census.tigerweb`, `src:census.acs_api` | Public domain | Cite Census Bureau, product name, and vintage (e.g. TIGER/Line vintage year, ACS release) on every artifact | Boundary vintage must match the tabular vintage used in any join; mismatches must be declared in the uncertainty report |
| `src:socrata.soda_api`, `src:datagov.ckan_api`, `src:ogc.api_records` portal datasets | Varies per dataset | Attribution per dataset-declared license | License is a dataset-level property, not a portal-level property; record the dataset-level license string in every receipt, quarantine when absent |
| `src:esri.arcgis_hub`, `src:esri.arcgis_featureserver` | Owner-set terms per item | Attribution per item terms | Record the item-level terms-of-use text (or its absence) in every receipt; absence of terms does not imply permission |
| `src:dol.state_etpl_directories` | Varies by state | Cite state agency and effective date | ETPL/WIOA lists are eligibility-adjacent; freshness stamping is mandatory (see Section 5) |
| `src:healthsites.global_registry` | ODbL (OSM-derived) | OSM attribution plus Healthsites attribution | Treat as OSM-derived for share-alike purposes |
| `src:who.ghfd`, `src:hdx.health_facility_datasets` | Varies per dataset/country | Per-dataset attribution | Record dataset-level license; some national facility lists carry restrictions on redistribution |
| `src:geonames.gazetteer` | CC-BY | GeoNames attribution on every artifact using its records | Public web services have request quotas; bulk use should rely on dump files |
| `src:naturalearth.basemap_vectors` | Public domain | Attribution appreciated but not required; the lane still emits an attribution string for consistency | No usage restrictions; still receipt-tracked |
| `src:gcp.bigquery_public_datasets` | Varies per dataset | Per-dataset attribution | The hosting platform does not change the underlying dataset license; record it per dataset |

Cross-cutting rules:

- ODbL share-alike: any derivative database produced substantially from ODbL
  sources inherits ODbL obligations. The evidence bundle must flag ODbL-derived
  outputs so downstream consumers know the obligation travels with the data.
- Mixed-license joins: when an output joins sources with different licenses,
  the receipt lists every contributing license and the artifact carries the
  union of attribution requirements.
- License downgrades are forbidden: a permissive summary never replaces the
  recorded license string of a source.

---

## 2. Usage-Policy Gates as Primitives

Usage policies are enforced in code, not in documentation alone. Three gate
behaviors are mandatory across the lane.

### 2.1 `prim:place_discovery.geocode_policy_gate`

- Sits in front of every geocoding and heavy-query call path (Nominatim,
  Overpass, TIGERweb, portal APIs).
- Enforces per-endpoint request pacing derived from the endpoint's published
  policy, sends an identifying User-Agent/contact string, and honors
  Retry-After and equivalent backoff signals.
- Detects bulk-use patterns (large batch geocoding, repeated area sweeps) and
  refuses to route them to shared public endpoints. Bulk workloads must
  escalate to: (a) bulk extracts (`src:osm.planet_extracts`,
  `src:openaddresses.global_collection`), (b) a self-hosted instance
  (Nominatim, `src:tooling.osrm`, `src:tooling.openrouteservice` self-hosted),
  or (c) a commercial/keyed endpoint whose terms permit the workload.
- Every gate decision (allow, throttle, refuse, escalate) is logged with the
  policy rule that produced it.

### 2.2 Attribution receipts on rendered artifacts

- `prim:place_discovery.map_artifact_generation` must embed the full set of
  required attribution strings in every map, tile set, dashboard export, and
  static image it produces. An artifact without its attribution block fails
  the artifact contract test.
- Attribution strings are assembled from receipts, never hand-typed at render
  time.

### 2.3 License gate on every ingested dataset

- Every ingester (`ckan_package_resource_harvester`,
  `socrata_soql_dataset_ingester`, `arcgis_featureserver_layer_ingester`,
  `hrsa_health_center_ingester`, `overture_openaddresses_place_ingester`,
  `osm_overpass_bounded_poi_query`, and peers) resolves the dataset-level
  license before persisting rows.
- Outcomes: `known-permissive`, `known-restricted` (ingest with obligations
  recorded), or `unknown` (quarantine; data is held out of all downstream
  joins until a human review resolves the license).
- `prim:place_discovery.evidence_bundle_wrapper` refuses to seal a bundle that
  contains any quarantined source.

---

## 3. Privacy Boundaries

This lane handles facility and provider DIRECTORY data only.

- NPI/NPPES (`src:cms.nppes_npi_registry`) is public directory data. It must
  never be joined with patient-level data, claims-line data, encounter data,
  or any dataset containing individual health information within this lane.
  `prim:place_discovery.nppes_provider_identity_resolver` operates on provider
  identity records only.
- No re-identification joins: no combination of lane outputs with external
  data for the purpose of identifying, locating, or profiling individuals.
  This prohibition covers indirect paths (e.g. joining rare provider
  specialties with small geographies to single out a person's care pattern).
- Small-population suppression: tract-level (or finer) reporting must apply a
  suppression rule when the underlying population or facility count falls
  below a configured threshold. The threshold is configurable per deployment;
  the existence of the rule is not optional. Suppressed cells are marked as
  suppressed, not zero.
- Sensitive facility categories (domestic-violence shelters and analogous
  categories where exact location can endanger people) require suppression or
  generalization of exact coordinates in every output. Generalization means
  reporting at a coarser geography (city, county, service area) with the
  generalization method recorded in the receipt. Category lists are maintained
  in the source surface registry and applied by
  `prim:place_discovery.entity_normalize_and_dedupe` and
  `prim:place_discovery.map_artifact_generation`.

---

## 4. Output Boundaries

- Permitted outputs: directory listings, access/coverage analysis, catchment
  and isochrone summaries, site-selection candidate lists, gap analyses,
  harvest inventories, change reports, and planning-grade maps.
- Every analytical answer ships with an UncertaintyReport. Mandatory contents:
  source vintages, geocoding precision distribution, boundary vintage,
  known coverage gaps, and any suppression applied.
- Never emitted: diagnosis or treatment advice, clinical recommendations, or
  any output that steers an individual's medical care.
- Never emitted: final legal, regulatory, or eligibility conclusions. When a
  question crosses into eligibility or compliance determination (e.g. "is this
  provider ETPL-eligible for this participant"), the lane emits a human-review
  packet: the evidence bundle, the candidate finding, the applicable policy
  citations, and an explicit "requires human determination" flag.
- Eligibility-adjacent outputs (ETPL/WIOA training lists, scholarship and
  program eligibility contexts) must carry freshness and effective-date
  stamps: retrieval timestamp, source-declared effective date where present,
  and the `prim:place_discovery.portal_change_monitor` status for the source.
  ETPL and WIOA lists change; an unstamped list is a contract-test failure.

---

## 5. Promotion Gates and Lifecycle Mapping

A lane primitive is promotable only when all of the following hold:

1. Source refs resolved: every `src:*` reference resolves in the source
   surface registry.
2. License reviewed: every referenced surface has a reviewed matrix entry
   (Section 1) or registry record.
3. Usage policy encoded: rate/bulk/self-host rules exist as executable gate
   configuration, not prose.
4. Contract tests: input/output contracts of the primitive's edge are tested.
5. Fixture tests: the primitive runs against recorded fixtures offline with
   deterministic results.
6. Attribution receipt tests: artifacts produced in tests carry complete
   attribution blocks assembled from receipts.
7. Freshness policy: a declared staleness policy per source, wired to
   `prim:place_discovery.portal_change_monitor`.
8. Human review wiring: high-risk outputs (Section 6 triggers) route to a
   human-review packet rather than an autonomous answer.

L0-L10 lifecycle mapping for this lane:

| Level | Meaning in this lane |
|---|---|
| L0 | Primitive named; stable ID reserved; edge sketched |
| L1 | Edge declared: typed inputs/outputs and hard boundaries written down |
| L2 | Source surfaces enumerated and resolved in the registry |
| L3 | License and usage policy reviewed for every referenced surface; matrix entry exists |
| L4 | Usage-policy gates encoded (rate pacing, bulk refusal, self-host escalation paths) |
| L5 | Contract tests pass on the declared edge |
| L6 | Fixture tests pass offline against recorded source snapshots |
| L7 | Live smoke run against real endpoints, executed through the policy gates |
| L8 | Attribution receipts and evidence bundles verified end-to-end; license gate exercised on real datasets |
| L9 | Freshness/change monitoring wired; human-review routing verified for triggering outputs |
| L10 | Promotion candidate complete: all Section 5 gates green; eligible for serves_truth review |

No primitive may skip levels; a regression at any level demotes the primitive
to that level until repaired.

---

## 6. Human-Review Triggers

A human-review packet (not an autonomous answer) is required when any of the
following occur:

- The requested output is an eligibility, legal, or compliance determination.
- A source's license is unknown, disputed, or newly changed since last review.
- A sensitive facility category appears in the result set.
- Small-population suppression would remove a material share of the result and
  the requester asks for the unsuppressed view.
- An ODbL share-alike obligation would attach to an output destined for a
  consumer who has not acknowledged the obligation.
- Entity resolution (`entity_normalize_and_dedupe`,
  `nppes_provider_identity_resolver`) merges records below its configured
  confidence policy and the merge would change a headline answer.
- A portal change monitor detects schema drift
  (`dataset_schema_fingerprint` mismatch) on a source feeding a live answer.
- The requester asks to bypass any gate in this pack.

---

## 7. Telemetry and Audit Requirements

Every ingest event emits, at minimum:

- Source surface ID (`src:*`) and concrete endpoint/dataset identifier.
- Source snapshot hash (content hash of the retrieved payload or file).
- License status as resolved by the license gate, including the recorded
  license string or `unknown`.
- The exact attribution string(s) attached to the ingested data.
- Retrieval timestamp (UTC) and the identity/contact string presented to the
  endpoint.
- Policy-gate decisions taken during retrieval (pacing, backoff, refusals).

Every spatial analysis emits a method receipt, at minimum:

- CRS of every input layer and of the analysis frame, with any reprojection
  steps listed.
- Boundary source and vintage for every administrative or statistical
  geography used (`src:census.tiger_line` vintage, etc.).
- Travel-time engine and parameters when isochrones or catchments are
  computed: engine (`src:tooling.osrm`, `src:tooling.openrouteservice`, or
  other), profile, cost model, snapshot of the network data vintage.
- Spatial indexing/tessellation scheme when used (`src:tooling.h3`,
  `src:tooling.s2geometry`) including resolution/level.
- Join predicates and tolerance settings for
  `prim:place_discovery.point_to_boundary_spatial_join`.
- Suppression and generalization operations applied, with rule identifiers.

Audit retention: receipts and method records are retained with the evidence
bundle for as long as the bundle is servable. A bundle whose receipts have
been lost is no longer servable and must be regenerated from sources.

---

## 8. Precedence and Change Control

- Where this pack conflicts with a source's own published policy, the stricter
  requirement wins.
- Changes to this pack are versioned through normal review; primitives already
  promoted are re-evaluated against the changed gates before their next
  promotion-affecting release.
- Nothing in this pack authorizes patient-level data handling, diagnosis or
  treatment advice, or final legal/compliance conclusions under any
  configuration.

"""Benchmark dimension seed data for the place-discovery-geospatial lane.

Defines the task families, areas of interest, and comparison arms used to
assemble benchmark scenarios for the lane's canonical visible edge:
AreaOfInterest + DirectedQuestion + SourcePolicy + ExtractionSchema ->
EvidenceBackedAnswer + SourceBundle + SpatialArtifacts + UncertaintyReport.
All rows are candidate seed material; a builder script injects candidacy
and truth-status fields. Outputs described here are directory, access, and
planning artifacts only -- never patient-level data, never diagnosis or
treatment advice, never final legal or compliance conclusions.
"""

TASK_FAMILIES = [
    {
        "family_id": "clinic_discovery",
        "title": "Clinic and Health Center Discovery",
        "directed_question_template": (
            "Find all federally funded health centers and free or "
            "sliding-scale clinics operating in {aoi}, list each site with "
            "address, services offered, and operating status, and cite the "
            "official source record for every site."
        ),
        "expected_artifacts": [
            "EvidenceBackedAnswer",
            "SourceBundle",
            "FacilityDirectory",
            "UncertaintyReport",
        ],
        "primitive_demands": [
            "prim:place_discovery.hrsa_health_center_ingester",
            "prim:place_discovery.nppes_provider_identity_resolver",
            "prim:place_discovery.entity_normalize_and_dedupe",
            "prim:place_discovery.geocode_policy_gate",
            "prim:place_discovery.evidence_bundle_wrapper",
        ],
        "default_source_policy": "official_first",
        "scorecard_fields": [
            "task_success",
            "tokens_to_plan",
            "tokens_to_pass",
            "source_context_tokens",
            "entity_match_precision",
            "source_ref_coverage",
            "attribution_complete",
            "freshness_recorded",
            "proof_coverage",
        ],
        "notes": (
            "The same physical clinic appears under different names, "
            "addresses, and identifiers across HRSA, NPPES, and open map "
            "sources, so correct answers require identity resolution rather "
            "than simple list concatenation."
        ),
    },
    {
        "family_id": "training_provider_discovery",
        "title": "Workforce Training Provider Discovery",
        "directed_question_template": (
            "Identify every eligible training provider offering healthcare "
            "or skilled-trades programs within commuting distance of {aoi}, "
            "including program names, credential outcomes, and cost fields, "
            "with a source citation for each provider record."
        ),
        "expected_artifacts": [
            "EvidenceBackedAnswer",
            "SourceBundle",
            "ProviderDirectory",
            "UncertaintyReport",
        ],
        "primitive_demands": [
            "prim:place_discovery.careeronestop_training_provider_adapter",
            "prim:place_discovery.college_scorecard_ipeds_program_adapter",
            "prim:place_discovery.entity_normalize_and_dedupe",
            "prim:place_discovery.geocode_policy_gate",
            "prim:place_discovery.evidence_bundle_wrapper",
        ],
        "default_source_policy": "official_first",
        "scorecard_fields": [
            "task_success",
            "tokens_to_plan",
            "tokens_to_pass",
            "source_files_read",
            "entity_match_precision",
            "source_ref_coverage",
            "attribution_complete",
            "freshness_recorded",
            "schema_validity",
        ],
        "notes": (
            "Federal, state ETPL, and institutional catalogs disagree on "
            "program taxonomies and campus locations, so reconciling a "
            "provider's programs to a single geocoded site is the core "
            "difficulty."
        ),
    },
    {
        "family_id": "care_desert_analysis",
        "title": "Care Desert and Coverage Gap Analysis",
        "directed_question_template": (
            "Determine which populated areas of {aoi} lie more than 30 "
            "minutes travel from the nearest primary care site, quantify "
            "the population inside each gap, and deliver a map with an "
            "uncertainty report describing travel-time assumptions."
        ),
        "expected_artifacts": [
            "EvidenceBackedAnswer",
            "SourceBundle",
            "MapArtifact",
            "CatchmentLayer",
            "UncertaintyReport",
        ],
        "primitive_demands": [
            "prim:place_discovery.hrsa_health_center_ingester",
            "prim:place_discovery.osm_overpass_bounded_poi_query",
            "prim:place_discovery.point_to_boundary_spatial_join",
            "prim:place_discovery.nearest_facility_isochrone_catchment_analysis",
            "prim:place_discovery.map_artifact_generation",
            "prim:place_discovery.evidence_bundle_wrapper",
        ],
        "default_source_policy": "official_and_open_compare",
        "scorecard_fields": [
            "task_success",
            "tokens_to_plan",
            "tokens_to_pass",
            "wall_clock_seconds",
            "map_artifact_correctness",
            "source_ref_coverage",
            "attribution_complete",
            "proof_coverage",
            "depth_to_solution",
        ],
        "notes": (
            "Results depend on chained spatial operations where an error in "
            "facility geocoding, network routing, or population "
            "apportionment silently corrupts the final gap estimate."
        ),
    },
    {
        "family_id": "portal_dataset_harvest",
        "title": "Open Data Portal Dataset Harvest",
        "directed_question_template": (
            "Enumerate all open-government datasets about health, human "
            "services, or facilities that cover {aoi} across CKAN, Socrata, "
            "and ArcGIS portals, and record each dataset's access endpoint, "
            "license, update cadence, and schema fingerprint."
        ),
        "expected_artifacts": [
            "EvidenceBackedAnswer",
            "SourceBundle",
            "DatasetCatalog",
            "UncertaintyReport",
        ],
        "primitive_demands": [
            "prim:place_discovery.source_surface_registry",
            "prim:place_discovery.ckan_package_resource_harvester",
            "prim:place_discovery.socrata_soql_dataset_ingester",
            "prim:place_discovery.arcgis_featureserver_layer_ingester",
            "prim:place_discovery.dataset_schema_fingerprint",
            "prim:place_discovery.evidence_bundle_wrapper",
        ],
        "default_source_policy": "portal_catalog_only",
        "scorecard_fields": [
            "task_success",
            "tokens_to_plan",
            "tokens_to_pass",
            "source_files_read",
            "source_context_tokens",
            "schema_validity",
            "source_ref_coverage",
            "attribution_complete",
            "freshness_recorded",
        ],
        "notes": (
            "The same dataset is often republished across multiple portals "
            "with different identifiers and stale copies, so the harvest "
            "must distinguish authoritative originals from mirrors."
        ),
    },
    {
        "family_id": "osm_poi_extraction",
        "title": "Open Map POI Extraction",
        "directed_question_template": (
            "Extract all healthcare and social-facility points of interest "
            "inside {aoi} from OpenStreetMap and Overture, normalize their "
            "categories and addresses, and report tag completeness with "
            "ODbL-compliant attribution."
        ),
        "expected_artifacts": [
            "EvidenceBackedAnswer",
            "SourceBundle",
            "POILayer",
            "UncertaintyReport",
        ],
        "primitive_demands": [
            "prim:place_discovery.osm_overpass_bounded_poi_query",
            "prim:place_discovery.overture_openaddresses_place_ingester",
            "prim:place_discovery.entity_normalize_and_dedupe",
            "prim:place_discovery.geocode_policy_gate",
            "prim:place_discovery.evidence_bundle_wrapper",
        ],
        "default_source_policy": "open_first",
        "scorecard_fields": [
            "task_success",
            "tokens_to_plan",
            "tokens_to_pass",
            "runtime_llm_tokens",
            "entity_match_precision",
            "attribution_complete",
            "source_ref_coverage",
            "freshness_recorded",
            "negative_memory_created",
        ],
        "notes": (
            "Community-mapped tagging is inconsistent across regions, and "
            "queries must stay within Overpass and Nominatim usage policies "
            "while still achieving complete coverage of the area."
        ),
    },
    {
        "family_id": "schema_drift_detection",
        "title": "Portal Schema Drift Detection",
        "directed_question_template": (
            "Compare the current schemas and record counts of previously "
            "harvested facility datasets covering {aoi} against their "
            "stored fingerprints, flag added, removed, or retyped fields, "
            "and report which downstream extractions the drift would break."
        ),
        "expected_artifacts": [
            "EvidenceBackedAnswer",
            "SourceBundle",
            "DriftReport",
            "UncertaintyReport",
        ],
        "primitive_demands": [
            "prim:place_discovery.dataset_schema_fingerprint",
            "prim:place_discovery.portal_change_monitor",
            "prim:place_discovery.ckan_package_resource_harvester",
            "prim:place_discovery.arcgis_featureserver_layer_ingester",
            "prim:place_discovery.evidence_bundle_wrapper",
        ],
        "default_source_policy": "portal_catalog_only",
        "scorecard_fields": [
            "task_success",
            "tokens_to_plan",
            "tokens_to_pass",
            "schema_validity",
            "freshness_recorded",
            "source_ref_coverage",
            "proof_coverage",
            "negative_memory_created",
            "route_reuse_count",
        ],
        "notes": (
            "Drift signals are subtle and mixed with benign changes such as "
            "row-order shuffles or metadata edits, so the task requires "
            "distinguishing breaking schema changes from cosmetic ones."
        ),
    },
    {
        "family_id": "site_selection_ranking",
        "title": "Facility Site Selection Ranking",
        "directed_question_template": (
            "Rank candidate locations in {aoi} for a new community health "
            "or training facility by unmet demand, travel-time coverage "
            "gain, and proximity to transit, and justify each ranking "
            "factor with cited source data."
        ),
        "expected_artifacts": [
            "EvidenceBackedAnswer",
            "SourceBundle",
            "RankedSiteList",
            "MapArtifact",
            "UncertaintyReport",
        ],
        "primitive_demands": [
            "prim:place_discovery.entity_normalize_and_dedupe",
            "prim:place_discovery.point_to_boundary_spatial_join",
            "prim:place_discovery.nearest_facility_isochrone_catchment_analysis",
            "prim:place_discovery.map_artifact_generation",
            "prim:place_discovery.evidence_bundle_wrapper",
        ],
        "default_source_policy": "official_and_open_compare",
        "scorecard_fields": [
            "task_success",
            "tokens_to_plan",
            "tokens_to_pass",
            "wall_clock_seconds",
            "depth_to_solution",
            "map_artifact_correctness",
            "source_ref_coverage",
            "proof_coverage",
            "route_reuse_count",
        ],
        "notes": (
            "Rankings combine demographic, facility, and network layers "
            "with explicit weighting choices, so every scoring decision "
            "must remain traceable to source evidence instead of model "
            "intuition."
        ),
    },
    {
        "family_id": "map_dashboard_generation",
        "title": "Map and Dashboard Artifact Generation",
        "directed_question_template": (
            "Produce a shareable map dashboard of facility access in {aoi} "
            "showing facility locations, catchment areas, and coverage "
            "statistics, with layer-level attribution and a data freshness "
            "panel."
        ),
        "expected_artifacts": [
            "EvidenceBackedAnswer",
            "SourceBundle",
            "MapArtifact",
            "DashboardSpec",
            "UncertaintyReport",
        ],
        "primitive_demands": [
            "prim:place_discovery.point_to_boundary_spatial_join",
            "prim:place_discovery.nearest_facility_isochrone_catchment_analysis",
            "prim:place_discovery.map_artifact_generation",
            "prim:place_discovery.geocode_policy_gate",
            "prim:place_discovery.evidence_bundle_wrapper",
        ],
        "default_source_policy": "open_first",
        "scorecard_fields": [
            "task_success",
            "tokens_to_plan",
            "tokens_to_pass",
            "runtime_llm_tokens",
            "map_artifact_correctness",
            "attribution_complete",
            "freshness_recorded",
            "schema_validity",
            "route_reuse_count",
        ],
        "notes": (
            "Correctness is judged on the rendered artifact itself, where "
            "projection choices, layer ordering, symbology, and attribution "
            "text all have to be right simultaneously for the output to "
            "pass."
        ),
    },
]

AREAS_OF_INTEREST = [
    {
        "aoi_id": "aoi:harris_county_tx",
        "name": "Harris County",
        "aoi_type": "county",
        "state": "TX",
        "context_tags": ["urban", "gulf_coast", "high_uninsured", "flood_prone"],
    },
    {
        "aoi_id": "aoi:atlanta_metro",
        "name": "Atlanta-Sandy Springs-Roswell Metro Area",
        "aoi_type": "metro",
        "state": "GA",
        "context_tags": ["urban", "sprawl", "transit_mixed", "regional_hub"],
    },
    {
        "aoi_id": "aoi:glacier_county_mt",
        "name": "Glacier County",
        "aoi_type": "county",
        "state": "MT",
        "context_tags": ["rural", "frontier", "tribal_area", "high_poverty"],
    },
    {
        "aoi_id": "aoi:issaquena_county_ms",
        "name": "Issaquena County",
        "aoi_type": "county",
        "state": "MS",
        "context_tags": ["rural", "delta_region", "high_poverty", "low_population"],
    },
    {
        "aoi_id": "aoi:bethel_census_area_ak",
        "name": "Bethel Census Area",
        "aoi_type": "county",
        "state": "AK",
        "context_tags": ["frontier", "tribal_area", "off_road_system", "fly_in_access"],
    },
    {
        "aoi_id": "aoi:aroostook_county_me",
        "name": "Aroostook County",
        "aoi_type": "county",
        "state": "ME",
        "context_tags": ["rural", "border", "aging_population", "forested"],
    },
    {
        "aoi_id": "aoi:mckinley_county_nm",
        "name": "McKinley County",
        "aoi_type": "county",
        "state": "NM",
        "context_tags": ["rural", "tribal_area", "high_uninsured", "checkerboard_land"],
    },
    {
        "aoi_id": "aoi:mcdowell_county_wv",
        "name": "McDowell County",
        "aoi_type": "county",
        "state": "WV",
        "context_tags": ["rural", "appalachian", "coal_region", "high_poverty"],
    },
    {
        "aoi_id": "aoi:adjuntas_municipio_pr",
        "name": "Adjuntas Municipio",
        "aoi_type": "county",
        "state": "PR",
        "context_tags": ["island", "mountainous", "rural", "hurricane_exposure"],
    },
    {
        "aoi_id": "aoi:fresno_county_ca",
        "name": "Fresno County",
        "aoi_type": "county",
        "state": "CA",
        "context_tags": ["central_valley", "agricultural", "high_uninsured", "urban_rural_mix"],
    },
    {
        "aoi_id": "aoi:youngstown_oh",
        "name": "Youngstown",
        "aoi_type": "city",
        "state": "OH",
        "context_tags": ["rust_belt", "population_decline", "legacy_industrial", "high_vacancy"],
    },
    {
        "aoi_id": "aoi:eagle_mountain_ut",
        "name": "Eagle Mountain",
        "aoi_type": "city",
        "state": "UT",
        "context_tags": ["mountain_west", "exurb", "fast_growth", "car_dependent"],
    },
    {
        "aoi_id": "aoi:imperial_county_ca",
        "name": "Imperial County",
        "aoi_type": "county",
        "state": "CA",
        "context_tags": ["border", "agricultural", "desert", "high_unemployment"],
    },
    {
        "aoi_id": "aoi:webb_county_tx",
        "name": "Webb County",
        "aoi_type": "county",
        "state": "TX",
        "context_tags": ["border", "urban_rural_mix", "high_uninsured", "bilingual_services"],
    },
    {
        "aoi_id": "aoi:hidalgo_county_tx",
        "name": "Hidalgo County",
        "aoi_type": "county",
        "state": "TX",
        "context_tags": ["border", "colonias", "high_uninsured", "fast_growth"],
    },
    {
        "aoi_id": "aoi:new_york_city_ny",
        "name": "New York City",
        "aoi_type": "city",
        "state": "NY",
        "context_tags": ["urban", "transit_rich", "dense", "immigrant_communities"],
    },
    {
        "aoi_id": "aoi:chicago_metro",
        "name": "Chicago-Naperville-Elgin Metro Area",
        "aoi_type": "metro",
        "state": "multi",
        "context_tags": ["urban", "transit_rich", "multi_state", "regional_hub"],
    },
    {
        "aoi_id": "aoi:los_angeles_county_ca",
        "name": "Los Angeles County",
        "aoi_type": "county",
        "state": "CA",
        "context_tags": ["urban", "dense", "car_dependent", "diverse_population"],
    },
    {
        "aoi_id": "aoi:maricopa_county_az",
        "name": "Maricopa County",
        "aoi_type": "county",
        "state": "AZ",
        "context_tags": ["urban", "desert", "fast_growth", "heat_exposure"],
    },
    {
        "aoi_id": "aoi:king_county_wa",
        "name": "King County",
        "aoi_type": "county",
        "state": "WA",
        "context_tags": ["urban", "transit_rich", "tech_economy", "high_cost_of_living"],
    },
    {
        "aoi_id": "aoi:wayne_county_mi",
        "name": "Wayne County",
        "aoi_type": "county",
        "state": "MI",
        "context_tags": ["rust_belt", "urban", "population_decline", "high_poverty"],
    },
    {
        "aoi_id": "aoi:gary_in",
        "name": "Gary",
        "aoi_type": "city",
        "state": "IN",
        "context_tags": ["rust_belt", "population_decline", "legacy_industrial", "lakefront"],
    },
    {
        "aoi_id": "aoi:flint_mi",
        "name": "Flint",
        "aoi_type": "city",
        "state": "MI",
        "context_tags": ["rust_belt", "infrastructure_stress", "high_poverty", "population_decline"],
    },
    {
        "aoi_id": "aoi:oglala_lakota_county_sd",
        "name": "Oglala Lakota County",
        "aoi_type": "county",
        "state": "SD",
        "context_tags": ["tribal_area", "rural", "frontier", "high_poverty"],
    },
    {
        "aoi_id": "aoi:apache_county_az",
        "name": "Apache County",
        "aoi_type": "county",
        "state": "AZ",
        "context_tags": ["tribal_area", "rural", "frontier", "high_uninsured"],
    },
    {
        "aoi_id": "aoi:harlan_county_ky",
        "name": "Harlan County",
        "aoi_type": "county",
        "state": "KY",
        "context_tags": ["appalachian", "coal_region", "rural", "high_poverty"],
    },
    {
        "aoi_id": "aoi:kauai_county_hi",
        "name": "Kauai County",
        "aoi_type": "county",
        "state": "HI",
        "context_tags": ["island", "rural", "tourism_economy", "geographically_isolated"],
    },
    {
        "aoi_id": "aoi:washington_dc",
        "name": "Washington",
        "aoi_type": "city",
        "state": "DC",
        "context_tags": ["urban", "transit_rich", "dense", "federal_hub"],
    },
    {
        "aoi_id": "aoi:san_juan_municipio_pr",
        "name": "San Juan Municipio",
        "aoi_type": "county",
        "state": "PR",
        "context_tags": ["island", "urban", "dense", "hurricane_exposure"],
    },
    {
        "aoi_id": "aoi:rio_arriba_county_nm",
        "name": "Rio Arriba County",
        "aoi_type": "county",
        "state": "NM",
        "context_tags": ["rural", "tribal_area", "mountainous", "high_poverty"],
    },
    {
        "aoi_id": "aoi:kern_county_ca",
        "name": "Kern County",
        "aoi_type": "county",
        "state": "CA",
        "context_tags": ["central_valley", "agricultural", "oil_economy", "air_quality_burden"],
    },
    {
        "aoi_id": "aoi:boise_metro",
        "name": "Boise City Metro Area",
        "aoi_type": "metro",
        "state": "ID",
        "context_tags": ["mountain_west", "fast_growth", "exurban_sprawl", "urban_rural_mix"],
    },
    {
        "aoi_id": "aoi:coos_county_or",
        "name": "Coos County",
        "aoi_type": "county",
        "state": "OR",
        "context_tags": ["rural", "coastal", "timber_economy", "aging_population"],
    },
    {
        "aoi_id": "aoi:loving_county_tx",
        "name": "Loving County",
        "aoi_type": "county",
        "state": "TX",
        "context_tags": ["frontier", "oil_economy", "lowest_population", "sparse_services"],
    },
    {
        "aoi_id": "aoi:cherry_county_ne",
        "name": "Cherry County",
        "aoi_type": "county",
        "state": "NE",
        "context_tags": ["frontier", "rural", "ranching_economy", "sparse_services"],
    },
    {
        "aoi_id": "aoi:west_census_region",
        "name": "West Census Region",
        "aoi_type": "census_region",
        "state": "multi",
        "context_tags": ["continental_scale", "frontier_counties", "urban_cores", "diverse_terrain"],
    },
    {
        "aoi_id": "aoi:vermont",
        "name": "Vermont",
        "aoi_type": "state",
        "state": "VT",
        "context_tags": ["rural", "aging_population", "mountainous", "small_state"],
    },
    {
        "aoi_id": "aoi:mississippi",
        "name": "Mississippi",
        "aoi_type": "state",
        "state": "MS",
        "context_tags": ["rural", "high_uninsured", "high_poverty", "delta_region"],
    },
    {
        "aoi_id": "aoi:minneapolis_st_paul_metro",
        "name": "Minneapolis-St. Paul-Bloomington Metro Area",
        "aoi_type": "metro",
        "state": "multi",
        "context_tags": ["urban", "transit_mixed", "cold_climate", "multi_state"],
    },
    {
        "aoi_id": "aoi:dothan_al",
        "name": "Dothan",
        "aoi_type": "city",
        "state": "AL",
        "context_tags": ["small_city", "rural_hub", "agricultural", "regional_health_hub"],
    },
]

COMPARISON_ARMS = [
    {
        "arm_id": "A1",
        "title": "Baseline Browsing Agent",
        "description": (
            "A general LLM agent that browses data portals, APIs, and "
            "documentation on the open web with no primitive scaffolding."
        ),
        "allowed_model_use": "unconstrained LLM calls for planning, browsing, and extraction",
        "allowed_context": "full_web_and_docs",
    },
    {
        "arm_id": "A2",
        "title": "Baseline Agent with RAG",
        "description": (
            "The same general agent grounded by retrieval over the repo and "
            "a prebuilt document index instead of live web browsing."
        ),
        "allowed_model_use": "unconstrained LLM calls with retrieval-augmented context",
        "allowed_context": "repo_and_rag",
    },
    {
        "arm_id": "A3",
        "title": "Primitive-First Candidate Bundle",
        "description": (
            "A primitive-first agent that plans against a CandidateBundle "
            "and commits execution through PlanDelta and PlanLock steps."
        ),
        "allowed_model_use": "LLM calls only for plan selection and PlanDelta authoring",
        "allowed_context": "candidate_bundle_only",
    },
    {
        "arm_id": "A4",
        "title": "Deterministic Route Replay",
        "description": (
            "Replay of a previously promoted route with deterministic "
            "template fill of the area of interest and question parameters."
        ),
        "allowed_model_use": "no generative calls beyond parameter template fill",
        "allowed_context": "planlock_replay",
    },
    {
        "arm_id": "A5",
        "title": "Primitive-First with Bounded Fallback",
        "description": (
            "A primitive-first agent that may escalate to a bounded set of "
            "registered source surfaces when the candidate bundle lacks "
            "coverage."
        ),
        "allowed_model_use": "LLM calls for planning plus policy-gated fallback queries",
        "allowed_context": "bundle_plus_source_fallback",
    },
]

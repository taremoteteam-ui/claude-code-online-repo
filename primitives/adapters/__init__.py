"""Source-adapter P0 primitives for the place-discovery-geospatial lane.

Each adapter is a plain function ``def <name>(payload: dict, transport)
-> PrimitiveOutcome`` with an injectable transport (FixtureTransport or
LiveTransport). Fixtures are SYNTHETIC data shaped like the real APIs;
adapters propagate ``retrieved_mode`` into snapshot metadata so
downstream evidence bundles disclose it. Stdlib only.
"""

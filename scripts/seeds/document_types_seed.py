"""Seed rows for document/contract types in the document-extraction lane.

Pure data module: one top-level constant DOCUMENT_TYPES (list of dicts).
Each row names a document family, the industry it belongs to, the canonical
field families that meaningfully apply to it, and where public exemplars or
standard forms live. The builder script injects record_type, version,
candidate=True, and serves_truth=False; seed rows must not set those. The
applicable_field_families list restricts the doc-type x field cross so the
builder pairs only meaningful fields, and every extracted field value must
still carry a verifiable source span into the document text. No metric,
benchmark, or accuracy claim appears here; rows describe only what a document
is and what is extracted from it.
"""

DOCUMENT_TYPES = [
    # ------------------------------------------------------------------
    # cross_industry
    # ------------------------------------------------------------------
    {
        "doc_type_id": "doctype:cross.mutual_nda",
        "title": "Mutual Non-Disclosure Agreement",
        "industry": "cross_industry",
        "description": (
            "A two-way confidentiality agreement under which both parties "
            "exchange and protect confidential information; extraction "
            "targets the parties, effective date, definition of confidential "
            "information, permitted use, and the confidentiality term."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "medium",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "definitions", "obligations",
            "confidentiality", "term_termination", "dispute_resolution",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "definition of confidential information",
            "permitted use and non-disclosure",
            "term and survival",
            "return or destruction of materials",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "industry standard confidentiality agreement templates",
        ],
        "human_review_required": False,
    },
    {
        "doc_type_id": "doctype:cross.unilateral_nda",
        "title": "Unilateral Non-Disclosure Agreement",
        "industry": "cross_industry",
        "description": (
            "A one-way confidentiality agreement protecting a disclosing "
            "party's information; extraction targets the disclosing and "
            "receiving parties, confidential-information scope, permitted "
            "purpose, and the confidentiality period."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "medium",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "definitions", "obligations",
            "confidentiality", "term_termination",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "definition of confidential information",
            "receiving party obligations",
            "term and survival",
            "exclusions from confidential information",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "industry standard confidentiality agreement templates",
        ],
        "human_review_required": False,
    },
    {
        "doc_type_id": "doctype:cross.master_services_agreement",
        "title": "Master Services Agreement",
        "industry": "cross_industry",
        "description": (
            "A framework agreement governing recurring services delivered "
            "under future statements of work; extraction targets the "
            "parties, fees and payment terms, term and renewal, liability "
            "caps, indemnities, and confidentiality obligations."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "obligations",
            "term_termination", "representations_warranties",
            "indemnification_liability", "confidentiality",
            "dispute_resolution", "governing_law_jurisdiction",
            "signatures_execution",
        ],
        "key_clause_types": [
            "scope and order of precedence",
            "fees and payment terms",
            "limitation of liability",
            "indemnification",
            "term and termination",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "industry standard master services agreement templates",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:cross.statement_of_work",
        "title": "Statement of Work",
        "industry": "cross_industry",
        "description": (
            "A work order issued under a master agreement that scopes "
            "specific deliverables, schedule, and fees; extraction targets "
            "the deliverables, milestones, quantities, unit and total fees, "
            "and the performance period."
        ),
        "typical_formats": ["pdf_native", "docx", "email"],
        "governing_law_sensitivity": "medium",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "monetary", "quantities", "obligations",
            "term_termination", "signatures_execution",
        ],
        "key_clause_types": [
            "scope of deliverables",
            "milestones and schedule",
            "fees and invoicing",
            "acceptance criteria",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "industry standard statement of work templates",
        ],
        "human_review_required": False,
    },
    {
        "doc_type_id": "doctype:cross.independent_contractor_agreement",
        "title": "Independent Contractor Agreement",
        "industry": "cross_industry",
        "description": (
            "An agreement engaging a non-employee to provide services; "
            "extraction targets the parties, compensation, term, work-product "
            "ownership, confidentiality, and the independent-contractor "
            "relationship statement."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "monetary", "obligations",
            "term_termination", "confidentiality", "ip_specific",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "scope of services",
            "compensation and expenses",
            "independent contractor relationship",
            "work product and intellectual property assignment",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "industry standard independent contractor templates",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:cross.letter_of_intent",
        "title": "Letter of Intent",
        "industry": "cross_industry",
        "description": (
            "A preliminary document outlining the principal terms of a "
            "proposed transaction, often mixing binding and non-binding "
            "provisions; extraction targets the parties, proposed price or "
            "consideration, key conditions, exclusivity, and expiration."
        ),
        "typical_formats": ["pdf_native", "docx", "email"],
        "governing_law_sensitivity": "medium",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "monetary", "conditions", "obligations",
            "confidentiality", "term_termination", "signatures_execution",
        ],
        "key_clause_types": [
            "proposed transaction terms",
            "binding and non-binding provisions",
            "exclusivity and no-shop",
            "expiration of offer",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "industry standard letter of intent templates",
        ],
        "human_review_required": True,
    },
    # ------------------------------------------------------------------
    # employment_hr
    # ------------------------------------------------------------------
    {
        "doc_type_id": "doctype:employment.executive_employment_agreement",
        "title": "Executive Employment Agreement",
        "industry": "employment_hr",
        "description": (
            "A negotiated agreement engaging a senior executive; extraction "
            "targets base salary, bonus and equity, title and duties, term, "
            "termination and severance triggers, restrictive covenants, and "
            "change-of-control provisions."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "obligations",
            "term_termination", "employment_specific", "confidentiality",
            "ip_specific", "indemnification_liability", "dispute_resolution",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "compensation and benefits",
            "term and termination for cause or good reason",
            "severance and change of control",
            "restrictive covenants",
            "clawback",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "SEC executive compensation exhibit filings",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:employment.at_will_employment_agreement",
        "title": "At-Will Employment Agreement",
        "industry": "employment_hr",
        "description": (
            "A standard-employee agreement establishing at-will employment; "
            "extraction targets the employee and employer, position, "
            "compensation, at-will statement, benefits eligibility, and "
            "confidentiality obligations."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "monetary", "obligations",
            "term_termination", "employment_specific", "confidentiality",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "at-will employment statement",
            "position and duties",
            "compensation and benefits",
            "confidentiality and assignment",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "state employment law model form guidance",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:employment.collective_bargaining_agreement",
        "title": "Collective Bargaining Agreement",
        "industry": "employment_hr",
        "description": (
            "A negotiated agreement between an employer and a labor union "
            "covering wages, hours, and working conditions; extraction "
            "targets wage scales, term, grievance and arbitration procedure, "
            "seniority, and management-rights provisions."
        ),
        "typical_formats": ["pdf_native", "pdf_scanned", "docx"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "obligations",
            "term_termination", "employment_specific", "dispute_resolution",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "recognition and bargaining unit",
            "wage scales and benefits",
            "grievance and arbitration procedure",
            "seniority and layoff",
            "management rights",
        ],
        "source_ref_families": [
            "U.S. Department of Labor Office of Labor-Management Standards "
            "public CBA collection",
            "National Labor Relations Board public case records",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:employment.offer_letter",
        "title": "Employment Offer Letter",
        "industry": "employment_hr",
        "description": (
            "A letter extending an employment offer; extraction targets the "
            "candidate, position and start date, base compensation, sign-on "
            "and bonus terms, contingencies such as background checks, and "
            "the response deadline."
        ),
        "typical_formats": ["pdf_native", "docx", "email"],
        "governing_law_sensitivity": "medium",
        "risk_class": "low",
        "applicable_field_families": [
            "parties", "dates", "monetary", "employment_specific",
            "term_termination", "conditions", "signatures_execution",
        ],
        "key_clause_types": [
            "position and start date",
            "base compensation and bonus",
            "contingencies and conditions",
            "at-will acknowledgment",
        ],
        "source_ref_families": [
            "human resources standard offer letter templates",
            "state employment law model form guidance",
        ],
        "human_review_required": False,
    },
    {
        "doc_type_id": "doctype:employment.severance_agreement",
        "title": "Severance and Release Agreement",
        "industry": "employment_hr",
        "description": (
            "A separation agreement providing severance in exchange for a "
            "release of claims; extraction targets the severance amount and "
            "schedule, released claims, revocation and consideration "
            "periods, non-disparagement, and continuing confidentiality."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "obligations",
            "employment_specific", "confidentiality", "dispute_resolution",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "severance payment and schedule",
            "general release of claims",
            "revocation and consideration period",
            "non-disparagement",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "EEOC guidance on age-discrimination waiver requirements",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:employment.non_compete_agreement",
        "title": "Non-Compete and Restrictive Covenant Agreement",
        "industry": "employment_hr",
        "description": (
            "An agreement restricting an employee's post-employment "
            "competition, solicitation, and disclosure; extraction targets "
            "the restricted activities, geographic scope, duration, "
            "consideration, and non-solicitation terms."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "obligations", "term_termination",
            "employment_specific", "confidentiality",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "non-competition restriction",
            "non-solicitation of employees and customers",
            "geographic and temporal scope",
            "consideration and enforceability",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "state non-compete statutory and case-law references",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:employment.invention_assignment_agreement",
        "title": "Employee Invention Assignment Agreement",
        "industry": "employment_hr",
        "description": (
            "An agreement assigning employee inventions and work product to "
            "the employer; extraction targets the assignment scope, prior "
            "inventions carve-outs, disclosure duties, and statutory "
            "exclusions for inventions developed on personal time."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "obligations", "ip_specific",
            "confidentiality", "employment_specific",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "assignment of inventions",
            "prior inventions disclosure",
            "cooperation in prosecution",
            "statutory exclusion notice",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "state invention-assignment statutory references",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:employment.stock_option_award_agreement",
        "title": "Stock Option Award Agreement",
        "industry": "employment_hr",
        "description": (
            "An equity award granting options under an incentive plan; "
            "extraction targets the number of shares, exercise price, grant "
            "and vesting dates, vesting schedule, expiration, and "
            "termination treatment."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "medium",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "monetary", "quantities",
            "employment_specific", "financial_specific", "term_termination",
            "conditions", "signatures_execution",
        ],
        "key_clause_types": [
            "number of shares and exercise price",
            "vesting schedule",
            "expiration and exercise window",
            "termination and forfeiture",
        ],
        "source_ref_families": [
            "SEC EDGAR equity incentive plan exhibit filings",
            "SEC EDGAR material contract exhibits (Item 601)",
        ],
        "human_review_required": False,
    },
    # ------------------------------------------------------------------
    # real_estate
    # ------------------------------------------------------------------
    {
        "doc_type_id": "doctype:real_estate.commercial_office_lease",
        "title": "Commercial Office Lease",
        "industry": "real_estate",
        "description": (
            "A lease of office space; extraction targets the landlord and "
            "tenant, premises and rentable area, base and additional rent, "
            "term and renewal options, operating-expense pass-throughs, and "
            "the insurance and indemnity provisions."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "quantities", "term_termination",
            "real_estate_specific", "property_description", "obligations",
            "indemnification_liability", "insurance_specific",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "premises and rentable area",
            "base rent and escalations",
            "operating expenses and CAM",
            "term and renewal options",
            "insurance and indemnity",
        ],
        "source_ref_families": [
            "commercial real estate association model leases",
            "SEC EDGAR material contract exhibits (Item 601)",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:real_estate.retail_lease",
        "title": "Retail and Shopping Center Lease",
        "industry": "real_estate",
        "description": (
            "A lease of retail space, often with percentage rent; extraction "
            "targets the premises and area, base and percentage rent, use "
            "and exclusivity, co-tenancy conditions, term, and common-area "
            "maintenance obligations."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "quantities", "term_termination",
            "real_estate_specific", "property_description", "obligations",
            "conditions", "indemnification_liability", "insurance_specific",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "premises and permitted use",
            "base and percentage rent",
            "exclusive use and co-tenancy",
            "common area maintenance",
        ],
        "source_ref_families": [
            "commercial real estate association model leases",
            "retail lease standard form references",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:real_estate.ground_lease",
        "title": "Ground Lease",
        "industry": "real_estate",
        "description": (
            "A long-term lease of land on which the tenant builds and owns "
            "improvements; extraction targets the demised land, term "
            "(commonly decades), rent and reset mechanics, improvement and "
            "reversion terms, and financing and leasehold-mortgage rights."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "term_termination",
            "real_estate_specific", "property_description", "obligations",
            "indemnification_liability", "governing_law_jurisdiction",
            "signatures_execution",
        ],
        "key_clause_types": [
            "demised premises and legal description",
            "term and rent reset",
            "improvements and reversion",
            "leasehold mortgage protections",
        ],
        "source_ref_families": [
            "commercial real estate association model leases",
            "SEC EDGAR material contract exhibits (Item 601)",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:real_estate.residential_lease",
        "title": "Residential Lease Agreement",
        "industry": "real_estate",
        "description": (
            "A lease of a dwelling unit; extraction targets the landlord and "
            "tenant, unit address, monthly rent and deposit, lease term, and "
            "the maintenance and occupancy obligations."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "monetary", "term_termination",
            "real_estate_specific", "property_description", "obligations",
            "signatures_execution",
        ],
        "key_clause_types": [
            "premises and occupancy",
            "rent and security deposit",
            "term and renewal",
            "maintenance and repair",
        ],
        "source_ref_families": [
            "state bar association and legal aid residential lease forms",
            "state landlord-tenant statutory form references",
        ],
        "human_review_required": False,
    },
    {
        "doc_type_id": "doctype:real_estate.purchase_and_sale_agreement",
        "title": "Real Property Purchase and Sale Agreement",
        "industry": "real_estate",
        "description": (
            "An agreement to buy and sell real property; extraction targets "
            "the buyer and seller, purchase price and deposit, property "
            "description, contingencies and closing date, representations, "
            "and title and survey provisions."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "conditions",
            "real_estate_specific", "property_description",
            "representations_warranties", "term_termination",
            "indemnification_liability", "governing_law_jurisdiction",
            "signatures_execution",
        ],
        "key_clause_types": [
            "purchase price and deposit",
            "property description",
            "contingencies and due diligence",
            "closing and possession",
            "representations and warranties",
        ],
        "source_ref_families": [
            "commercial real estate association model purchase agreements",
            "state bar association real property forms",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:real_estate.warranty_deed",
        "title": "Warranty Deed",
        "industry": "real_estate",
        "description": (
            "A recorded instrument conveying real property with covenants of "
            "title; extraction targets the grantor and grantee, legal "
            "description, consideration, warranty covenants, and the "
            "recording and notarization details."
        ),
        "typical_formats": ["pdf_scanned", "image", "pdf_native"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "property_description",
            "real_estate_specific", "representations_warranties",
            "signatures_execution",
        ],
        "key_clause_types": [
            "granting clause",
            "legal description",
            "warranty covenants",
            "acknowledgment and recording",
        ],
        "source_ref_families": [
            "county recorder and register of deeds recorded instruments",
            "state statutory deed form references",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:real_estate.quitclaim_deed",
        "title": "Quitclaim Deed",
        "industry": "real_estate",
        "description": (
            "A recorded instrument conveying whatever interest the grantor "
            "holds without title warranties; extraction targets the grantor "
            "and grantee, legal description, consideration, and the "
            "recording and notarization details."
        ),
        "typical_formats": ["pdf_scanned", "image", "pdf_native"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "property_description",
            "real_estate_specific", "signatures_execution",
        ],
        "key_clause_types": [
            "granting and quitclaim language",
            "legal description",
            "acknowledgment and recording",
        ],
        "source_ref_families": [
            "county recorder and register of deeds recorded instruments",
            "state statutory deed form references",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:real_estate.deed_of_trust",
        "title": "Deed of Trust or Mortgage",
        "industry": "real_estate",
        "description": (
            "A recorded security instrument pledging real property to secure "
            "a loan; extraction targets the borrower, lender, and trustee, "
            "secured amount, property description, payment and default "
            "terms, and power-of-sale provisions."
        ),
        "typical_formats": ["pdf_scanned", "pdf_native", "image"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "property_description",
            "real_estate_specific", "financial_specific", "obligations",
            "term_termination", "governing_law_jurisdiction",
            "signatures_execution",
        ],
        "key_clause_types": [
            "secured obligation and amount",
            "legal description of encumbered property",
            "payment and default",
            "power of sale and foreclosure",
        ],
        "source_ref_families": [
            "county recorder and register of deeds recorded instruments",
            "Fannie Mae and Freddie Mac uniform security instruments",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:real_estate.easement_agreement",
        "title": "Easement Agreement",
        "industry": "real_estate",
        "description": (
            "A recorded grant of a limited right to use another's land; "
            "extraction targets the grantor and grantee, easement purpose "
            "and scope, the servient and dominant parcels, maintenance "
            "obligations, and duration."
        ),
        "typical_formats": ["pdf_scanned", "pdf_native", "image"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "property_description",
            "real_estate_specific", "obligations", "term_termination",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "grant and purpose of easement",
            "location and legal description",
            "maintenance and repair obligations",
            "duration and termination",
        ],
        "source_ref_families": [
            "county recorder and register of deeds recorded instruments",
            "state statutory easement form references",
        ],
        "human_review_required": True,
    },
    # ------------------------------------------------------------------
    # oil_gas_energy
    # ------------------------------------------------------------------
    {
        "doc_type_id": "doctype:oil_gas.oil_and_gas_lease",
        "title": "Oil and Gas Lease",
        "industry": "oil_gas_energy",
        "description": (
            "A lease granting the right to explore for and produce oil and "
            "gas; extraction targets the lessor and lessee, leased premises "
            "and legal description, primary term, royalty fraction, bonus "
            "and delay-rental terms, and habendum and Pugh clauses."
        ),
        "typical_formats": ["pdf_scanned", "pdf_native", "image"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "term_termination",
            "oil_gas_specific", "property_description", "real_estate_specific",
            "obligations", "governing_law_jurisdiction",
            "signatures_execution",
        ],
        "key_clause_types": [
            "granting clause and leased substances",
            "primary term and habendum",
            "royalty clause",
            "delay rental and shut-in royalty",
            "Pugh clause",
        ],
        "source_ref_families": [
            "state statutory oil-and-gas lease forms",
            "county recorder and register of deeds recorded instruments",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:oil_gas.mineral_deed",
        "title": "Mineral Deed",
        "industry": "oil_gas_energy",
        "description": (
            "A recorded instrument conveying mineral interests; extraction "
            "targets the grantor and grantee, mineral-interest fraction "
            "conveyed, legal description of the lands, reservations, and the "
            "recording details."
        ),
        "typical_formats": ["pdf_scanned", "image", "pdf_native"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "oil_gas_specific",
            "property_description", "real_estate_specific",
            "signatures_execution",
        ],
        "key_clause_types": [
            "granting clause and mineral fraction",
            "legal description of lands",
            "reservations and exceptions",
            "acknowledgment and recording",
        ],
        "source_ref_families": [
            "county recorder and register of deeds recorded instruments",
            "state statutory mineral conveyance form references",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:oil_gas.joint_operating_agreement",
        "title": "Joint Operating Agreement",
        "industry": "oil_gas_energy",
        "description": (
            "An agreement governing joint development of an oil and gas "
            "unit; extraction targets the operator and non-operators, "
            "working-interest fractions, the contract area, cost sharing and "
            "non-consent penalties, and the accounting procedure."
        ),
        "typical_formats": ["pdf_native", "pdf_scanned", "docx"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "quantities", "obligations",
            "term_termination", "oil_gas_specific", "property_description",
            "indemnification_liability", "dispute_resolution",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "contract area and interests",
            "operator designation and duties",
            "cost sharing and non-consent penalties",
            "accounting procedure",
        ],
        "source_ref_families": [
            "AAPL model form operating agreements (e.g., Form 610)",
            "SEC EDGAR material contract exhibits (Item 601)",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:oil_gas.farmout_agreement",
        "title": "Farmout Agreement",
        "industry": "oil_gas_energy",
        "description": (
            "An agreement under which a lease owner assigns an interest in "
            "exchange for drilling; extraction targets the farmor and "
            "farmee, earning obligations and drilling commitments, the "
            "assigned interest, and reversionary and continuous-operations "
            "terms."
        ),
        "typical_formats": ["pdf_native", "pdf_scanned", "docx"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "conditions", "obligations",
            "oil_gas_specific", "property_description", "term_termination",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "drilling and earning obligations",
            "assignment of earned interest",
            "reversionary interest",
            "continuous operations",
        ],
        "source_ref_families": [
            "AAPL model form farmout agreements",
            "SEC EDGAR material contract exhibits (Item 601)",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:oil_gas.right_of_way_agreement",
        "title": "Pipeline Right-of-Way and Surface Use Agreement",
        "industry": "oil_gas_energy",
        "description": (
            "A recorded grant of a corridor across land for pipelines or "
            "facilities; extraction targets the grantor and grantee, "
            "easement width and route, consideration and damage payments, "
            "surface-use restrictions, and restoration obligations."
        ),
        "typical_formats": ["pdf_scanned", "pdf_native", "image"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "property_description",
            "real_estate_specific", "oil_gas_specific", "obligations",
            "term_termination", "governing_law_jurisdiction",
            "signatures_execution",
        ],
        "key_clause_types": [
            "grant and route description",
            "easement width and facilities",
            "consideration and damage payments",
            "surface use and restoration",
        ],
        "source_ref_families": [
            "county recorder and register of deeds recorded instruments",
            "state statutory right-of-way form references",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:oil_gas.division_order",
        "title": "Division Order",
        "industry": "oil_gas_energy",
        "description": (
            "A statement directing the distribution of production proceeds; "
            "extraction targets the owner, operator or purchaser, the "
            "well or unit, decimal interest, product type, and payment "
            "instructions."
        ),
        "typical_formats": ["pdf_scanned", "pdf_native", "image"],
        "governing_law_sensitivity": "high",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "monetary", "quantities", "oil_gas_specific",
            "property_description", "identifiers", "signatures_execution",
        ],
        "key_clause_types": [
            "owner and interest identification",
            "decimal interest",
            "well or unit identification",
            "payment instructions",
        ],
        "source_ref_families": [
            "state oil and gas commission division order records",
            "state statutory division order form references",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:oil_gas.drilling_contract",
        "title": "Drilling Contract",
        "industry": "oil_gas_energy",
        "description": (
            "An agreement engaging a drilling contractor to drill a well; "
            "extraction targets the operator and contractor, the well and "
            "depth, day rate or footage rate, the rig and equipment, and "
            "the risk-allocation and indemnity provisions."
        ),
        "typical_formats": ["pdf_native", "pdf_scanned", "docx"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "quantities", "obligations",
            "term_termination", "oil_gas_specific",
            "indemnification_liability", "governing_law_jurisdiction",
            "signatures_execution",
        ],
        "key_clause_types": [
            "well location and depth",
            "day rate and footage rate",
            "rig and equipment specification",
            "knock-for-knock indemnity",
        ],
        "source_ref_families": [
            "IADC model drilling contract forms",
            "SEC EDGAR material contract exhibits (Item 601)",
        ],
        "human_review_required": True,
    },
    # ------------------------------------------------------------------
    # commercial_general
    # ------------------------------------------------------------------
    {
        "doc_type_id": "doctype:commercial.sales_agreement",
        "title": "Sale of Goods Agreement",
        "industry": "commercial_general",
        "description": (
            "An agreement for the sale of goods; extraction targets the "
            "buyer and seller, goods and quantities, price and payment, "
            "delivery and risk of loss, and the warranty and limitation-of- "
            "liability terms."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "medium",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "monetary", "quantities", "obligations",
            "term_termination", "representations_warranties",
            "indemnification_liability", "governing_law_jurisdiction",
            "signatures_execution",
        ],
        "key_clause_types": [
            "description and quantity of goods",
            "price and payment terms",
            "delivery and risk of loss",
            "warranties and disclaimers",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "Uniform Commercial Code Article 2 form references",
        ],
        "human_review_required": False,
    },
    {
        "doc_type_id": "doctype:commercial.distribution_agreement",
        "title": "Distribution Agreement",
        "industry": "commercial_general",
        "description": (
            "An agreement appointing a distributor to resell a supplier's "
            "products; extraction targets the parties, territory and "
            "exclusivity, pricing and minimums, term and termination, and "
            "the indemnity and trademark-use terms."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "monetary", "quantities", "obligations",
            "term_termination", "indemnification_liability",
            "confidentiality", "governing_law_jurisdiction",
            "signatures_execution",
        ],
        "key_clause_types": [
            "appointment and territory",
            "exclusivity and minimums",
            "pricing and payment",
            "term and termination",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "industry standard distribution agreement templates",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:commercial.franchise_agreement",
        "title": "Franchise Agreement",
        "industry": "commercial_general",
        "description": (
            "An agreement licensing a franchisee to operate under a brand "
            "and system; extraction targets the parties, initial and royalty "
            "fees, territory, term and renewal, system standards, and the "
            "trademark and termination provisions."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "obligations", "term_termination",
            "ip_specific", "indemnification_liability", "dispute_resolution",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "grant of franchise and territory",
            "initial and royalty fees",
            "system standards and operations",
            "trademark license and termination",
        ],
        "source_ref_families": [
            "FTC Franchise Rule disclosure document references",
            "SEC EDGAR material contract exhibits (Item 601)",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:commercial.joint_venture_agreement",
        "title": "Joint Venture Agreement",
        "industry": "commercial_general",
        "description": (
            "An agreement forming a joint venture between businesses; "
            "extraction targets the venturers, capital contributions, "
            "governance and profit sharing, term, exclusivity, and the "
            "deadlock and exit provisions."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "obligations", "term_termination",
            "representations_warranties", "confidentiality",
            "dispute_resolution", "governing_law_jurisdiction",
            "signatures_execution",
        ],
        "key_clause_types": [
            "capital contributions",
            "governance and management",
            "profit and loss sharing",
            "deadlock and exit",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "industry standard joint venture agreement templates",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:commercial.terms_of_service",
        "title": "Terms of Service",
        "industry": "commercial_general",
        "description": (
            "The standard terms governing use of a product or online "
            "service; extraction targets the service provider, acceptable "
            "use, disclaimers and liability limits, termination, and the "
            "dispute-resolution and governing-law provisions."
        ),
        "typical_formats": ["html", "pdf_native", "docx"],
        "governing_law_sensitivity": "medium",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "obligations", "term_termination",
            "indemnification_liability", "confidentiality",
            "dispute_resolution", "governing_law_jurisdiction",
        ],
        "key_clause_types": [
            "acceptable use",
            "disclaimers and limitation of liability",
            "termination and suspension",
            "arbitration and governing law",
        ],
        "source_ref_families": [
            "publicly posted online terms of service",
            "industry standard terms of service templates",
        ],
        "human_review_required": False,
    },
    # ------------------------------------------------------------------
    # financial_lending
    # ------------------------------------------------------------------
    {
        "doc_type_id": "doctype:finance.credit_agreement",
        "title": "Loan and Credit Agreement",
        "industry": "financial_lending",
        "description": (
            "A commercial financing agreement between a borrower and "
            "lenders; extraction targets the facility amount and type, "
            "interest rate and margin, maturity, financial covenants, "
            "conditions precedent, and events of default."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "financial_specific",
            "obligations", "conditions", "representations_warranties",
            "term_termination", "indemnification_liability",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "facility amount and type",
            "interest rate and fees",
            "financial covenants",
            "conditions precedent",
            "events of default",
        ],
        "source_ref_families": [
            "SEC EDGAR credit agreement exhibit filings",
            "SEC EDGAR material contract exhibits (Item 601)",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:finance.promissory_note",
        "title": "Promissory Note",
        "industry": "financial_lending",
        "description": (
            "A written promise to repay a debt; extraction targets the "
            "maker and payee, principal amount, interest rate, maturity "
            "date, payment schedule, and default and acceleration terms."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "financial_specific",
            "obligations", "term_termination", "governing_law_jurisdiction",
            "signatures_execution",
        ],
        "key_clause_types": [
            "principal and interest rate",
            "maturity and payment schedule",
            "default and acceleration",
            "prepayment",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "Uniform Commercial Code Article 3 form references",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:finance.security_agreement",
        "title": "Security Agreement",
        "industry": "financial_lending",
        "description": (
            "An agreement granting a lender a security interest in "
            "collateral; extraction targets the debtor and secured party, "
            "the collateral description, the secured obligations, perfection "
            "and covenants, and default remedies."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "financial_specific",
            "property_description", "obligations",
            "representations_warranties", "governing_law_jurisdiction",
            "signatures_execution",
        ],
        "key_clause_types": [
            "grant of security interest",
            "collateral description",
            "secured obligations",
            "default and remedies",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "Uniform Commercial Code Article 9 form references",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:finance.guaranty_agreement",
        "title": "Guaranty Agreement",
        "industry": "financial_lending",
        "description": (
            "An agreement under which a guarantor promises payment of "
            "another's obligation; extraction targets the guarantor, the "
            "guaranteed obligations, whether the guaranty is of payment or "
            "collection, limits and caps, and waivers of defenses."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "financial_specific",
            "obligations", "term_termination", "governing_law_jurisdiction",
            "signatures_execution",
        ],
        "key_clause_types": [
            "guaranteed obligations",
            "guaranty of payment or collection",
            "maximum liability",
            "waiver of defenses",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "industry standard guaranty agreement templates",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:finance.safe_agreement",
        "title": "Simple Agreement for Future Equity (SAFE)",
        "industry": "financial_lending",
        "description": (
            "An early-stage financing instrument convertible into equity on "
            "a future priced round; extraction targets the investor and "
            "company, purchase amount, valuation cap and discount, and the "
            "conversion and liquidity-event triggers."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "medium",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "monetary", "financial_specific",
            "conditions", "representations_warranties", "signatures_execution",
        ],
        "key_clause_types": [
            "purchase amount",
            "valuation cap and discount",
            "conversion events",
            "liquidity and dissolution events",
        ],
        "source_ref_families": [
            "Y Combinator standard SAFE forms",
            "NVCA model venture financing documents",
        ],
        "human_review_required": False,
    },
    {
        "doc_type_id": "doctype:finance.convertible_note",
        "title": "Convertible Promissory Note",
        "industry": "financial_lending",
        "description": (
            "A debt instrument convertible into equity; extraction targets "
            "the principal and interest, maturity, valuation cap and "
            "discount, qualified-financing conversion mechanics, and the "
            "default provisions."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "medium",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "financial_specific",
            "obligations", "conditions", "term_termination",
            "signatures_execution",
        ],
        "key_clause_types": [
            "principal and interest",
            "maturity date",
            "conversion on qualified financing",
            "valuation cap and discount",
        ],
        "source_ref_families": [
            "NVCA model venture financing documents",
            "SEC EDGAR material contract exhibits (Item 601)",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:finance.financing_term_sheet",
        "title": "Financing Term Sheet",
        "industry": "financial_lending",
        "description": (
            "A summary of proposed financing terms preceding definitive "
            "documents; extraction targets the amount and instrument, "
            "valuation, key economic and control terms, and the binding "
            "confidentiality and exclusivity provisions."
        ),
        "typical_formats": ["pdf_native", "docx", "email"],
        "governing_law_sensitivity": "medium",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "monetary", "financial_specific",
            "conditions", "confidentiality", "signatures_execution",
        ],
        "key_clause_types": [
            "investment amount and instrument",
            "valuation and price",
            "control and economic terms",
            "binding confidentiality and exclusivity",
        ],
        "source_ref_families": [
            "NVCA model term sheet",
            "SEC EDGAR material contract exhibits (Item 601)",
        ],
        "human_review_required": True,
    },
    # ------------------------------------------------------------------
    # corporate_governance
    # ------------------------------------------------------------------
    {
        "doc_type_id": "doctype:corporate.bylaws",
        "title": "Corporate Bylaws",
        "industry": "corporate_governance",
        "description": (
            "The internal rules governing a corporation's operation; "
            "extraction targets the corporation, board and officer "
            "structure, meeting and quorum requirements, indemnification, "
            "and amendment procedures."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "definitions", "obligations",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "board composition and powers",
            "meetings and quorum",
            "officers and duties",
            "amendment procedure",
        ],
        "source_ref_families": [
            "SEC EDGAR governance exhibit filings",
            "state corporation statute model bylaw references",
        ],
        "human_review_required": False,
    },
    {
        "doc_type_id": "doctype:corporate.operating_agreement",
        "title": "LLC Operating Agreement",
        "industry": "corporate_governance",
        "description": (
            "The governing agreement of a limited liability company; "
            "extraction targets the members and managers, capital "
            "contributions and units, allocation and distribution, "
            "management structure, and transfer restrictions."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "definitions", "obligations",
            "term_termination", "dispute_resolution",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "capital contributions and units",
            "allocations and distributions",
            "management and voting",
            "transfer restrictions",
        ],
        "source_ref_families": [
            "SEC EDGAR governance exhibit filings",
            "state LLC act model operating agreement references",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:corporate.stock_purchase_agreement",
        "title": "Stock Purchase Agreement",
        "industry": "corporate_governance",
        "description": (
            "An agreement for the purchase and sale of a company's shares; "
            "extraction targets the buyer and seller, shares and purchase "
            "price, representations and warranties, closing conditions, "
            "indemnification, and the escrow terms."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "quantities",
            "financial_specific", "representations_warranties", "conditions",
            "indemnification_liability", "term_termination",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "shares and purchase price",
            "representations and warranties",
            "closing conditions",
            "indemnification and escrow",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "NVCA model stock purchase agreement",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:corporate.asset_purchase_agreement",
        "title": "Asset Purchase Agreement",
        "industry": "corporate_governance",
        "description": (
            "An agreement to buy and sell business assets; extraction "
            "targets the buyer and seller, purchased and excluded assets, "
            "assumed liabilities, purchase price and allocation, "
            "representations, and closing conditions."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "property_description",
            "representations_warranties", "conditions",
            "indemnification_liability", "term_termination",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "purchased and excluded assets",
            "assumed liabilities",
            "purchase price and allocation",
            "representations and indemnification",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "American Bar Association model asset purchase agreement",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:corporate.merger_agreement",
        "title": "Merger Agreement",
        "industry": "corporate_governance",
        "description": (
            "An agreement setting the terms of a merger or acquisition; "
            "extraction targets the constituent parties, merger "
            "consideration and structure, representations, covenants, "
            "closing conditions, and termination and break-fee provisions."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "representations_warranties",
            "conditions", "indemnification_liability", "term_termination",
            "dispute_resolution", "governing_law_jurisdiction",
            "signatures_execution",
        ],
        "key_clause_types": [
            "merger structure and consideration",
            "representations and covenants",
            "closing conditions",
            "termination and break-up fee",
        ],
        "source_ref_families": [
            "SEC EDGAR merger agreement exhibit filings",
            "SEC EDGAR material contract exhibits (Item 601)",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:corporate.articles_of_incorporation",
        "title": "Articles of Incorporation or Certificate of Formation",
        "industry": "corporate_governance",
        "description": (
            "The charter document filed to form a corporation or company; "
            "extraction targets the entity name and type, registered agent, "
            "authorized shares or membership structure, purpose, and the "
            "incorporator or organizer."
        ),
        "typical_formats": ["pdf_native", "pdf_scanned", "image"],
        "governing_law_sensitivity": "high",
        "risk_class": "low",
        "applicable_field_families": [
            "parties", "dates", "identifiers", "definitions",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "entity name and purpose",
            "registered agent and office",
            "authorized shares or membership",
            "incorporator or organizer",
        ],
        "source_ref_families": [
            "state secretary of state corporate formation filings",
            "state business entity public records",
        ],
        "human_review_required": False,
    },
    # ------------------------------------------------------------------
    # ip_technology
    # ------------------------------------------------------------------
    {
        "doc_type_id": "doctype:ip.ip_assignment_agreement",
        "title": "Intellectual Property Assignment Agreement",
        "industry": "ip_technology",
        "description": (
            "An agreement transferring ownership of intellectual property; "
            "extraction targets the assignor and assignee, the assigned "
            "patents, trademarks, copyrights, or trade secrets, "
            "consideration, and further-assurances obligations."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "ip_specific", "obligations",
            "representations_warranties", "confidentiality",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "assignment of intellectual property",
            "identification of assigned rights",
            "further assurances",
            "warranties of ownership",
        ],
        "source_ref_families": [
            "USPTO patent and trademark assignment recordation records",
            "U.S. Copyright Office recorded document records",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:ip.patent_license_agreement",
        "title": "Patent License Agreement",
        "industry": "ip_technology",
        "description": (
            "An agreement licensing patent rights; extraction targets the "
            "licensor and licensee, licensed patents, field and territory, "
            "exclusivity, royalty and milestone terms, and the sublicensing "
            "and indemnity provisions."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "ip_specific", "obligations",
            "term_termination", "representations_warranties",
            "indemnification_liability", "governing_law_jurisdiction",
            "signatures_execution",
        ],
        "key_clause_types": [
            "licensed patents and field of use",
            "exclusivity and territory",
            "royalties and milestones",
            "sublicensing and improvements",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "USPTO patent assignment and license recordation records",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:ip.trademark_license_agreement",
        "title": "Trademark License Agreement",
        "industry": "ip_technology",
        "description": (
            "An agreement licensing trademark rights with quality control; "
            "extraction targets the licensor and licensee, licensed marks, "
            "goods and territory, royalty terms, and the quality-control and "
            "trademark-use provisions."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "monetary", "ip_specific", "obligations",
            "term_termination", "representations_warranties",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "licensed marks and goods",
            "territory and exclusivity",
            "quality control",
            "royalties and reporting",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "USPTO trademark assignment and license recordation records",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:ip.software_license_agreement",
        "title": "Software License Agreement",
        "industry": "ip_technology",
        "description": (
            "An agreement licensing software to an end user or enterprise; "
            "extraction targets the licensor and licensee, license scope and "
            "restrictions, fees, warranty disclaimers, and the liability and "
            "termination provisions."
        ),
        "typical_formats": ["pdf_native", "html", "docx"],
        "governing_law_sensitivity": "medium",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "monetary", "ip_specific", "obligations",
            "term_termination", "indemnification_liability",
            "governing_law_jurisdiction",
        ],
        "key_clause_types": [
            "license grant and restrictions",
            "fees and maintenance",
            "warranty disclaimer",
            "limitation of liability",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "industry standard software license templates",
        ],
        "human_review_required": False,
    },
    {
        "doc_type_id": "doctype:ip.saas_subscription_agreement",
        "title": "SaaS Subscription Agreement",
        "industry": "ip_technology",
        "description": (
            "An agreement providing cloud software on a subscription basis; "
            "extraction targets the parties, subscription fees and term, "
            "service levels, data and security obligations, and the "
            "liability and termination provisions."
        ),
        "typical_formats": ["pdf_native", "html", "docx"],
        "governing_law_sensitivity": "medium",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "monetary", "ip_specific", "obligations",
            "term_termination", "indemnification_liability", "confidentiality",
            "dispute_resolution", "governing_law_jurisdiction",
            "signatures_execution",
        ],
        "key_clause_types": [
            "subscription and fees",
            "service levels",
            "data protection and security",
            "limitation of liability",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "industry standard SaaS subscription templates",
        ],
        "human_review_required": False,
    },
    {
        "doc_type_id": "doctype:ip.data_processing_agreement",
        "title": "Data Processing Agreement",
        "industry": "ip_technology",
        "description": (
            "A data-protection agreement between controller and processor; "
            "extraction targets the parties and roles, processing purposes "
            "and categories, subprocessor and transfer terms, security "
            "measures, and breach-notification obligations."
        ),
        "typical_formats": ["pdf_native", "docx", "html"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "obligations", "confidentiality",
            "indemnification_liability", "term_termination",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "roles and processing details",
            "subprocessors and transfers",
            "security measures",
            "breach notification and audit",
        ],
        "source_ref_families": [
            "EU standard contractual clauses and model data processing terms",
            "SEC EDGAR material contract exhibits (Item 601)",
        ],
        "human_review_required": True,
    },
    # ------------------------------------------------------------------
    # healthcare
    # ------------------------------------------------------------------
    {
        "doc_type_id": "doctype:healthcare.business_associate_agreement",
        "title": "HIPAA Business Associate Agreement",
        "industry": "healthcare",
        "description": (
            "A HIPAA-required agreement governing a business associate's "
            "handling of protected health information; extraction targets "
            "the covered entity and business associate, permitted uses, "
            "safeguards, breach-notification duties, and return or "
            "destruction on termination."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "obligations", "confidentiality",
            "indemnification_liability", "term_termination",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "permitted uses and disclosures",
            "safeguards for protected health information",
            "breach notification",
            "return or destruction on termination",
        ],
        "source_ref_families": [
            "HHS sample business associate agreement provisions",
            "SEC EDGAR material contract exhibits (Item 601)",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:healthcare.clinical_trial_agreement",
        "title": "Clinical Trial Agreement",
        "industry": "healthcare",
        "description": (
            "An agreement between a sponsor and a research site to conduct a "
            "clinical trial; extraction targets the parties, protocol and "
            "budget, payment milestones, subject-injury and indemnity terms, "
            "publication rights, and intellectual-property ownership."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "obligations", "term_termination",
            "confidentiality", "indemnification_liability", "ip_specific",
            "insurance_specific", "governing_law_jurisdiction",
            "signatures_execution",
        ],
        "key_clause_types": [
            "protocol and scope of study",
            "budget and payment milestones",
            "subject injury and indemnification",
            "publication and intellectual property",
        ],
        "source_ref_families": [
            "NIH and academic model clinical trial agreement templates",
            "SEC EDGAR material contract exhibits (Item 601)",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:healthcare.informed_consent_form",
        "title": "Informed Consent Form",
        "industry": "healthcare",
        "description": (
            "A document by which a patient or research subject consents to "
            "treatment or study participation; extraction targets the "
            "subject and site, procedure or study description, risks and "
            "benefits, voluntary-participation statement, and the signature "
            "and date."
        ),
        "typical_formats": ["pdf_scanned", "pdf_native", "image"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "definitions", "obligations",
            "confidentiality", "signatures_execution",
        ],
        "key_clause_types": [
            "description of procedure or study",
            "risks and benefits",
            "voluntary participation and withdrawal",
            "authorization and signature",
        ],
        "source_ref_families": [
            "institutional review board model consent form templates",
            "FDA informed consent guidance references",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:healthcare.physician_employment_agreement",
        "title": "Physician Employment Agreement",
        "industry": "healthcare",
        "description": (
            "An agreement engaging a physician; extraction targets the "
            "compensation and productivity terms, clinical duties, term and "
            "termination, restrictive covenants, malpractice coverage, and "
            "the referral and compliance provisions."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "obligations", "term_termination",
            "employment_specific", "confidentiality",
            "indemnification_liability", "governing_law_jurisdiction",
            "signatures_execution",
        ],
        "key_clause_types": [
            "compensation and productivity",
            "clinical duties and privileges",
            "restrictive covenants",
            "malpractice insurance and tail coverage",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "medical group standard physician agreement templates",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:healthcare.provider_network_agreement",
        "title": "Provider Network and Payer Agreement",
        "industry": "healthcare",
        "description": (
            "An agreement between a provider and a health plan for network "
            "participation; extraction targets the parties, covered "
            "services, reimbursement rates and fee schedules, term, claims "
            "and utilization terms, and the dispute-resolution provisions."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "obligations", "term_termination",
            "indemnification_liability", "dispute_resolution",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "covered services and network participation",
            "reimbursement rates and fee schedule",
            "claims and utilization management",
            "term and termination",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "managed care standard provider agreement templates",
        ],
        "human_review_required": True,
    },
    # ------------------------------------------------------------------
    # government_procurement
    # ------------------------------------------------------------------
    {
        "doc_type_id": "doctype:govcon.government_prime_contract",
        "title": "Government Prime Contract",
        "industry": "government_procurement",
        "description": (
            "A contract awarded directly by a government agency; extraction "
            "targets the contracting parties, contract and solicitation "
            "numbers, scope and deliverables, contract value and type, "
            "period of performance, and incorporated FAR and DFARS clauses."
        ),
        "typical_formats": ["pdf_native", "pdf_scanned", "docx"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "quantities", "obligations",
            "term_termination", "representations_warranties",
            "indemnification_liability", "governing_law_jurisdiction",
            "signatures_execution",
        ],
        "key_clause_types": [
            "statement of work and deliverables",
            "contract type and value",
            "period of performance",
            "incorporated FAR and DFARS clauses",
        ],
        "source_ref_families": [
            "System for Award Management (SAM.gov) contract records",
            "FAR and DFARS clause references",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:govcon.request_for_proposal",
        "title": "Request for Proposal",
        "industry": "government_procurement",
        "description": (
            "A solicitation inviting offers for goods or services; "
            "extraction targets the issuing agency, solicitation number, "
            "scope and requirements, evaluation criteria, submission "
            "deadline, and mandatory terms."
        ),
        "typical_formats": ["pdf_native", "pdf_scanned", "docx"],
        "governing_law_sensitivity": "medium",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "monetary", "quantities", "obligations",
            "conditions", "signatures_execution",
        ],
        "key_clause_types": [
            "scope and requirements",
            "evaluation criteria",
            "submission instructions and deadline",
            "mandatory terms and certifications",
        ],
        "source_ref_families": [
            "System for Award Management (SAM.gov) solicitation records",
            "agency electronic procurement portals",
        ],
        "human_review_required": False,
    },
    {
        "doc_type_id": "doctype:govcon.government_subcontract",
        "title": "Government Subcontract",
        "industry": "government_procurement",
        "description": (
            "A subcontract issued under a government prime contract; "
            "extraction targets the prime and subcontractor, flow-down "
            "clauses, scope and price, period of performance, and the "
            "compliance and audit provisions."
        ),
        "typical_formats": ["pdf_native", "pdf_scanned", "docx"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "quantities", "obligations",
            "term_termination", "indemnification_liability",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "scope and price",
            "flow-down clauses",
            "period of performance",
            "compliance and audit rights",
        ],
        "source_ref_families": [
            "FAR and DFARS clause references",
            "System for Award Management (SAM.gov) contract records",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:govcon.grant_agreement",
        "title": "Federal Grant or Cooperative Agreement",
        "industry": "government_procurement",
        "description": (
            "An award of federal financial assistance; extraction targets "
            "the awarding agency and recipient, award amount and budget "
            "period, allowable costs, reporting requirements, and the terms "
            "and conditions incorporated by reference."
        ),
        "typical_formats": ["pdf_native", "pdf_scanned", "docx"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "obligations", "conditions",
            "term_termination", "governing_law_jurisdiction",
            "signatures_execution",
        ],
        "key_clause_types": [
            "award amount and budget period",
            "allowable costs",
            "reporting requirements",
            "terms and conditions",
        ],
        "source_ref_families": [
            "USAspending.gov and agency grant award records",
            "Uniform Guidance (2 CFR 200) references",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:govcon.task_order",
        "title": "Task or Delivery Order",
        "industry": "government_procurement",
        "description": (
            "An order placed against an indefinite-delivery contract; "
            "extraction targets the order and base contract numbers, the "
            "ordered work or supplies, quantities and price, and the "
            "delivery schedule."
        ),
        "typical_formats": ["pdf_native", "pdf_scanned", "docx"],
        "governing_law_sensitivity": "medium",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "monetary", "quantities", "obligations",
            "term_termination", "signatures_execution",
        ],
        "key_clause_types": [
            "ordered work or supplies",
            "quantities and price",
            "delivery schedule",
            "reference to base contract",
        ],
        "source_ref_families": [
            "System for Award Management (SAM.gov) contract records",
            "FAR and DFARS clause references",
        ],
        "human_review_required": False,
    },
    # ------------------------------------------------------------------
    # insurance
    # ------------------------------------------------------------------
    {
        "doc_type_id": "doctype:insurance.property_casualty_policy",
        "title": "Property and Casualty Insurance Policy",
        "industry": "insurance",
        "description": (
            "A policy insuring property against covered perils; extraction "
            "targets the insurer and named insured, policy number and "
            "period, covered property and perils, limits and deductibles, "
            "and the exclusions and conditions."
        ),
        "typical_formats": ["pdf_native", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "insurance_specific",
            "obligations", "term_termination", "conditions", "definitions",
            "governing_law_jurisdiction",
        ],
        "key_clause_types": [
            "declarations and named insured",
            "covered property and perils",
            "limits and deductibles",
            "exclusions and conditions",
        ],
        "source_ref_families": [
            "state insurance department filed form and rate records",
            "ISO standard policy form references",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:insurance.general_liability_policy",
        "title": "Commercial General Liability Policy",
        "industry": "insurance",
        "description": (
            "A policy insuring against third-party bodily injury and "
            "property damage claims; extraction targets the insurer and "
            "insured, policy period, coverage parts, per-occurrence and "
            "aggregate limits, additional insureds, and exclusions."
        ),
        "typical_formats": ["pdf_native", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "insurance_specific",
            "obligations", "term_termination", "conditions", "definitions",
            "indemnification_liability", "governing_law_jurisdiction",
        ],
        "key_clause_types": [
            "coverage parts and insuring agreement",
            "per-occurrence and aggregate limits",
            "additional insureds",
            "exclusions",
        ],
        "source_ref_families": [
            "state insurance department filed form and rate records",
            "ISO standard commercial general liability form references",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:insurance.life_insurance_policy",
        "title": "Life Insurance Policy",
        "industry": "insurance",
        "description": (
            "A policy paying a death benefit to a beneficiary; extraction "
            "targets the insurer, insured, and owner, the face amount and "
            "premium, the beneficiary designation, and the contestability "
            "and exclusion provisions."
        ),
        "typical_formats": ["pdf_native", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "insurance_specific",
            "term_termination", "conditions", "definitions",
            "signatures_execution",
        ],
        "key_clause_types": [
            "face amount and premium",
            "beneficiary designation",
            "contestability period",
            "exclusions",
        ],
        "source_ref_families": [
            "state insurance department filed form and rate records",
            "NAIC model policy form references",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:insurance.health_insurance_policy",
        "title": "Health Insurance Policy or Certificate of Coverage",
        "industry": "insurance",
        "description": (
            "A policy or certificate describing health benefits; extraction "
            "targets the insurer and member, covered benefits, premiums and "
            "cost-sharing, exclusions and limitations, and the eligibility "
            "and appeals provisions."
        ),
        "typical_formats": ["pdf_native", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "insurance_specific",
            "obligations", "term_termination", "conditions", "definitions",
        ],
        "key_clause_types": [
            "covered benefits",
            "premiums and cost sharing",
            "exclusions and limitations",
            "eligibility and appeals",
        ],
        "source_ref_families": [
            "state insurance department filed form and rate records",
            "summary of benefits and coverage standard references",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:insurance.certificate_of_insurance",
        "title": "Certificate of Insurance",
        "industry": "insurance",
        "description": (
            "A one-page summary evidencing active coverage; extraction "
            "targets the insured and certificate holder, insurers and policy "
            "numbers, coverage types and limits, effective and expiration "
            "dates, and additional-insured status."
        ),
        "typical_formats": ["pdf_native", "pdf_scanned", "image"],
        "governing_law_sensitivity": "low",
        "risk_class": "low",
        "applicable_field_families": [
            "parties", "dates", "monetary", "insurance_specific",
            "identifiers", "signatures_execution",
        ],
        "key_clause_types": [
            "insurers and policy numbers",
            "coverage types and limits",
            "effective and expiration dates",
            "certificate holder and additional insured",
        ],
        "source_ref_families": [
            "ACORD standard certificate of insurance forms",
            "industry standard certificate templates",
        ],
        "human_review_required": False,
    },
    {
        "doc_type_id": "doctype:insurance.surety_bond",
        "title": "Surety Bond",
        "industry": "insurance",
        "description": (
            "A three-party bond guaranteeing an obligor's performance or "
            "payment; extraction targets the principal, obligee, and surety, "
            "the bond penal sum, the bonded obligation, effective date, and "
            "claim and release conditions."
        ),
        "typical_formats": ["pdf_native", "pdf_scanned", "image"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "insurance_specific",
            "obligations", "term_termination", "signatures_execution",
        ],
        "key_clause_types": [
            "principal, obligee, and surety",
            "penal sum",
            "bonded obligation",
            "claim and release conditions",
        ],
        "source_ref_families": [
            "surety bond standard forms (e.g., AIA A312 bond references)",
            "state statutory bond form references",
        ],
        "human_review_required": True,
    },
    # ------------------------------------------------------------------
    # litigation_disputes
    # ------------------------------------------------------------------
    {
        "doc_type_id": "doctype:litigation.settlement_agreement",
        "title": "Settlement and Release Agreement",
        "industry": "litigation_disputes",
        "description": (
            "An agreement resolving a dispute in exchange for a release; "
            "extraction targets the settling parties, settlement amount and "
            "payment terms, scope of released claims, confidentiality, and "
            "the dismissal and non-admission provisions."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "obligations", "confidentiality",
            "dispute_resolution", "governing_law_jurisdiction",
            "signatures_execution",
        ],
        "key_clause_types": [
            "settlement payment",
            "release of claims",
            "confidentiality and non-disparagement",
            "dismissal and non-admission",
        ],
        "source_ref_families": [
            "court electronic filing dockets (PACER and state e-filing)",
            "SEC EDGAR material contract exhibits (Item 601)",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:litigation.arbitration_agreement",
        "title": "Arbitration Agreement",
        "industry": "litigation_disputes",
        "description": (
            "An agreement to resolve disputes by binding arbitration; "
            "extraction targets the parties, scope of covered disputes, the "
            "arbitration rules and forum, seat and number of arbitrators, "
            "and any class-action waiver."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "obligations", "dispute_resolution",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "scope of covered disputes",
            "arbitration rules and forum",
            "seat and arbitrator selection",
            "class action waiver",
        ],
        "source_ref_families": [
            "AAA and JAMS model arbitration clauses and rules",
            "SEC EDGAR material contract exhibits (Item 601)",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:litigation.civil_complaint",
        "title": "Civil Complaint or Petition",
        "industry": "litigation_disputes",
        "description": (
            "A pleading commencing a civil lawsuit; extraction targets the "
            "caption and parties, court and case number, causes of action, "
            "factual allegations, and the relief and damages demanded."
        ),
        "typical_formats": ["pdf_native", "pdf_scanned", "html"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "identifiers", "monetary",
            "dispute_resolution",
        ],
        "key_clause_types": [
            "caption and parties",
            "jurisdiction and venue",
            "causes of action",
            "prayer for relief",
        ],
        "source_ref_families": [
            "court electronic filing dockets (PACER and state e-filing)",
            "public court records repositories",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:litigation.subpoena",
        "title": "Subpoena",
        "industry": "litigation_disputes",
        "description": (
            "A command to testify or produce documents; extraction targets "
            "the issuing court and case, the recipient, the testimony or "
            "documents demanded, the compliance date and place, and the "
            "objection procedure."
        ),
        "typical_formats": ["pdf_native", "pdf_scanned", "image"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "identifiers", "obligations",
            "dispute_resolution",
        ],
        "key_clause_types": [
            "recipient and issuing authority",
            "documents or testimony demanded",
            "compliance date and place",
            "objection procedure",
        ],
        "source_ref_families": [
            "court electronic filing dockets (PACER and state e-filing)",
            "federal and state rules of civil procedure form references",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:litigation.court_judgment",
        "title": "Court Order or Judgment",
        "industry": "litigation_disputes",
        "description": (
            "A court's ruling or final judgment; extraction targets the "
            "court and case number, the parties, the disposition, monetary "
            "award or relief granted, and the entry date and effective "
            "terms."
        ),
        "typical_formats": ["pdf_native", "pdf_scanned", "html"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "identifiers", "obligations",
            "dispute_resolution",
        ],
        "key_clause_types": [
            "disposition and holding",
            "monetary award or relief",
            "effective and entry date",
            "post-judgment terms",
        ],
        "source_ref_families": [
            "court electronic filing dockets (PACER and state e-filing)",
            "published court opinion repositories",
        ],
        "human_review_required": True,
    },
    # ------------------------------------------------------------------
    # supply_chain_logistics
    # ------------------------------------------------------------------
    {
        "doc_type_id": "doctype:supply_chain.master_supply_agreement",
        "title": "Master Supply Agreement",
        "industry": "supply_chain_logistics",
        "description": (
            "A framework agreement governing recurring supply of goods; "
            "extraction targets the buyer and supplier, pricing and volume "
            "commitments, forecasting and delivery terms, quality and "
            "warranty obligations, and the indemnity provisions."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "quantities", "obligations",
            "term_termination", "representations_warranties",
            "indemnification_liability", "governing_law_jurisdiction",
            "signatures_execution",
        ],
        "key_clause_types": [
            "pricing and volume commitments",
            "forecasting and delivery",
            "quality and warranty",
            "indemnification",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "industry standard supply agreement templates",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:supply_chain.purchase_order",
        "title": "Purchase Order",
        "industry": "supply_chain_logistics",
        "description": (
            "A buyer's order to purchase goods or services; extraction "
            "targets the buyer and seller, PO number, line items with "
            "quantities and unit prices, total amount, delivery terms, and "
            "requested delivery date."
        ),
        "typical_formats": ["pdf_native", "pdf_scanned", "email"],
        "governing_law_sensitivity": "low",
        "risk_class": "low",
        "applicable_field_families": [
            "parties", "dates", "monetary", "quantities", "identifiers",
            "obligations", "signatures_execution",
        ],
        "key_clause_types": [
            "line items and quantities",
            "unit and total price",
            "delivery terms",
            "purchase order terms and conditions",
        ],
        "source_ref_families": [
            "industry standard purchase order templates",
            "Uniform Commercial Code Article 2 form references",
        ],
        "human_review_required": False,
    },
    {
        "doc_type_id": "doctype:supply_chain.bill_of_lading",
        "title": "Bill of Lading",
        "industry": "supply_chain_logistics",
        "description": (
            "A transport document evidencing receipt of goods for shipment; "
            "extraction targets the shipper, carrier, and consignee, the "
            "goods description and quantities, origin and destination, "
            "freight terms, and the tracking or bill-of-lading number."
        ),
        "typical_formats": ["pdf_scanned", "image", "pdf_native"],
        "governing_law_sensitivity": "medium",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "quantities", "identifiers",
            "property_description", "obligations", "signatures_execution",
        ],
        "key_clause_types": [
            "shipper, carrier, and consignee",
            "description and quantity of goods",
            "origin and destination",
            "freight charges and terms",
        ],
        "source_ref_families": [
            "uniform straight bill of lading standard forms",
            "carrier standard bill of lading references",
        ],
        "human_review_required": False,
    },
    {
        "doc_type_id": "doctype:supply_chain.warehouse_agreement",
        "title": "Warehouse and Storage Agreement",
        "industry": "supply_chain_logistics",
        "description": (
            "An agreement for the storage and handling of goods; extraction "
            "targets the depositor and warehouse operator, storage and "
            "handling fees, liability limits, insurance obligations, and the "
            "term and termination provisions."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "medium",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "monetary", "quantities", "obligations",
            "term_termination", "indemnification_liability",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "storage and handling fees",
            "liability and warehouse lien",
            "insurance obligations",
            "term and termination",
        ],
        "source_ref_families": [
            "Uniform Commercial Code Article 7 form references",
            "industry standard warehouse agreement templates",
        ],
        "human_review_required": False,
    },
    {
        "doc_type_id": "doctype:supply_chain.freight_transportation_agreement",
        "title": "Freight and Transportation Services Agreement",
        "industry": "supply_chain_logistics",
        "description": (
            "An agreement for carriage of goods by a motor or freight "
            "carrier; extraction targets the shipper and carrier, rates and "
            "accessorial charges, service levels, liability and cargo-claim "
            "terms, and insurance obligations."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "medium",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "monetary", "quantities", "obligations",
            "term_termination", "indemnification_liability",
            "insurance_specific", "governing_law_jurisdiction",
            "signatures_execution",
        ],
        "key_clause_types": [
            "rates and accessorial charges",
            "service levels",
            "cargo liability and claims",
            "insurance obligations",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "motor carrier standard transportation agreement templates",
        ],
        "human_review_required": False,
    },
    {
        "doc_type_id": "doctype:supply_chain.manufacturing_agreement",
        "title": "Manufacturing and OEM Agreement",
        "industry": "supply_chain_logistics",
        "description": (
            "An agreement engaging a manufacturer to produce goods to a "
            "buyer's specifications; extraction targets the parties, "
            "specifications and quality standards, pricing and minimums, "
            "tooling and intellectual-property ownership, and warranty and "
            "indemnity terms."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "quantities", "obligations",
            "term_termination", "ip_specific", "representations_warranties",
            "indemnification_liability", "governing_law_jurisdiction",
            "signatures_execution",
        ],
        "key_clause_types": [
            "specifications and quality standards",
            "pricing and minimum volumes",
            "tooling and intellectual property",
            "warranty and indemnification",
        ],
        "source_ref_families": [
            "SEC EDGAR material contract exhibits (Item 601)",
            "industry standard manufacturing agreement templates",
        ],
        "human_review_required": True,
    },
    # ------------------------------------------------------------------
    # construction
    # ------------------------------------------------------------------
    {
        "doc_type_id": "doctype:construction.prime_construction_contract",
        "title": "Prime Construction Contract",
        "industry": "construction",
        "description": (
            "An owner-contractor agreement for a construction project; "
            "extraction targets the owner and contractor, the project and "
            "scope, contract sum and payment terms, schedule and milestones, "
            "insurance and bonding, and indemnity provisions."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "quantities", "obligations",
            "term_termination", "indemnification_liability",
            "property_description", "insurance_specific", "dispute_resolution",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "scope of work",
            "contract sum and payment",
            "schedule and milestones",
            "insurance and bonding",
            "indemnification",
        ],
        "source_ref_families": [
            "AIA and ConsensusDocs standard construction contract forms",
            "SEC EDGAR material contract exhibits (Item 601)",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:construction.subcontract_agreement",
        "title": "Construction Subcontract",
        "industry": "construction",
        "description": (
            "A subcontract between a general contractor and a trade "
            "subcontractor; extraction targets the parties, subcontract "
            "scope and sum, flow-down terms, payment and retainage, "
            "insurance, and the indemnity provisions."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "quantities", "obligations",
            "term_termination", "indemnification_liability",
            "property_description", "insurance_specific",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "subcontract scope and sum",
            "flow-down provisions",
            "payment and retainage",
            "insurance and indemnity",
        ],
        "source_ref_families": [
            "AIA and ConsensusDocs standard construction subcontract forms",
            "industry standard subcontract templates",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:construction.aia_owner_contractor_agreement",
        "title": "AIA-Style Owner-Contractor Agreement",
        "industry": "construction",
        "description": (
            "A standard-form owner-contractor agreement with general "
            "conditions; extraction targets the contract sum or guaranteed "
            "maximum price, the general conditions incorporated, payment "
            "applications and retainage, changes, and the dispute-resolution "
            "provisions."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "obligations", "term_termination",
            "indemnification_liability", "property_description",
            "insurance_specific", "dispute_resolution",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "contract sum or guaranteed maximum price",
            "general conditions",
            "payment applications and retainage",
            "changes in the work",
            "dispute resolution",
        ],
        "source_ref_families": [
            "AIA standard form agreements (e.g., A101 and A201 references)",
            "ConsensusDocs standard construction contract forms",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:construction.architect_services_agreement",
        "title": "Architect and Engineer Services Agreement",
        "industry": "construction",
        "description": (
            "An agreement engaging a design professional; extraction targets "
            "the owner and design professional, the scope and phases of "
            "services, compensation, standard of care, ownership of "
            "instruments of service, and the limitation-of-liability terms."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "obligations", "term_termination",
            "indemnification_liability", "ip_specific", "property_description",
            "governing_law_jurisdiction", "signatures_execution",
        ],
        "key_clause_types": [
            "scope and phases of services",
            "compensation",
            "standard of care",
            "ownership of instruments of service",
        ],
        "source_ref_families": [
            "AIA standard form agreements (e.g., B101 references)",
            "engineering society standard agreement references (EJCDC)",
        ],
        "human_review_required": True,
    },
    {
        "doc_type_id": "doctype:construction.change_order",
        "title": "Construction Change Order",
        "industry": "construction",
        "description": (
            "A written modification to a construction contract; extraction "
            "targets the change-order number, the referenced contract, the "
            "scope of the change, the adjustment to the contract sum, and the "
            "adjustment to the contract time."
        ),
        "typical_formats": ["pdf_native", "docx", "pdf_scanned"],
        "governing_law_sensitivity": "medium",
        "risk_class": "medium",
        "applicable_field_families": [
            "parties", "dates", "monetary", "quantities", "obligations",
            "property_description", "signatures_execution",
        ],
        "key_clause_types": [
            "description of change",
            "adjustment to contract sum",
            "adjustment to contract time",
            "reference to base contract",
        ],
        "source_ref_families": [
            "AIA and ConsensusDocs standard change order forms",
            "industry standard change order templates",
        ],
        "human_review_required": False,
    },
    {
        "doc_type_id": "doctype:construction.lien_waiver",
        "title": "Mechanic's Lien Waiver",
        "industry": "construction",
        "description": (
            "A waiver releasing lien rights in exchange for payment; "
            "extraction targets the claimant and owner, the project and "
            "property, the payment amount, whether the waiver is "
            "conditional or unconditional, and the through-date."
        ),
        "typical_formats": ["pdf_native", "pdf_scanned", "image"],
        "governing_law_sensitivity": "high",
        "risk_class": "high",
        "applicable_field_families": [
            "parties", "dates", "monetary", "property_description",
            "real_estate_specific", "signatures_execution",
        ],
        "key_clause_types": [
            "conditional or unconditional waiver",
            "payment amount",
            "project and property description",
            "through-date of waiver",
        ],
        "source_ref_families": [
            "state mechanics lien statutory waiver forms",
            "county recorder and register of deeds recorded instruments",
        ],
        "human_review_required": True,
    },
]

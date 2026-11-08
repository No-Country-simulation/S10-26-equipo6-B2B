-- Migracion inicial del esquema de RepuSense (issue #38).
-- Fuente de verdad: backend/app/models/entities.py y las restricciones
-- declaradas en docs/systemDesign.md (seccion 3.3).
-- SQL plano: corre igual en Docker local (docker-entrypoint-initdb.d) y en la nube.
-- Los UUID los genera la aplicacion (uuid.uuid4), igual que el modelo ORM.

CREATE TABLE platform (
    platform_id SMALLSERIAL NOT NULL,
    name VARCHAR(50) NOT NULL UNIQUE,
    PRIMARY KEY (platform_id)
);

CREATE TABLE problem_category (
    problem_category_id SMALLSERIAL NOT NULL,
    name VARCHAR(100) NOT NULL UNIQUE,
    PRIMARY KEY (problem_category_id)
);

CREATE TABLE search (
    search_id UUID NOT NULL,
    sector VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    max_rating NUMERIC(2, 1) NOT NULL DEFAULT 3.5,
    min_reviews INTEGER NOT NULL DEFAULT 10,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (search_id)
);

CREATE TABLE business (
    business_id UUID NOT NULL,
    name VARCHAR(150) NOT NULL,
    sector VARCHAR(100),
    city VARCHAR(100),
    address VARCHAR(255),
    phone_number VARCHAR(50),
    website VARCHAR(255),
    lead_status VARCHAR(30) NOT NULL DEFAULT 'NEW',
    contacted_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (business_id)
);

CREATE TABLE business_source (
    business_source_id UUID NOT NULL,
    business_id UUID NOT NULL REFERENCES business (business_id),
    platform_id SMALLINT NOT NULL REFERENCES platform (platform_id),
    external_id VARCHAR(255) NOT NULL,
    source_url VARCHAR(500),
    rating NUMERIC(2, 1),
    total_reviews INTEGER,
    last_scraped_at TIMESTAMPTZ,
    PRIMARY KEY (business_source_id),
    CONSTRAINT uq_business_source_platform_external UNIQUE (platform_id, external_id)
);

CREATE TABLE contact (
    contact_id UUID NOT NULL,
    business_id UUID NOT NULL REFERENCES business (business_id) ON DELETE CASCADE,
    contact_type VARCHAR(20) NOT NULL,
    value VARCHAR(255) NOT NULL,
    source VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (contact_id)
);

CREATE TABLE review (
    review_id UUID NOT NULL,
    business_source_id UUID NOT NULL REFERENCES business_source (business_source_id) ON DELETE CASCADE,
    external_id VARCHAR(255) NOT NULL,
    author VARCHAR(150),
    rating SMALLINT,
    content TEXT,
    reviewed_at TIMESTAMPTZ,
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (review_id),
    CONSTRAINT uq_review_source_external UNIQUE (business_source_id, external_id)
);

CREATE TABLE search_business (
    search_id UUID NOT NULL REFERENCES search (search_id) ON DELETE CASCADE,
    business_id UUID NOT NULL REFERENCES business (business_id) ON DELETE CASCADE,
    found_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (search_id, business_id)
);

CREATE TABLE ai_analysis (
    analysis_id UUID NOT NULL,
    business_id UUID NOT NULL UNIQUE REFERENCES business (business_id),
    problem_category_id SMALLINT NOT NULL REFERENCES problem_category (problem_category_id),
    pain_points_summary TEXT,
    email_subject VARCHAR(255),
    email_first_paragraph TEXT,
    ai_model VARCHAR(50),
    generated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (analysis_id)
);

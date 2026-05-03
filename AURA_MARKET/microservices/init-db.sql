CREATE DATABASE auramarket_auth;
CREATE DATABASE auramarket_product;
CREATE DATABASE auramarket_negotiation;
CREATE DATABASE auramarket_audit;

-- Seed test users into the auth database
\c auramarket_auth;

CREATE TABLE IF NOT EXISTS utilisateurs (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    mdp_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL
);

INSERT INTO utilisateurs (id, email, mdp_hash, role) VALUES
    ('a0000000-0000-0000-0000-000000000001', 'admin@auramarket.com', '$2a$10$dummyhashforpassword123placeholder00', 'SUPERVISEUR'),
    ('a0000000-0000-0000-0000-000000000002', 'vendeur@auramarket.com', '$2a$10$dummyhashforpassword123placeholder00', 'VENDEUR'),
    ('a0000000-0000-0000-0000-000000000003', 'acheteur@auramarket.com', '$2a$10$dummyhashforpassword123placeholder00', 'ACHETEUR')
ON CONFLICT (email) DO NOTHING;

-- Seed product table schema
\c auramarket_product;

CREATE TABLE IF NOT EXISTS produits (
    id UUID PRIMARY KEY,
    titre VARCHAR(255) NOT NULL,
    description TEXT,
    prix DOUBLE PRECISION NOT NULL,
    prix_min DOUBLE PRECISION NOT NULL,
    categorie VARCHAR(255),
    image_url TEXT,
    stock INTEGER DEFAULT 0,
    statut VARCHAR(50),
    date_publication TIMESTAMP,
    vendeur_id UUID
);

CREATE TABLE IF NOT EXISTS commentaires (
    id UUID PRIMARY KEY,
    produit_id UUID,
    texte TEXT,
    note INT,
    date_publication TIMESTAMP,
    auteur_id UUID
);

-- Negotiation table schema
\c auramarket_negotiation;

CREATE TABLE IF NOT EXISTS negociations (
    id UUID PRIMARY KEY,
    acheteur_id UUID,
    produit_id UUID,
    rounds INT,
    prix_final DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS messages_negociation (
    id UUID PRIMARY KEY,
    negociation_id UUID,
    sender VARCHAR(50),
    content TEXT,
    price DOUBLE PRECISION,
    timestamp TIMESTAMP
);

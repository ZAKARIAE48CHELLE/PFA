-- Create custom types for enums
CREATE TYPE statut_commande AS ENUM 
  ('EN_ATTENTE_PAIEMENT', 'PAYEE', 'EXPIREE', 'ANNULEE');

CREATE TYPE statut_paiement AS ENUM 
  ('EN_COURS', 'CONFIRME', 'ECHOUE', 'REMBOURSE');

CREATE TYPE methode_paiement AS ENUM 
  ('CARTE', 'VIREMENT', 'PAYPAL', 'CRYPTO');

-- Create the commandes table
CREATE TABLE commandes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  reference VARCHAR(30) UNIQUE NOT NULL,
  offre_id UUID NOT NULL REFERENCES offres(id),
  acheteur_id UUID NOT NULL,
  vendeur_id UUID NOT NULL,
  produit_id UUID NOT NULL REFERENCES produits(id),
  prix_final DOUBLE PRECISION NOT NULL,
  statut VARCHAR(30) NOT NULL DEFAULT 'EN_ATTENTE_PAIEMENT',
  date_commande TIMESTAMP NOT NULL DEFAULT now(),
  date_expiration TIMESTAMP NOT NULL,
  paiement_id UUID
);

-- Create the paiements table
CREATE TABLE paiements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  commande_id UUID NOT NULL REFERENCES commandes(id),
  montant DOUBLE PRECISION NOT NULL,
  methode VARCHAR(20) NOT NULL,
  statut VARCHAR(20) NOT NULL DEFAULT 'EN_COURS',
  reference VARCHAR(30) UNIQUE NOT NULL,
  date_paiement TIMESTAMP NOT NULL DEFAULT now(),
  date_confirmation TIMESTAMP
);

-- Add cross-reference constraint (Deferred to allow circular dependency during creation if needed)
ALTER TABLE commandes 
  ADD CONSTRAINT fk_paiement 
  FOREIGN KEY (paiement_id) REFERENCES paiements(id) 
  DEFERRABLE INITIALLY DEFERRED;

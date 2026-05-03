-- Insert some sample offers
INSERT INTO offres (id, titre, description, prix_propose, prix_final, statut, date_creation, date_expiration, produit_id, acheteur_id, agent_genere)
VALUES
(gen_random_uuid(), 'Offre iPhone', 'Offre directe pour iPhone 15', 1050.00, 1050.00, 'VALIDEE', NOW(), NOW() + INTERVAL '7 days', '71d0674c-2a73-4dbd-8110-14918b5ea975', 'a0000000-0000-0000-0000-000000000003', false),
(gen_random_uuid(), 'Offre Casque', 'Proposition pour Sony WH', 300.00, 300.00, 'EN_ATTENTE', NOW(), NOW() + INTERVAL '7 days', '64397248-7616-4555-85ee-f72f339a91b6', 'a0000000-0000-0000-0000-000000000003', false);

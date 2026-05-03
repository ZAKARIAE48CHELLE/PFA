-- Insert 3 active negotiations for the acheteur
-- Nego 1: iPhone 15 Pro
INSERT INTO negociations (id, produit_id, acheteur_id, rounds, prix_final)
VALUES ('a0000000-0000-0000-0000-000000000011', '71d0674c-2a73-4dbd-8110-14918b5ea975', 'a0000000-0000-0000-0000-000000000003', 1, 1150.00);

INSERT INTO messages_negociation (id, negociation_id, sender, content, price, timestamp)
VALUES 
(gen_random_uuid(), 'a0000000-0000-0000-0000-000000000011', 'AGENT', 'Bonjour ! Je suis l''agent. Quel est votre prix ?', 1199.00, NOW()),
(gen_random_uuid(), 'a0000000-0000-0000-0000-000000000011', 'ACHETEUR', 'Je propose 1050 €', 1050.00, NOW()),
(gen_random_uuid(), 'a0000000-0000-0000-0000-000000000011', 'AGENT', 'Je peux descendre à 1150 €.', 1150.00, NOW());

-- Nego 2: MacBook Air
INSERT INTO negociations (id, produit_id, acheteur_id, rounds, prix_final)
VALUES ('a0000000-0000-0000-0000-000000000022', '69d1a0f3-dc1a-4d12-b8f9-6e77d836d6e9', 'a0000000-0000-0000-0000-000000000003', 0, 1299.00);

INSERT INTO messages_negociation (id, negociation_id, sender, content, price, timestamp)
VALUES 
(gen_random_uuid(), 'a0000000-0000-0000-0000-000000000022', 'AGENT', 'Bonjour ! Souhaitez-vous négocier ce MacBook ?', 1299.00, NOW());

-- Nego 3: Sony Headphones
INSERT INTO negociations (id, produit_id, acheteur_id, rounds, prix_final)
VALUES ('a0000000-0000-0000-0000-000000000033', '64397248-7616-4555-85ee-f72f339a91b6', 'a0000000-0000-0000-0000-000000000003', 2, 320.00);

INSERT INTO messages_negociation (id, negociation_id, sender, content, price, timestamp)
VALUES 
(gen_random_uuid(), 'a0000000-0000-0000-0000-000000000033', 'AGENT', 'Bonjour !', 349.00, NOW()),
(gen_random_uuid(), 'a0000000-0000-0000-0000-000000000033', 'ACHETEUR', 'Je propose 300 €', 300.00, NOW()),
(gen_random_uuid(), 'a0000000-0000-0000-0000-000000000033', 'AGENT', '330 € ?', 330.00, NOW()),
(gen_random_uuid(), 'a0000000-0000-0000-0000-000000000033', 'ACHETEUR', '310 €', 310.00, NOW()),
(gen_random_uuid(), 'a0000000-0000-0000-0000-000000000033', 'AGENT', 'Ok pour 320 €.', 320.00, NOW());

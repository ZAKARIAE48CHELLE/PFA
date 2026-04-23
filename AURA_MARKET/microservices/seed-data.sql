-- Insert 50 Products in various categories
INSERT INTO produits (id, titre, description, prix, prix_min, categorie, image_url, stock, statut, date_publication, vendeur_id)
VALUES
-- Electronics
(gen_random_uuid(), 'iPhone 15 Pro', 'Le dernier cri de chez Apple avec puce A17 Pro.', 1199.00, 1050.00, 'Electronique', 'https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=500', 10, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'MacBook Air M2', 'Ultra-fin, ultra-rapide avec puce M2.', 1299.00, 1150.00, 'Electronique', 'https://images.unsplash.com/photo-1611186871348-b1ce696e52c9?w=500', 5, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Sony WH-1000XM5', 'Casque à réduction de bruit de référence.', 349.00, 300.00, 'Electronique', 'https://images.unsplash.com/photo-1670057037190-27806f0e74f8?w=500', 15, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Samsung Galaxy S23', 'Ecran AMOLED magnifique et processeur puissant.', 899.00, 800.00, 'Electronique', 'https://images.unsplash.com/photo-1678911820864-e2c567c655d7?w=500', 8, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'iPad Pro 12.9', 'L''outil ultime pour les créatifs.', 1099.00, 950.00, 'Electronique', 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=500', 4, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Nintendo Switch OLED', 'Pour jouer partout avec des couleurs éclatantes.', 349.00, 310.00, 'Electronique', 'https://images.unsplash.com/photo-1612036782180-6f0b6cd846fe?w=500', 20, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'GoPro HERO12', 'Capturez vos aventures en 5.3K.', 449.00, 400.00, 'Electronique', 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=500', 12, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Dell XPS 13', 'L''excellence sous Windows.', 1149.00, 1000.00, 'Electronique', 'https://images.unsplash.com/photo-1593642632823-8f785ba67e45?w=500', 3, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'AirPods Pro 2', 'Un son spatial immersif.', 249.00, 220.00, 'Electronique', 'https://images.unsplash.com/photo-1588423770574-91993ca06f42?w=500', 30, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Apple Watch Series 9', 'Votre santé au poignet.', 449.00, 400.00, 'Electronique', 'https://images.unsplash.com/photo-1434493907317-a46b53b81822?w=500', 10, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),

-- Fashion
(gen_random_uuid(), 'Veste en cuir', 'Coupe ajustée, cuir véritable de haute qualité.', 199.00, 150.00, 'Mode', 'https://images.unsplash.com/photo-1551028711-0305df2f9fb3?w=500', 25, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Jean Slim Bleu', 'Denim stretch confortable.', 59.00, 40.00, 'Mode', 'https://images.unsplash.com/photo-1542272604-787c3835535d?w=500', 50, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Baskets Nike Air Max', 'Style iconique et confort bulle d''air.', 129.00, 100.00, 'Mode', 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500', 15, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Pull en Cachemire', 'Douceur et élégance pour l''hiver.', 89.00, 70.00, 'Mode', 'https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=500', 10, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Montre Rolex Datejust', 'Le luxe intemporel.', 8500.00, 7800.00, 'Mode', 'https://images.unsplash.com/photo-1523170335258-f5ed11844a49?w=500', 1, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Sac à main Gucci', 'Cuir italien et finitions dorées.', 1800.00, 1600.00, 'Mode', 'https://images.unsplash.com/photo-1584917033904-4b927cc13688?w=500', 2, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Echarpe en soie', 'Motifs floraux délicats.', 45.00, 30.00, 'Mode', 'https://images.unsplash.com/photo-1520903920243-00d872a2d1c9?w=500', 40, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Lunettes Ray-Ban Aviator', 'Le style classique indémodable.', 155.00, 130.00, 'Mode', 'https://images.unsplash.com/photo-1572635196237-14b3f281503f?w=500', 20, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Robe de soirée Rouge', 'Parfaite pour les grandes occasions.', 120.00, 90.00, 'Mode', 'https://images.unsplash.com/photo-1518917232263-7cda38807902?w=500', 5, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Ceinture en cuir marron', 'Sobriété et robustesse.', 35.00, 25.00, 'Mode', 'https://images.unsplash.com/photo-1554412933-514a83d2f3c8?w=500', 100, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),

-- Home & Garden
(gen_random_uuid(), 'Canapé d''angle Gris', 'Confortable et moderne.', 799.00, 650.00, 'Maison', 'https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=500', 2, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Table basse en chêne', 'Design épuré et bois massif.', 249.00, 180.00, 'Maison', 'https://images.unsplash.com/photo-1533090161767-e6ffed986c88?w=500', 5, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Robot Aspirateur iRobot', 'Nettoyage intelligent et autonome.', 499.00, 420.00, 'Maison', 'https://images.unsplash.com/photo-1518640467707-6811f4a6ab73?w=500', 10, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Machine à café Delonghi', 'L''espresso parfait à la maison.', 399.00, 350.00, 'Maison', 'https://images.unsplash.com/photo-1517668808822-9ebb02f2a0e6?w=500', 7, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Ensemble de 4 chaises', 'Velours bleu et pieds dorés.', 299.00, 250.00, 'Maison', 'https://images.unsplash.com/photo-1503602642458-232111445657?w=500', 4, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Lampe à poser industrielle', 'Style loft et lumière chaude.', 45.00, 35.00, 'Maison', 'https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=500', 15, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Plante Monstera Deliciosa', 'La touche tropicale chez vous.', 30.00, 20.00, 'Maison', 'https://images.unsplash.com/photo-1614594975525-e45190c55d0b?w=500', 20, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Set de couteaux de cuisine', 'Acier forgé de haute précision.', 149.00, 110.00, 'Maison', 'https://images.unsplash.com/photo-1593618998160-e34014e67546?w=500', 10, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Housse de couette en lin', 'Confort naturel et respirant.', 75.00, 60.00, 'Maison', 'https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?w=500', 12, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Barbecue à Gaz Weber', 'Le roi des grillades.', 599.00, 520.00, 'Maison', 'https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=500', 3, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),

-- Sports
(gen_random_uuid(), 'Vélo de route Trek', 'Léger et performant.', 1499.00, 1300.00, 'Sport', 'https://images.unsplash.com/photo-1485965120184-e220f721d03e?w=500', 2, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Tapis de course pliable', 'Pour rester en forme à la maison.', 499.00, 400.00, 'Sport', 'https://images.unsplash.com/photo-1540497077202-7c8a3999166f?w=500', 5, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Haltères 2x10kg', 'Indispensable pour la musculation.', 45.00, 35.00, 'Sport', 'https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=500', 30, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Raquette de Tennis Wilson', 'Précision et puissance.', 189.00, 160.00, 'Sport', 'https://images.unsplash.com/photo-1622279457486-62dcc4a4bd13?w=500', 10, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Ballon de Basket Spalding', 'Le ballon officiel de la NBA.', 35.00, 25.00, 'Sport', 'https://images.unsplash.com/photo-1519861531473-9200262188bf?w=500', 40, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Gants de Boxe Everlast', 'Protection et durabilité.', 55.00, 45.00, 'Sport', 'https://images.unsplash.com/photo-1509563268479-0f004cf3f58b?w=500', 20, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Planche de Surf Rip Curl', 'Pour dompter les vagues.', 450.00, 400.00, 'Sport', 'https://images.unsplash.com/photo-1502680390469-be75c86b636f?w=500', 3, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Sac de couchage Camping', 'Confortable jusqu''à -5°C.', 65.00, 50.00, 'Sport', 'https://images.unsplash.com/photo-1504280390367-361c6d9f38f4?w=500', 15, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Chaussures de Randonnée Salomon', 'Imperméables et tout-terrain.', 145.00, 120.00, 'Sport', 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500', 12, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Casque de Vélo Giro', 'Sécurité et aérodynamisme.', 89.00, 70.00, 'Sport', 'https://images.unsplash.com/photo-1541625602330-2277a4c4b282?w=500', 25, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),

-- Toys & Books
(gen_random_uuid(), 'Lego Star Wars Millenium Falcon', 'L''icône de la saga.', 169.00, 140.00, 'Jouets', 'https://images.unsplash.com/photo-1585366119957-e9730b6d0f60?w=500', 10, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Barbie Dreamhouse', 'La maison de rêve pour les enfants.', 199.00, 170.00, 'Jouets', 'https://images.unsplash.com/photo-1558000143-a78f8299c40b?w=500', 5, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Peluche Ours Géant', 'Un compagnon tout doux.', 45.00, 30.00, 'Jouets', 'https://images.unsplash.com/photo-1559440666-3742132630ce?w=500', 20, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Puzzle 1000 pièces Paysage', 'Un défi pour toute la famille.', 20.00, 15.00, 'Jouets', 'https://images.unsplash.com/photo-1585366119957-e9730b6d0f60?w=500', 50, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Jeu de société Catan', 'Construisez et commercez.', 40.00, 35.00, 'Jouets', 'https://images.unsplash.com/photo-1610890716171-6b1bb98ffd09?w=500', 15, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Roman ''Le Seigneur des Anneaux''', 'L''intégrale de J.R.R. Tolkien.', 35.00, 25.00, 'Livres', 'https://images.unsplash.com/photo-1621351183012-e2f9972dd9bf?w=500', 25, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'BD ''Asterix le Gaulois''', 'Un classique de la bande dessinée.', 12.00, 10.00, 'Livres', 'https://images.unsplash.com/photo-1589998059171-988d887df646?w=500', 100, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Crayons de couleur Faber-Castell', 'Qualité professionnelle.', 25.00, 20.00, 'Loisirs', 'https://images.unsplash.com/photo-1513364776144-60967b0f800f?w=500', 40, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Télescope pour débutants', 'Découvrez les étoiles.', 120.00, 100.00, 'Loisirs', 'https://images.unsplash.com/photo-1454789548928-9efd52dc4031?w=500', 8, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002'),
(gen_random_uuid(), 'Microscope 1200x', 'Explorez le monde invisible.', 85.00, 70.00, 'Loisirs', 'https://images.unsplash.com/photo-1516062423079-7ca13cdc7f5a?w=500', 10, 'ACTIF', NOW(), 'a0000000-0000-0000-0000-000000000002');

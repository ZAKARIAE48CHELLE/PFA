import os
import uuid
import random
import pandas as pd
import psycopg2

CSV_PATH = "d:/EMSI/S8/PFA/PFA/DATA AND ML/data/processed/unified_dataset.csv"

# Category Mapping
category_mapping = {
    'Smartphones': 'Électronique',
    'Tablettes': 'Électronique',
    'Informatique': 'Électronique',
    'TV & Vidéo': 'Électronique',
    'Audio': 'Électronique',
    'Photo & Caméra': 'Électronique',
    'Gaming': 'Électronique',
    'Téléphones & Tablettes': 'Électronique',
    'TV & Home Cinéma': 'Électronique',
    'Électronique': 'Électronique',
    'Steam Specials': 'Électronique',
    'Steam Top Sellers': 'Électronique',
    'Steam All Games': 'Électronique',
    'Accessoires': 'Électronique',
    'Mode Homme': 'Mode',
    'Mode Femme': 'Mode',
    'Montres': 'Mode',
    'Électroménager': 'Maison',
    'Maison': 'Maison',
    'Maison & Cuisine': 'Maison',
    'Beauté': 'Beauté',
    'Beauté & Santé': 'Beauté',
    'Sport': 'Sport',
    'Jouets': 'Jouets',
    'Jeux & Jouets': 'Jouets',
    'Loisirs': 'Loisirs',
    'Livres': 'Livres',
    'Auto': 'Auto',
    'Alimentation': 'Alimentation'
}

# Image Lists per Mapped Category
category_images = {
    'Électronique': [
        'https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=500',
        'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=500',
        'https://images.unsplash.com/photo-1588449668338-d1517689ee14?w=500',
        'https://images.unsplash.com/photo-1593642632823-8f785ba67e45?w=500',
        'https://images.unsplash.com/photo-1496181130204-755241544e35?w=500',
        'https://images.unsplash.com/photo-1526738549149-8e07eca6c147?w=500',
        'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500',
    ],
    'Mode': [
        'https://images.unsplash.com/photo-1483985988355-763728e1935b?w=500',
        'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500',
        'https://images.unsplash.com/photo-1523170335258-f5ed11844a49?w=500',
        'https://images.unsplash.com/photo-1551028711-0305df2f9fb3?w=500',
        'https://images.unsplash.com/photo-1542272604-787c3835535d?w=500',
    ],
    'Maison': [
        'https://images.unsplash.com/photo-1513694203232-719a280e022f?w=500',
        'https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=500',
        'https://images.unsplash.com/photo-1533090161767-e6ffed986c88?w=500',
        'https://images.unsplash.com/photo-1517668808822-9ebb02f2a0e6?w=500',
    ],
    'Sport': [
        'https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=500',
        'https://images.unsplash.com/photo-1485965120184-e220f721d03e?w=500',
        'https://images.unsplash.com/photo-1509563268479-0f004cf3f58b?w=500',
        'https://images.unsplash.com/photo-1502680390469-be75c86b636f?w=500',
    ],
    'Beauté': [
        'https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=500',
        'https://images.unsplash.com/photo-1556228720-195a672e8a03?w=500',
        'https://images.unsplash.com/photo-1608248597279-f99d160bfcbc?w=500',
    ],
    'Jouets': [
        'https://images.unsplash.com/photo-1534447677768-be436bb09401?w=500',
        'https://images.unsplash.com/photo-1587654780291-39c9404d746b?w=500',
        'https://images.unsplash.com/photo-1558000143-a78f8299c40b?w=500',
    ],
    'Livres': [
        'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=500',
        'https://images.unsplash.com/photo-1497633762265-9d179a990aa6?w=500',
        'https://images.unsplash.com/photo-1506880018603-83d5b814b5a6?w=500',
    ],
    'Loisirs': [
        'https://images.unsplash.com/photo-1513364776144-60967b0f800f?w=500',
        'https://images.unsplash.com/photo-1454789548928-9efd52dc4031?w=500',
    ],
    'Alimentation': [
        'https://images.unsplash.com/photo-1542838132-92c53300491e?w=500',
        'https://images.unsplash.com/photo-1506084868230-bb9d95c24759?w=500',
    ],
    'Auto': [
        'https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=500',
        'https://images.unsplash.com/photo-1486006920555-c77dce18193b?w=500',
    ]
}

def ensure_databases_and_tables():
    print("Connecting to default postgres database...")
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="postgres",
        user="postgres",
        password="1708"
    )
    conn.autocommit = True
    cursor = conn.cursor()

    # Create missing databases
    cursor.execute("SELECT datname FROM pg_database;")
    existing_dbs = [row[0] for row in cursor.fetchall()]

    target_dbs = ["auramarket_auth", "auramarket_product", "auramarket_negotiation", "auramarket_audit"]
    for db in target_dbs:
        if db not in existing_dbs:
            print(f"Creating missing database: {db}...")
            cursor.execute(f"CREATE DATABASE {db};")

    cursor.close()
    conn.close()

    # --- 1. SETUP auramarket_auth ---
    print("Initializing auramarket_auth...")
    conn_auth = psycopg2.connect(host="localhost", port=5432, database="auramarket_auth", user="postgres", password="1708")
    conn_auth.autocommit = True
    cur_auth = conn_auth.cursor()
    cur_auth.execute("""
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id UUID PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            mdp_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL
        );
    """)
    # Seed default users
    cur_auth.execute("""
        INSERT INTO utilisateurs (id, email, mdp_hash, role) VALUES
            ('a0000000-0000-0000-0000-000000000001', 'admin@auramarket.com', '$2a$10$dummyhashforpassword123placeholder00', 'SUPERVISEUR'),
            ('a0000000-0000-0000-0000-000000000002', 'vendeur@auramarket.com', '$2a$10$dummyhashforpassword123placeholder00', 'VENDEUR'),
            ('a0000000-0000-0000-0000-000000000003', 'acheteur@auramarket.com', '$2a$10$dummyhashforpassword123placeholder00', 'ACHETEUR')
        ON CONFLICT (email) DO NOTHING;
    """)
    cur_auth.close()
    conn_auth.close()

    # --- 2. SETUP auramarket_product ---
    print("Initializing auramarket_product...")
    conn_prod = psycopg2.connect(host="localhost", port=5432, database="auramarket_product", user="postgres", password="1708")
    conn_prod.autocommit = True
    cur_prod = conn_prod.cursor()
    cur_prod.execute("""
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
            vendeur_id UUID,
            prix_offre DOUBLE PRECISION
        );
    """)
    cur_prod.execute("""
        CREATE TABLE IF NOT EXISTS commentaires (
            id UUID PRIMARY KEY,
            produit_id UUID,
            texte TEXT,
            note INT,
            date_publication TIMESTAMP,
            auteur_id UUID
        );
    """)
    cur_prod.execute("""
        CREATE TABLE IF NOT EXISTS offres (
            id UUID PRIMARY KEY,
            titre VARCHAR(255),
            description TEXT,
            prix_propose DOUBLE PRECISION,
            prix_final DOUBLE PRECISION,
            statut VARCHAR(50),
            date_creation TIMESTAMP,
            date_expiration TIMESTAMP,
            date_debut TIMESTAMP,
            date_fin TIMESTAMP,
            pourcentage_discount DOUBLE PRECISION DEFAULT 0.0,
            produit_id UUID,
            acheteur_id UUID,
            agent_genere BOOLEAN DEFAULT FALSE
        );
    """)
    cur_prod.close()
    conn_prod.close()

    # --- 3. SETUP auramarket_negotiation ---
    print("Initializing auramarket_negotiation...")
    conn_nego = psycopg2.connect(host="localhost", port=5432, database="auramarket_negotiation", user="postgres", password="1708")
    conn_nego.autocommit = True
    cur_nego = conn_nego.cursor()
    cur_nego.execute("""
        CREATE TABLE IF NOT EXISTS negociations (
            id UUID PRIMARY KEY,
            acheteur_id UUID,
            produit_id UUID,
            rounds INT,
            prix_final DOUBLE PRECISION
        );
    """)
    cur_nego.execute("""
        CREATE TABLE IF NOT EXISTS messages_negociation (
            id UUID PRIMARY KEY,
            negociation_id UUID,
            sender VARCHAR(50),
            content TEXT,
            price DOUBLE PRECISION,
            timestamp TIMESTAMP
        );
    """)
    cur_nego.close()
    conn_nego.close()

    print("All databases and tables have been fully created and seeded!")

def import_products():
    # Ensure databases and tables are set up
    ensure_databases_and_tables()

    print(f"Reading unified dataset from: {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} rows. Filtering and mapping categories...")

    # Fill empty fields & clean categories
    df['category'] = df['category'].fillna('Autre')
    df['mapped_category'] = df['category'].map(category_mapping).fillna('Électronique')

    # Exclude rows where price_initial_mad is null or <= 0
    df = df[df['price_initial_mad'].notna() & (df['price_initial_mad'] > 0)]
    print(f"{len(df)} rows remaining after filtering invalid prices.")

    # Remove exact duplicate titles to keep catalog fresh and clean
    df = df.drop_duplicates(subset=['title_clean'])
    print(f"{len(df)} rows remaining after deduplication.")

    # Sample up to 100 products per category
    sampled_dfs = []
    for cat in category_images.keys():
        cat_df = df[df['mapped_category'] == cat]
        if len(cat_df) > 100:
            cat_df = cat_df.sample(n=100, random_state=42)
        sampled_dfs.append(cat_df)

    final_df = pd.concat(sampled_dfs)
    print(f"Selected {len(final_df)} diverse high-quality products to insert.")

    # Connect to PostgreSQL
    print("Connecting to PostgreSQL database: auramarket_product...")
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="auramarket_product",
        user="postgres",
        password="1708"
    )
    cursor = conn.cursor()

    print("Seeding into produits table...")
    inserted_count = 0

    vendeur_id = "a0000000-0000-0000-0000-000000000002" # Standard Seller ID

    for _, row in final_df.iterrows():
        p_id = str(uuid.uuid4())
        titre = row['title_clean']
        if len(titre) > 255:
            titre = titre[:252] + "..."
            
        description = f"Produit importé de {row['source']}. {row['title_clean']}"
        prix = float(row['price_initial_mad'])
        
        # Calculate a realistic minimum price for negotiation
        prix_min = round(prix * random.choice([0.7, 0.75, 0.8]), 2)
        
        # Get offer price if exists, else None
        prix_offre = None
        if pd.notna(row['price_offre_mad']) and float(row['price_offre_mad']) > 0:
            prix_offre = round(float(row['price_offre_mad']), 2)
            if prix_offre >= prix:
                prix_offre = round(prix * 0.85, 2)
        
        categorie = row['mapped_category']
        
        # Select an aesthetic image matching this category
        images = category_images.get(categorie, category_images['Électronique'])
        image_url = random.choice(images)
        
        stock = random.randint(5, 30)
        statut = "ACTIF"
        date_pub = pd.to_datetime(row['date']) if pd.notna(row['date']) else pd.Timestamp.now()

        try:
            cursor.execute("""
                INSERT INTO produits (id, titre, description, prix, prix_min, categorie, image_url, stock, statut, date_publication, vendeur_id, prix_offre)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING;
            """, (p_id, titre, description, prix, prix_min, categorie, image_url, stock, statut, date_pub, vendeur_id, prix_offre))
            inserted_count += 1
        except Exception as e:
            print(f"Failed to insert {titre[:30]}: {e}")
            conn.rollback()

    conn.commit()
    cursor.close()
    conn.close()
    print(f"Successfully imported {inserted_count} new products into the database!")

if __name__ == "__main__":
    import_products()

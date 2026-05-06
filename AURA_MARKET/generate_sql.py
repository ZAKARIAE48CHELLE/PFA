import os
import uuid
import random
import pandas as pd

CSV_PATH = "d:/EMSI/S8/PFA/PFA/DATA AND ML/data/processed/unified_dataset.csv"
SQL_OUTPUT_PATH = "import_dataset.sql"

# Upgraded Category Mapping representing the real-world products in the CSV perfectly
category_mapping = {
    'Smartphones': 'Smartphones',
    'Tablettes': 'Smartphones',
    'Téléphones & Tablettes': 'Smartphones',
    'Tlphones & Tablettes': 'Smartphones',
    'TV & Home Cinéma': 'Smartphones',
    'TV & Home Cinma': 'Smartphones',
    
    'Informatique': 'Informatique',
    'Audio': 'Informatique',
    'Photo & Caméra': 'Informatique',
    'Photo & Camra': 'Informatique',
    'Accessoires': 'Informatique',
    'Électronique': 'Informatique',
    'lectronique': 'Informatique',
    
    'Gaming': 'Gaming',
    'Steam Specials': 'Gaming',
    'Steam Top Sellers': 'Gaming',
    'Steam All Games': 'Gaming',
    'Jouets': 'Gaming',
    'Jeux & Jouets': 'Gaming',
    
    'Électroménager': 'Électroménager',
    'lectromnager': 'Électroménager',
    'TV & Vidéo': 'Électroménager',
    'TV & Vido': 'Électroménager',
    
    'Mode Homme': 'Mode',
    'Mode Femme': 'Mode',
    'Montres': 'Mode',
    
    'Maison': 'Maison',
    'Maison & Cuisine': 'Maison',
    
    'Beauté': 'Beauté',
    'Beaut': 'Beauté',
    'Beauté & Santé': 'Beauté',
    'Beaut & Sant': 'Beauté',
    
    'Sport': 'Sport'
}

# Image Lists per exact Mapped Category
category_images = {
    'Smartphones': [
        'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=500',
        'https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=500',
        'https://images.unsplash.com/photo-1565630916779-e303be97b6f5?w=500',
        'https://images.unsplash.com/photo-1574757565409-e17b19fe57cb?w=500',
    ],
    'Informatique': [
        'https://images.unsplash.com/photo-1496181130204-755241544e35?w=500',
        'https://images.unsplash.com/photo-1526738549149-8e07eca6c147?w=500',
        'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500',
        'https://images.unsplash.com/photo-1588449668338-d1517689ee14?w=500',
        'https://images.unsplash.com/photo-1547082299-de196ea013d6?w=500',
    ],
    'Gaming': [
        'https://images.unsplash.com/photo-1534447677768-be436bb09401?w=500',
        'https://images.unsplash.com/photo-1587654780291-39c9404d746b?w=500',
        'https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=500',
        'https://images.unsplash.com/photo-1558000143-a78f8299c40b?w=500',
    ],
    'Électroménager': [
        'https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=500',
        'https://images.unsplash.com/photo-1574269909862-7e1d70bb8078?w=500',
        'https://images.unsplash.com/photo-1583847268964-b28dc8f51f92?w=500',
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
    'Beauté': [
        'https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=500',
        'https://images.unsplash.com/photo-1556228720-195a672e8a03?w=500',
        'https://images.unsplash.com/photo-1608248597279-f99d160bfcbc?w=500',
    ],
    'Sport': [
        'https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=500',
        'https://images.unsplash.com/photo-1485965120184-e220f721d03e?w=500',
        'https://images.unsplash.com/photo-1509563268479-0f004cf3f58b?w=500',
        'https://images.unsplash.com/photo-1502680390469-be75c86b636f?w=500',
    ]
}

def clean_sql_str(val):
    if val is None:
        return "NULL"
    return str(val).replace("'", "''")

def generate_sql_file():
    print(f"Reading unified dataset from: {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} rows. Filtering and mapping categories...")

    df['category'] = df['category'].fillna('Autre')
    df['mapped_category'] = df['category'].map(category_mapping).fillna('Informatique')

    df = df[df['price_initial_mad'].notna() & (df['price_initial_mad'] > 0)]
    df = df.drop_duplicates(subset=['title_clean'])

    # Keep all products that belong to our 8 valid category groups
    final_df = df[df['mapped_category'].isin(category_images.keys())]
    print(f"Selected all {len(final_df)} unique valid products from the dataset. Generating SQL statements...")

    vendeur_id = "a0000000-0000-0000-0000-000000000002"

    with open(SQL_OUTPUT_PATH, "w", encoding="utf-8") as f:
        # Truncate both tables CASCADE to start completely fresh and avoid foreign key conflicts
        f.write("-- Clean existing products and offers to make way for the new dataset\n")
        f.write("TRUNCATE TABLE produits, offres CASCADE;\n\n")

        for _, row in final_df.iterrows():
            p_id = str(uuid.uuid4())
            titre_raw = row['title_clean']
            titre = clean_sql_str(titre_raw)
            if len(titre) > 255:
                titre = titre[:252] + "..."
                
            description = clean_sql_str(f"Produit importé de {row['source']}. {row['title_clean']}")
            prix = float(row['price_initial_mad'])
            prix_min = round(prix * random.choice([0.7, 0.75, 0.8]), 2)
            
            prix_offre_val = None
            prix_offre_str = "NULL"
            if pd.notna(row['price_offre_mad']) and float(row['price_offre_mad']) > 0:
                prix_offre_val = round(float(row['price_offre_mad']), 2)
                if prix_offre_val >= prix:
                    prix_offre_val = round(prix * 0.85, 2)
                prix_offre_str = str(prix_offre_val)
            
            categorie = clean_sql_str(row['mapped_category'])
            images = category_images.get(row['mapped_category'], category_images['Informatique'])
            image_url = clean_sql_str(random.choice(images))
            stock = random.randint(5, 30)
            statut = "ACTIF"
            
            date_pub = "NOW()"
            if pd.notna(row['date']):
                date_pub = f"'{row['date']}'"

            # 1. Insert Product
            sql_prod = f"INSERT INTO produits (id, titre, description, prix, prix_min, categorie, image_url, stock, statut, date_publication, vendeur_id, prix_offre) " \
                       f"VALUES ('{p_id}', '{titre}', '{description}', {prix}, {prix_min}, '{categorie}', '{image_url}', {stock}, '{statut}', {date_pub}, '{vendeur_id}', {prix_offre_str});\n"
            f.write(sql_prod)

            # 2. Insert corresponding Offer if product is discounted (prix_offre is non-null)
            if prix_offre_val is not None:
                o_id = str(uuid.uuid4())
                offre_titre = clean_sql_str(f"PROMO - {titre_raw}")
                if len(offre_titre) > 255:
                    offre_titre = offre_titre[:252] + "..."
                    
                offre_desc = clean_sql_str(f"Super promotion de {row['source']}")
                discount_pct = round((1 - prix_offre_val / prix) * 100, 2)
                
                sql_offre = f"INSERT INTO offres (id, titre, description, prix_propose, prix_final, statut, date_creation, date_expiration, date_debut, date_fin, pourcentage_discount, produit_id, acheteur_id, agent_genere) " \
                            f"VALUES ('{o_id}', '{offre_titre}', '{offre_desc}', {prix}, {prix_offre_val}, 'VALIDEE', NOW(), NOW() + INTERVAL '30 days', NOW() - INTERVAL '1 day', NOW() + INTERVAL '30 days', {discount_pct}, '{p_id}', NULL, FALSE);\n"
                f.write(sql_offre)

    print("Successfully generated upgraded SQL import file with accurate categories and offers!")

if __name__ == "__main__":
    generate_sql_file()

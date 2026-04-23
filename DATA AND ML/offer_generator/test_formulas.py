import pandas as pd
import math

def calculate_discount(source, price_val, rating_val, category_val=""):
    p = price_val if pd.notna(price_val) and price_val > 0 else 1
    r = rating_val if pd.notna(rating_val) and rating_val > 0 else 3.5
    
    source_lower = source.lower() if pd.notna(source) else ""
    cat_lower = str(category_val).lower() if pd.notna(category_val) else ""

    # --- Category Factor (Cf) ---
    # High Value / Low Margin: 0.8
    # High Margin / Accessories: 1.3
    # Standard: 1.0
    cf = 1.0
    high_value_keywords = ['smartphone', 'téléphone', 'phone', 'tablette', 'tablet', 'laptop', 'ordinateur', 'tv', 'vidéo', 'photo', 'électroménager']
    accessory_keywords = ['accessoire', 'audio', 'écouteur', 'casque', 'câble', 'cable', 'coque', 'étui', 'mouse', 'souris', 'clavier', 'keyboard', 'gaming']
    
    if any(kw in cat_lower for kw in high_value_keywords):
        cf = 0.8
    elif any(kw in cat_lower for kw in accessory_keywords):
        cf = 1.3

    if "cdiscount" in source_lower:
        d = (15.0 + 5.0 * math.log10(p + 1) + 4.0 * (5 - r)) * cf
        return max(10, min(60, d))
        
    elif "steam" in source_lower:
        # Steam already has digital-specific logic, we keep cf=1.0 for it
        d = 20.0 + (1000.0 / (p + 10)) + 5.0 * (5 - r)
        return max(10, min(85, d))
        
    elif "amazon" in source_lower:
        d = (8.0 + 3.0 * math.log10(p + 1) + 2.0 * (4.5 - r)) * cf
        return max(5, min(40, d))
        
    elif "jumia" in source_lower:
        d = (12.0 + 4.0 * math.log10(p + 1) + 3.0 * (4 - r)) * cf
        return max(10, min(50, d))
        
    elif "avito" in source_lower:
        d = (5.0 + 0.5 * math.log10(p + 1) + 1.5 * (4 - r)) * cf
        return max(0, min(20, d))
        
    else:
        d = (10.0 + 3.0 * math.log10(p + 1) + 2.0 * (5 - r)) * cf
        return max(5, min(50, d))


df = pd.read_csv(r'd:\EMSI\S8\PFA\PFA\data\processed\unified_dataset.csv')

# Use price_initial if available, otherwise price_offre
df['active_price'] = df['price_initial'].fillna(df['price_offre'])
df['active_price'] = pd.to_numeric(df['active_price'], errors='coerce')

# Safely extract numerical rating from possible strings
df['numeric_rating'] = pd.to_numeric(df['rating'], errors='coerce')

df = df.dropna(subset=['active_price'])

# Sample items from different sources and categories
sample_df = df.groupby('source').apply(lambda x: x.sample(min(len(x), 3))).reset_index(drop=True)

results = []

for _, row in sample_df.iterrows():
    src = str(row['source']).strip()
    title = str(row['title_clean'])[:50] + "..." if len(str(row['title_clean'])) > 50 else str(row['title_clean'])
    cat = str(row['category']).strip()
    p = row['active_price']
    r = row['numeric_rating']
    
    disc_pct = calculate_discount(src, p, r, cat)
    new_price = p * (1 - (disc_pct/100))
    
    results.append({
        "Source": src,
        "Category": cat,
        "Product": title,
        "Price": round(p, 2),
        "Rating": round(r, 2) if pd.notna(r) else "None (Asm 3.5)",
        "Generated_Offer_%": f"{round(disc_pct)}%",
        "Offer_Price": round(new_price, 2)
    })

res_df = pd.DataFrame(results)

print("\n--- DISCOUNT FORMULA MULTI-SOURCE TEST RESULTS ---\n")
print(res_df.to_string(index=False))

res_df.to_csv("d:/EMSI/S8/PFA/PFA/offer_generator/formula_test_results.csv", index=False)
print("\nResults saved to d:/EMSI/S8/PFA/PFA/offer_generator/formula_test_results.csv")

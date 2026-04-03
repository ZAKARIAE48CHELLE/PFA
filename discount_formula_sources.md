# Multi-Source Mathematical Offer Formulas

Each marketplace and platform operates on a different business model, which means a "one-size-fits-all" discount formula isn't ideal. E-commerce platforms like Cdiscount rely on aggressive flash sales, Steam relies on deep digital discounts for older games, and platforms like Avito are user-to-user (C2C) with narrower negotiation margins.

Below is a tailored mathematical formula for each of the main data sources in your raw folder: **Amazon**, **CDiscount**, **Steam**, **Jumia**, and **Avito**.

---

### Variables Legend
*   $P$: The product's numeric price.
*   $R$: The product rating (Scaled from 1 to 5). *If empty, use an average like 3.0 to 4.0 depending on the platform.*
*   $D$: The final Discount Percentage.

---

### 1. Cdiscount (The "Aggressive Discounter" Formula)
Cdiscount is known for very high base discounts and psychological flash pricing. Digital stock and aggressive retail sales demand a steeper formula.

$$ D_{cdiscount}(\%) = \min(60, \max(10, 15 + 5 \log_{10}(P + 1) + 4 (5 - R))) $$
**Logic Base:**
*   **Base:** 15% (Very aggressive starting point).
*   **Price Factor:** High weight ($5\log_{10}$), generating steeper discounts for more expensive products.
*   **Rating Factor:** High weight ($4 \times$), punishing poorly-rated items heavily to try to clear inventory out quickly.

> [!NOTE]
> **Example Application:** A **100€** item with a rating of **3.0**.
> *   $F_p$: $5 \times \log_{10}(101) \approx 5 \times 2.0 = 10\%$
> *   $F_r$: $4 \times (5 - 3) = 8\%$
> *   **Total Discount**: $15 + 10 + 8 = \textbf{33\%}$

---

### 2. Steam (The "Digital Goods" Formula)
Steam sells digital software where the marginal cost to produce another copy is $0. Thus, cheaper/older titles routinely see 75%–90% discounts, whereas AAA high-priced ones rarely drop below 20-30% early on.

$$ D_{steam}(\%) = \min(85, \max(10, 20 + \frac{1000}{P + 10} + 5(5 - R))) $$
**Logic Base:**
*   **Base:** 20% (Standard major sale starting point).
*   **Inverse Price Factor:** Notice the division $\frac{1000}{P + 10}$. Cheaper games (e.g., $10€$) get a huge boost ($+50\%$) because they are likely older titles. Expensive AAA games (e.g., $60€$) get a smaller boost ($+14\%$).
*   **Rating:** If a game is "Mixed" or "Negative" (low rating), it receives an extra push.

> [!NOTE]
> **Example Application 1:** An older/indie game priced at **15€** with a rating of **4.0**.
> *   $F_p$: $\frac{1000}{15 + 10} = \frac{1000}{25} = 40\%$
> *   $F_r$: $5 \times (5 - 4) = 5\%$
> *   **Total Discount**: $20 + 40 + 5 = \textbf{65\%}$
>
> **Example Application 2:** A new AAA game priced at **70€** with a rating of **4.5**.
> *   $F_p$: $\frac{1000}{70 + 10} = \frac{1000}{80} = 12.5\%$
> *   $F_r$: $5 \times (5 - 4.5) = 2.5\%$
> *   **Total Discount**: $20 + 12.5 + 2.5 = \textbf{35\%}$

---

### 3. Amazon (The "Algorithmic Retail" Formula)
Amazon is heavily optimized and competitive, rarely offering 60% discounts unless it's a blowout. The discounts are calculated and moderate.

$$ D_{amazon}(\%) = \min(40, \max(5, 8 + 3 \log_{10}(P + 1) + 2 (4.5 - R))) $$
**Logic Base:**
*   **Base:** 8%
*   **Rating Focus:** Amazon items hold their value well. We only start punishing if the score drops below 4.5. Items with a 4.5+ score barely get extra discount logic because they already sell themselves. Maximum cap is generally tight around 40%.

> [!NOTE]
> **Example Application:** A high-end speaker at **250€** with an excellent rating of **4.8**.
> *   $F_p$: $3 \times \log_{10}(251) \approx 3 \times 2.4 = 7.2\%$
> *   $F_r$: $2 \times (4.5 - 4.8) = -0.6\%$ (Small penalty drop because it sells well)
> *   **Total Discount**: $8 + 7.2 - 0.6 = 14.6\% \approx \textbf{15\%}$

---

### 4. Jumia (The "E-commerce Flash" Formula)
Jumia behaves similarly to a standard marketplace with seasonal pushes (like Black Friday). A balanced, versatile formula works best.

$$ D_{jumia}(\%) = \min(50, \max(10, 12 + 4 \log_{10}(P + 1) + 3 (4 - R))) $$
**Logic Base:**
*   **Base:** 12%
*   **Rating Focus:** Middle ground. Lower-rated items clear out faster, and prices scale reliably. Maximum is capped at 50%.

> [!NOTE]
> **Example Application:** An unbranded accessory at **30€** with a poor/mediocre rating of **2.5**.
> *   $F_p$: $4 \times \log_{10}(31) \approx 4 \times 1.5 = 6\%$
> *   $F_r$: $3 \times (4 - 2.5) = 4.5\%$
> *   **Total Discount**: $12 + 6 + 4.5 = 22.5\% \approx \textbf{23\%}$

---

### 5. Avito (The "C2C Negotiation" Margin)
Avito is mostly User-to-User (Classifieds). "Offers" here don't act as corporate discounts, but rather represent the *estimated negotiable margin* a buyer might realistically get off the listed price.

$$ D_{avito}(\%) = \min(20, \max(0, 5 + 0.5 \log_{10}(P + 1) + 1.5 (4 - R))) $$
**Logic Base:**
*   **Base:** 5% (Just a standard negotiation haggle).
*   **Price Factor:** Extremely flat limit ($0.5$).
*   **Behavior:** A seller might drop their price by 5-15% total if it's a poorly rated or older item, but you rarely "discount" second-hand goods by 50% unless they are completely broken. Limit is securely bounded at 20%.

> [!NOTE]
> **Example Application:** A second-hand phone listed for **500€** with an estimated condition rating of **3.5**.
> *   $F_p$: $0.5 \times \log_{10}(501) \approx 0.5 \times 2.7 = 1.35\%$
> *   $F_r$: $1.5 \times (4 - 3.5) = 0.75\%$
> *   **Total Discount**: $5 + 1.35 + 0.75 = 7.1\% \approx \textbf{7\%}$ *(Meaning a buyer could likely negotiate the 500€ price down by ~35€)*

---

### Python Implementation Generator
You can route your datasets through a Python script that applies the correct formula depending on the string name of the source:

```python
import math

def calculate_discount(source, price_val, rating_val):
    p = price_val if price_val > 0 else 1
    r = rating_val if rating_val > 0 else 3.5 # Default rating assumptions

    if source.lower() == "cdiscount":
        d = 15.0 + 5.0 * math.log10(p + 1) + 4.0 * (5 - r)
        return max(10, min(60, d))
        
    elif source.lower() == "steam":
        d = 20.0 + (1000.0 / (p + 10)) + 5.0 * (5 - r)
        return max(10, min(85, d))
        
    elif source.lower() == "amazon":
        d = 8.0 + 3.0 * math.log10(p + 1) + 2.0 * (4.5 - r)
        return max(5, min(40, d))
        
    elif source.lower() == "jumia":
        d = 12.0 + 4.0 * math.log10(p + 1) + 3.0 * (4 - r)
        return max(10, min(50, d))
        
    elif source.lower() == "avito":
        d = 5.0 + 0.5 * math.log10(p + 1) + 1.5 * (4 - r)
        return max(0, min(20, d))
        
    else:
        # Default Fallback
        d = 10.0 + 3.0 * math.log10(p + 1) + 2.0 * (5 - r)
        return max(5, min(50, d))

# Example Usage:
# print(calculate_discount("steam", 10.0, 4.0)) # Result ~62%
# print(calculate_discount("amazon", 500.0, 4.8)) # Result ~16%
```

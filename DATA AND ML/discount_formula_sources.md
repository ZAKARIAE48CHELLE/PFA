# Multi-Source & Category-Driven Mathematical Offer Formulas

Each marketplace and platform operates on a different business model, which means a "one-size-fits-all" discount formula isn't ideal. In this version, we incorporate a **Category Factor ($C_f$)** to distinguish between high-value electronics (low margin) and accessories (high margin).

---

### Variables Legend
*   $P$: The product's numeric price.
*   $R$: The product rating (Scaled from 1 to 5).
*   **$C_f$ (Category Factor)**:
    *   **0.8**: High Value / Low Margin (Smartphones, Laptops, TV, Electroménager).
    *   **1.3**: High Margin / Accessories (Audio, Cables, Cases, Mouse, Keyboard).
    *   **1.0**: Standard Retail (Home, Kitchen, Beauty, Health).
*   $D$: The final Discount Percentage.

---

### Algorithmic Rationale: Why "Fixed" Values?

You might notice several fixed numbers (constants) in these formulas (e.g., 15.0, 5.0, 4.0). These are **Heuristic Constants** used to calibrate the algorithm. Below is why they are "fixed" rather than calculated:

1.  **The Base Discount (The "Marketing Floor")**:
    *   *Examples: 15.0 for Cdiscount, 8.0 for Amazon.*
    *   **Why**: This represents the platform's "Identity." Amazon focuses on price stability, so their floor is lower. Cdiscount focuses on "Good Deals," so their floor is higher to ensure every generated offer looks like a "sale."

2.  **The Logarithmic Coefficient (The "Price Sensitivity")**:
    *   *Examples: $5 \log_{10}(P)$ or $3 \log_{10}(P)$.*
    *   **Why**: We use $\log_{10}$ because humans perceive value logarithmically (saving 10€ on 100€ feels the same as saving 100€ on 1000€). The fixed multiplier (e.g., 5.0) controls the **Slope**. We fixed these values to ensure that the "sweet spot" for max discounts happens around the median price of your specific dataset (~300€ - 500€).

3.  **The Rating Penalty (The "Inventory Clearance Speed")**:
    *   *Examples: $4 (5 - R)$ or $2 (4.5 - R)$.*
    *   **Why**: This fixed weight determines how much we "punish" bad products. A higher weight (4.0) means the AI is more desperate to get rid of low-rated stock. We fixed these based on the platform's trust level (Amazon customers care more about 0.1 differences in stars than Jumia customers).

4.  **The $D_{max}$ Cap (The "Profitability Shield")**:
    *   *Example: $\min(60, \dots)$.*
    *   **Why**: This is a hard business rule. Discounting physical goods above 60% usually results in a net loss for the retailer. Keeping this fixed prevents the algorithm from accidentally "bankrupting" the simulated store.

---

### 1. Cdiscount (The "Aggressive Discounter" Formula)
$$ D_{cdiscount}(\%) = \min(60, \max(10, (15 + 5 \log_{10}(P + 1) + 4 (5 - R)) \times C_f)) $$

> [!NOTE]
> **Example 1 (Smartphone):** 500€, Rating 4.0, $C_f = 0.8$.
> *   Base: $15 + 13.5 + 4 = 32.5\%$
> *   Adj: $32.5 \times 0.8 = \textbf{26\%}$

---

### 2. Steam (The "Digital Goods" Formula)
$$ D_{steam}(\%) = \min(85, \max(10, 20 + \frac{1000}{P + 10} + 5(5 - R))) $$

> [!NOTE]
> **Example 1 (AAA Games):** 60€, Rating 4.5.
> *   $20 + 12.5 + 2.5 = \textbf{35\%}$

---

### 3. Amazon (The "Algorithmic Retail" Formula)
$$ D_{amazon}(\%) = \min(40, \max(5, (8 + 3 \log_{10}(P + 1) + 2 (4.5 - R)) \times C_f)) $$

---

### 4. Jumia (The "E-commerce Flash" Formula)
$$ D_{jumia}(\%) = \min(50, \max(10, (12 + 4 \log_{10}(P + 1) + 3 (4 - R)) \times C_f)) $$

---

### 5. Avito (The "C2C Negotiation" Margin)
$$ D_{avito}(\%) = \min(20, \max(0, (5 + 0.5 \log_{10}(P + 1) + 1.5 (4 - R)) \times C_f)) $$

---

### Python Implementation

```python
import math

def calculate_discount(source, price_val, rating_val, category_val=""):
    p = price_val if price_val > 0 else 1
    r = rating_val if rating_val > 0 else 3.5
    cat = category_val.lower()

    # Apply Category Factor
    cf = 1.0
    if any(k in cat for k in ['phone', 'tablet', 'laptop', 'tv', 'électroménager']):
        cf = 0.8
    elif any(k in cat for k in ['accessoire', 'audio', 'câble', 'coque', 'souris']):
        cf = 1.3

    if "cdiscount" in source.lower():
        d = (15.0 + 5.0 * math.log10(p + 1) + 4.0 * (5 - r)) * cf
        return max(10, min(60, d))
    
    # ... and so on for other sources
```

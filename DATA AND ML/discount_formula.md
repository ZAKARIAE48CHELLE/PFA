# Dynamic Promotional Offer Formula

After analyzing your dataset (`cDiscount_data.json`), we have data containing the following key attributes which can influence an offer:
- **`price_offre`**: The current selling price.
- **`rating`**: Custumer rating (from 1 to 5).

To generate a dynamic discount (`offre`), we can use psychological pricing and inventory-demand estimates. A logical approach is that:
1. **Higher-priced items** can afford a slightly higher percentage discount to create perceived high value.
2. **Lower-rated items** or items without ratings might need a higher discount to incentivize the purchase compared to highly-rated products (which sell well naturally).

## Mathematical Formula

We can establish the following function $D(P, R)$ to calculate the discount percentage:

$$ D(\%) = \min \left( D_{max}, \max \left( D_{min}, D_{base} + F_p(P) + F_r(R) \right) \right) $$

### 1. Variables Definition
*   $P$: Product price (parsed as a numeric value from `price_offre`).
*   $R$: Product rating ($1$ to $5$). If a product has an empty rating, we assign it a default penalty baseline (e.g., $R = 2.5$).

### 2. Components
*   **$D_{base}$ (Base Discount)**: A starting flat discount rate, e.g., $10\%$.
*   **$F_p(P)$ (Price Factor)**: A logarithmic function. It increases the discount for expensive items but slows down to avoid excessive margin erosion.
    $$ F_p(P) = 5 \times \log_{10}(P + 1) $$
*   **$F_r(R)$ (Rating Factor)**: An inverse function to the rating. Highly rated items get less of an extra discount, while poorly rated (or unrated) items get more.
    $$ F_r(R) = \gamma \times (5 - R) $$
    *(Let $\gamma = 3$, meaning each dropped star adds $3\%$ more discount).*
*   **$D_{max}$ & $D_{min}$**: Boundary limiters to protect profitability. E.g., $D_{max} = 50\%$, $D_{min} = 5\%$.

---

## Examples of Application

**Scenario 1: High-end well-rated phone**
*   *Price:* $800€$
*   *Rating:* $4.8$
*   **Calculation**:
    *   $D_{base} = 10$
    *   $F_p(800) = 5 \times \log_{10}(801) \approx 5 \times 2.9 = 14.5$
    *   $F_r(4.8) = 3 \times (5 - 4.8) = 0.6$
    *   **Total Discount**: $10 + 14.5 + 0.6 = \textbf{25.1\%}$

**Scenario 2: Mid-range unrated/low-rated item**
*   *Price:* $50€$
*   *Rating:* $2.5$ (or missing)
*   **Calculation**:
    *   $D_{base} = 10$
    *   $F_p(50) = 5 \times \log_{10}(51) \approx 5 \times 1.7 = 8.5$
    *   $F_r(2.5) = 3 \times (5 - 2.5) = 7.5$
    *   **Total Discount**: $10 + 8.5 + 7.5 = \textbf{26\%}$

**Scenario 3: Cheap highly-rated accessory**
*   *Price:* $15€$
*   *Rating:* $5.0$
*   **Calculation**:
    *   $D_{base} = 10$
    *   $F_p(15) = 5 \times \log_{10}(16) \approx 5 \times 1.2 = 6.0$
    *   $F_r(5.0) = 3 \times (5 - 5) = 0$
    *   **Total Discount**: $10 + 6.0 + 0 = \textbf{16.0\%}$ (Rounded to 16%)

## Implementation in Python
If you wish to apply this to your JSON dataset, here is how the formula looks in code using `math.log10`:

```python
import math

def generate_offer(price_str, rating_str):
    try:
        # 1. Parse Price
        price = float(price_str.replace('€', '').replace(',', '.').strip())
        
        # 2. Parse Rating (default to 2.5 if missing)
        rating = float(rating_str) if rating_str.strip() else 2.5
        
        # 3. Apply Formula
        d_base = 10.0
        f_p = 5.0 * math.log10(price + 1)
        f_r = 3.0 * (5.0 - rating)
        
        raw_discount = d_base + f_p + f_r
        
        # 4. Limit between 5% and 50%
        final_discount = max(5.0, min(50.0, raw_discount))
        
        return {
            "type_offre": "pourcentage",
            "valeur_offre": f"{round(final_discount)}%"
        }
    except ValueError:
        return None  # Return None if data is unparseable
```

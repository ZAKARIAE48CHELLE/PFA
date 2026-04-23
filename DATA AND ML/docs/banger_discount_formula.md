# One Banger Discount Formula

Inspired by `formules_remises_multi_sources_FR.docx`, here is one unified mathematical formula that can drive offers for all marketplaces with source-specific calibration.

## Master Formula

\[
D(s,p,r,c)=\operatorname{clip}\!\left(
L_s,\,
U_s,\,
\left[
B_s
+\alpha_s\log_{10}(p+1)
+\beta_s(\tau_s-r)_+
+\frac{\delta_s}{p+\kappa_s}
\right]\cdot C_f(c)
\right)
\]

where:

- \(s\) = source / website
- \(p\) = product price
- \(r\) = rating on a 1 to 5 scale
- \(c\) = category
- \((x)_+ = \max(x,0)\)
- \(\operatorname{clip}(a,b,x)=\min(b,\max(a,x))\)

## Category Factor

\[
C_f(c)=
\begin{cases}
0.8 & \text{high-value, low-margin products} \\
1.3 & \text{high-margin accessories} \\
1.0 & \text{standard products}
\end{cases}
\]

Suggested mapping:

- \(0.8\): smartphones, laptops, TVs, major appliances
- \(1.3\): cables, audio accessories, cases, mice, keyboards
- \(1.0\): home, beauty, kitchen, general retail

## Source Constants

| Source \(s\) | \(B_s\) | \(\alpha_s\) | \(\beta_s\) | \(\tau_s\) | \(\delta_s\) | \(\kappa_s\) | \(L_s\) | \(U_s\) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Amazon | 8 | 3 | 2 | 4.5 | 0 | 10 | 5 | 40 |
| Jumia | 12 | 4 | 3 | 4.0 | 0 | 10 | 10 | 50 |
| CDiscount | 15 | 5 | 4 | 5.0 | 0 | 10 | 10 | 60 |
| Steam | 20 | 0 | 5 | 5.0 | 1000 | 10 | 10 | 85 |
| Avito | 5 | 0.5 | 1.5 | 4.0 | 0 | 10 | 0 | 20 |

## Why This Hits Hard

\[
\underbrace{B_s}_{\text{brand floor}}
+
\underbrace{\alpha_s\log_{10}(p+1)}_{\text{price sensitivity}}
+
\underbrace{\beta_s(\tau_s-r)_+}_{\text{rating penalty}}
+
\underbrace{\frac{\delta_s}{p+\kappa_s}}_{\text{cheap-item booster}}
\]

- \(B_s\) gives each platform its commercial identity.
- \(\log_{10}(p+1)\) increases discounts for expensive products without exploding.
- \((\tau_s-r)_+\) penalizes weak ratings but does nothing when rating is already strong.
- \(\frac{\delta_s}{p+\kappa_s}\) is the Steam-style weapon: small cheap digital products can get deep discounts.
- \(C_f(c)\) injects margin awareness.
- `clip` keeps the result realistic and profitable.

## Expanded Per-Source Formulas

### Amazon

\[
D_{amazon}(p,r,c)=\operatorname{clip}\left(5,40,\left[8+3\log_{10}(p+1)+2(4.5-r)_+\right]C_f(c)\right)
\]

### Jumia

\[
D_{jumia}(p,r,c)=\operatorname{clip}\left(10,50,\left[12+4\log_{10}(p+1)+3(4-r)_+\right]C_f(c)\right)
\]

### CDiscount

\[
D_{cdiscount}(p,r,c)=\operatorname{clip}\left(10,60,\left[15+5\log_{10}(p+1)+4(5-r)_+\right]C_f(c)\right)
\]

### Steam

\[
D_{steam}(p,r)=\operatorname{clip}\left(10,85,20+5(5-r)_++\frac{1000}{p+10}\right)
\]

### Avito

\[
D_{avito}(p,r,c)=\operatorname{clip}\left(0,20,\left[5+0.5\log_{10}(p+1)+1.5(4-r)_+\right]C_f(c)\right)
\]

## If You Want One Single Default Formula

If you want just one universal formula for the whole project, use this:

\[
D(p,r,c)=\operatorname{clip}\left(
8,\,
60,\,
\left[
10
+4\log_{10}(p+1)
+3(4.5-r)_+
+\frac{250}{p+10}
\right]C_f(c)
\right)
\]

This version is aggressive enough to feel like a real promotion engine, but still controlled enough to avoid absurd discounts.

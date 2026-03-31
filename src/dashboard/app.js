// ==========================
//   Dashboard Logic
// ==========================

// Chart global defaults for dark theme
Chart.defaults.color = '#94a3b8';
Chart.defaults.font.family = "'Inter', sans-serif";

// State
let dataset = [];

// Initialize Dashboard
async function initDashboard() {
  try {
    const response = await fetch('../../data/processed/unified_dataset.json');
    if (!response.ok) throw new Error("Network response was not ok");
    
    dataset = await response.json();
    
    calculateKPIs();
    renderCharts();
    renderTopDealsTable();
    renderCategoryTree();
    renderOffresSection('all');
    initOffresTabs();
    
  } catch (error) {
    console.error("Error loading JSON data:", error);
    document.getElementById('total-products').innerText = "Error";
    document.getElementById('total-products').style.color = "#ef4444";
    document.getElementById('total-products').nextElementSibling.innerText = "Check Local Server / CORS";
  }
}

// Calculate Top Metrics
function calculateKPIs() {
  // 1. Total Products
  const total = dataset.length;
  
  // 2. Average Price
  let totalPrice = 0;
  let countPrice = 0;
  
  // 3. Average Discount
  let totalDiscount = 0;
  let countDiscount = 0;
  
  // 4. Average Rating
  let totalRating = 0;
  let countRating = 0;

  dataset.forEach(item => {
    // Price
    if (typeof item.price_initial_mad === 'number') {
      totalPrice += item.price_initial_mad;
      countPrice++;
    } else if (typeof item.price_offre_mad === 'number') {
      totalPrice += item.price_offre_mad;
      countPrice++;
    }
    
    // Discount
    if (typeof item.discount_pct === 'number' && item.discount_pct > 0) {
      totalDiscount += item.discount_pct;
      countDiscount++;
    }
    
    // Rating
    if (typeof item.rating === 'number' && item.rating > 0 && item.rating <= 5) {
      totalRating += item.rating;
      countRating++;
    }
  });

  const avgPrice = countPrice > 0 ? (totalPrice / countPrice).toFixed(2) : 0;
  const avgDiscount = countDiscount > 0 ? (totalDiscount / countDiscount).toFixed(1) : 0;
  const avgRating = countRating > 0 ? (totalRating / countRating).toFixed(1) : 0;

  // Render to DOM
  document.getElementById('total-products').innerText = total.toLocaleString();
  document.getElementById('avg-price').innerText = Number(avgPrice).toLocaleString();
  document.getElementById('avg-discount').innerText = avgDiscount + "%";
  document.getElementById('avg-rating').innerText = avgRating + " / 5";
}

// Prepare Data & Render Charts
function renderCharts() {
  // --- Data aggregation for Platform Distribution ---
  const sourceCount = {};
  dataset.forEach(item => {
    const src = item.source || "Unknown";
    sourceCount[src] = (sourceCount[src] || 0) + 1;
  });

  const sourceLabels = Object.keys(sourceCount);
  const sourceData = Object.values(sourceCount);

  // Colors mapping for platforms
  const bgColors = sourceLabels.map(label => {
    if (label.toLowerCase().includes('amazon')) return 'rgba(245, 158, 11, 0.8)';
    if (label.toLowerCase().includes('jumia')) return 'rgba(249, 115, 22, 0.8)';
    if (label.toLowerCase().includes('avito')) return 'rgba(236, 72, 153, 0.8)';
    if (label.toLowerCase().includes('cdiscount')) return 'rgba(59, 130, 246, 0.8)';
    return 'rgba(148, 163, 184, 0.8)';
  });

  // Render Source Doughnut Chart
  const ctxSource = document.getElementById('sourceChart').getContext('2d');
  new Chart(ctxSource, {
    type: 'doughnut',
    data: {
      labels: sourceLabels,
      datasets: [{
        data: sourceData,
        backgroundColor: bgColors,
        borderColor: 'rgba(255, 255, 255, 0.05)',
        borderWidth: 2,
        hoverOffset: 10
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'right' }
      },
      cutout: '70%'
    }
  });


  // --- Data aggregation for Pricing by Category ---
  const catPriceSum = {};
  const catPriceCount = {};
  
  dataset.forEach(item => {
    const cat = item.category || "Other";
    const price = item.price_offre_mad || item.price_initial_mad || 0;
    
    // Ignore extreme outliers or missing data for clean chart
    if (price > 0 && price < 100000) {
      catPriceSum[cat] = (catPriceSum[cat] || 0) + price;
      catPriceCount[cat] = (catPriceCount[cat] || 0) + 1;
    }
  });

  const catNames = Object.keys(catPriceSum);
  const avgPrices = catNames.map(cat => Math.round(catPriceSum[cat] / catPriceCount[cat]));

  // Get Top 7 categories by volume
  const combined = catNames.map((name, i) => ({
    name, 
    avg: avgPrices[i], 
    count: catPriceCount[name]
  })).sort((a, b) => b.count - a.count).slice(0, 7);

  const finalCatLabels = combined.map(c => c.name);
  const finalCatPrices = combined.map(c => c.avg);

  // Gradient for Bar Chart
  const ctxPrice = document.getElementById('priceChart').getContext('2d');
  let gradientBar = ctxPrice.createLinearGradient(0, 0, 0, 400);
  gradientBar.addColorStop(0, 'rgba(139, 92, 246, 0.8)'); // Purple
  gradientBar.addColorStop(1, 'rgba(59, 130, 246, 0.2)'); // Blue

  new Chart(ctxPrice, {
    type: 'bar',
    data: {
      labels: finalCatLabels,
      datasets: [{
        label: 'Average Price (MAD)',
        data: finalCatPrices,
        backgroundColor: gradientBar,
        borderRadius: 6,
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function(context) {
              return context.parsed.y + ' MAD';
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: 'rgba(255, 255, 255, 0.05)' }
        },
        x: {
          grid: { display: false },
          ticks: {
             callback: function(val, index) {
               let label = this.getLabelForValue(val);
               return label.length > 12 ? label.substring(0, 10) + '...' : label;
             }
          }
        }
      }
    }
  });
}

// Render Top Deals Table
function renderTopDealsTable() {
  const tbody = document.querySelector("#deals-table tbody");
  
  // Sort by highest discount percentage and slice top 10
  const sorted = [...dataset]
    .filter(item => typeof item.discount_pct === 'number')
    .sort((a, b) => b.discount_pct - a.discount_pct)
    .slice(0, 10);
    
  sorted.forEach(item => {
    const tr = document.createElement("tr");

    // Platform Badge formulation
    let sourceClass = "amazon"; // default fallback
    const srcLower = (item.source || "").toLowerCase();
    if(srcLower.includes("jumia")) sourceClass = "jumia";
    if(srcLower.includes("avito")) sourceClass = "avito";
    if(srcLower.includes("cdiscount")) sourceClass = "cdiscount";

    const badge = `<span class="platform-badge ${sourceClass}">${item.source || "Unknown"}</span>`;
    
    // Title truncation
    let rawTitle = item.title_clean || "Unnamed Product";
    const titleStr = rawTitle.length > 40 ? rawTitle.substring(0, 40) + "..." : rawTitle;
    
    // Prices
    const displayPrice = (item.price_offre_mad || item.price_initial_mad || 0).toLocaleString();
    const discountStr = `-${item.discount_pct}%`;

    tr.innerHTML = `
      <td>${badge}</td>
      <td title="${rawTitle}"><a href="${item.link || '#'}" target="_blank" style="color: inherit; text-decoration: none;">${titleStr}</a></td>
      <td class="discount-tag">${discountStr}</td>
      <td><strong>${displayPrice}</strong></td>
    `;
    
    tbody.appendChild(tr);
  });
}

// Boot up
document.addEventListener("DOMContentLoaded", initDashboard);

// ==========================
//   OFFRES SECTION
// ==========================

// Chart instances we'll need to destroy & re-create on tab switch
let offresByCatChartInst = null;
let offresTypeChartInst  = null;

// Platform color palette (consistent with doughnut)
const PLATFORM_COLORS = {
  amazon:    { fill: 'rgba(245,158,11,0.75)',   border: 'rgba(245,158,11,1)' },
  jumia:     { fill: 'rgba(249,115,22,0.75)',   border: 'rgba(249,115,22,1)' },
  avito:     { fill: 'rgba(236,72,153,0.75)',   border: 'rgba(236,72,153,1)' },
  cdiscount: { fill: 'rgba(59,130,246,0.75)',   border: 'rgba(59,130,246,1)'  },
  unknown:   { fill: 'rgba(148,163,184,0.75)',  border: 'rgba(148,163,184,1)' },
};

function platformKey(src) {
  const s = (src || '').toLowerCase();
  if (s.includes('amazon'))    return 'amazon';
  if (s.includes('jumia'))     return 'jumia';
  if (s.includes('avito'))     return 'avito';
  if (s.includes('cdiscount')) return 'cdiscount';
  return 'unknown';
}

function renderOffresSection(filterSource = 'all') {
  // ── Filter dataset ────────────────────────────────────────────────────
  const filtered = filterSource === 'all'
    ? dataset
    : dataset.filter(d => (d.source || '').toLowerCase().includes(filterSource.toLowerCase()));

  const withOffer = filtered.filter(d =>
    d.offre_type ||
    (typeof d.discount_pct === 'number' && d.discount_pct > 0)
  );

  // ── Mini KPIs ─────────────────────────────────────────────────────────
  document.getElementById('total-offres').textContent   = withOffer.length.toLocaleString();
  document.getElementById('pct-offres').textContent     =
    filtered.length ? ((withOffer.length / filtered.length) * 100).toFixed(1) + '%' : '—';

  // Best platform = highest avg discount
  const srcAvg = {};
  const srcCnt = {};
  dataset.forEach(d => {
    if (typeof d.discount_pct !== 'number' || d.discount_pct <= 0) return;
    const k = d.source || 'Unknown';
    srcAvg[k] = (srcAvg[k] || 0) + d.discount_pct;
    srcCnt[k] = (srcCnt[k] || 0) + 1;
  });
  let bestSrc = '—', bestAvgVal = 0;
  Object.keys(srcAvg).forEach(k => {
    const avg = srcAvg[k] / srcCnt[k];
    if (avg > bestAvgVal) { bestAvgVal = avg; bestSrc = k; }
  });
  document.getElementById('best-offre-src').textContent = bestSrc;

  // ── Category aggregation ──────────────────────────────────────────────
  const catStats = {};   // { cat: { total, withOffer, sumDisc, maxDisc } }
  filtered.forEach(d => {
    const cat = d.category || 'Other';
    if (!catStats[cat]) catStats[cat] = { total: 0, withOffer: 0, sumDisc: 0, maxDisc: 0 };
    catStats[cat].total++;
    const disc = typeof d.discount_pct === 'number' ? d.discount_pct : 0;
    if (disc > 0 || d.offre_type) {
      catStats[cat].withOffer++;
      catStats[cat].sumDisc  += disc;
      catStats[cat].maxDisc   = Math.max(catStats[cat].maxDisc, disc);
    }
  });

  // Sort by number of offers descending, take top 8 for chart
  const sorted = Object.entries(catStats)
    .filter(([, v]) => v.withOffer > 0)
    .sort(([, a], [, b]) => b.withOffer - a.withOffer);

  const top8 = sorted.slice(0, 8);

  // ── Chart 1: Avg Discount % per Category ─────────────────────────────
  if (offresByCatChartInst) offresByCatChartInst.destroy();

  const catLabels   = top8.map(([k]) => k.length > 14 ? k.slice(0, 13) + '…' : k);
  const catAvgDiscs = top8.map(([, v]) => v.withOffer > 0 ? +(v.sumDisc / v.withOffer).toFixed(1) : 0);

  const ctx1 = document.getElementById('offresByCatChart').getContext('2d');
  const grad1 = ctx1.createLinearGradient(0, 0, 0, 340);
  grad1.addColorStop(0, 'rgba(139,92,246,0.85)');
  grad1.addColorStop(1, 'rgba(59,130,246,0.3)');

  offresByCatChartInst = new Chart(ctx1, {
    type: 'bar',
    data: {
      labels: catLabels,
      datasets: [{
        label: 'Avg Discount %',
        data: catAvgDiscs,
        backgroundColor: grad1,
        borderRadius: 6,
        borderWidth: 0,
      }]
    },
    options: {
      indexAxis: 'y',            // Horizontal bar → more readable labels
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => ctx.parsed.x.toFixed(1) + '%' } },
      },
      scales: {
        x: {
          beginAtZero: true,
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { callback: v => v + '%' },
        },
        y: { grid: { display: false } },
      },
    },
  });

  // ── Chart 2: Offer Type Distribution per Platform ─────────────────────
  if (offresTypeChartInst) offresTypeChartInst.destroy();

  // Aggregate: for each source, count pourcentage vs forfaite vs none
  const sources = [...new Set(filtered.map(d => d.source || 'Unknown'))].sort();
  const pctCounts  = sources.map(s =>
    filtered.filter(d => (d.source || 'Unknown') === s && d.offre_type === 'pourcentage').length
  );
  const flatCounts = sources.map(s =>
    filtered.filter(d => (d.source || 'Unknown') === s && d.offre_type === 'forfaite').length
  );
  const noneCounts = sources.map((s, i) => {
    const total = filtered.filter(d => (d.source || 'Unknown') === s).length;
    return total - pctCounts[i] - flatCounts[i];
  });

  const ctx2 = document.getElementById('offresTypeChart').getContext('2d');
  offresTypeChartInst = new Chart(ctx2, {
    type: 'bar',
    data: {
      labels: sources,
      datasets: [
        {
          label: 'Pourcentage',
          data: pctCounts,
          backgroundColor: 'rgba(139,92,246,0.8)',
          borderRadius: 4,
        },
        {
          label: 'Forfaitaire',
          data: flatCounts,
          backgroundColor: 'rgba(59,130,246,0.8)',
          borderRadius: 4,
        },
        {
          label: 'No Offer',
          data: noneCounts,
          backgroundColor: 'rgba(148,163,184,0.25)',
          borderRadius: 4,
        },
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { boxWidth: 12, padding: 16 },
        },
      },
      scales: {
        x: { stacked: true, grid: { display: false } },
        y: { stacked: true, grid: { color: 'rgba(255,255,255,0.05)' } },
      },
    },
  });

  // ── Category breakdown table ──────────────────────────────────────────
  const tbody = document.querySelector('#offres-category-table tbody');
  tbody.innerHTML = '';

  sorted.forEach(([cat, v]) => {
    const coverage = v.total > 0 ? (v.withOffer / v.total) * 100 : 0;
    const avgDisc  = v.withOffer > 0 ? (v.sumDisc / v.withOffer).toFixed(1) + '%' : '—';
    const bestDeal = v.maxDisc > 0  ? '-' + v.maxDisc.toFixed(0) + '%' : '—';
    const coveragePct = coverage.toFixed(1) + '%';

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${cat}</strong></td>
      <td>${v.total.toLocaleString()}</td>
      <td>${v.withOffer.toLocaleString()}</td>
      <td>
        <div class="coverage-bar-wrap">
          <div class="coverage-bar">
            <div class="coverage-bar-fill" style="width:${Math.min(coverage,100)}%"></div>
          </div>
          <span class="coverage-pct">${coveragePct}</span>
        </div>
      </td>
      <td>${avgDisc}</td>
      <td class="discount-tag">${bestDeal}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ── Tab wiring ────────────────────────────────────────────────────────────────
function initOffresTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const src = btn.dataset.source;
      const label = src === 'all' ? '— All Platforms' : `— ${btn.textContent.trim()}`;
      document.getElementById('filter-label-display').textContent = label;
      renderOffresSection(src);
    });
  });
}

// ==========================
//   CATEGORY TREE
// ==========================

/**
 * Hierarchical mapping: parent group → { icon, children[] }
 * Each child is a raw `category` value from the dataset.
 * Categories that overlap conceptually are grouped under the same parent.
 */
const CATEGORY_TREE_MAP = [
  {
    label: 'Tech & Computing',
    icon: '💻',
    children: ['Informatique']
  },
  {
    label: 'Mobile & Tablets',
    icon: '📱',
    children: ['Smartphones', 'Tablettes', 'Téléphones & Tablettes']
  },
  {
    label: 'Home & Appliances',
    icon: '🏠',
    children: ['Maison', 'Maison & Cuisine', 'Électroménager']
  },
  {
    label: 'Entertainment',
    icon: '🎮',
    children: ['Gaming', 'Jouets', 'Jeux & Jouets']
  },
  {
    label: 'TV, Audio & Photo',
    icon: '📺',
    children: ['TV & Vidéo', 'TV & Home Cinéma', 'Audio', 'Photo & Caméra']
  },
  {
    label: 'Fashion & Accessories',
    icon: '👗',
    children: ['Mode Femme', 'Mode Homme', 'Montres', 'Accessoires']
  },
  {
    label: 'Beauty & Health',
    icon: '✨',
    children: ['Beauté', 'Beauté & Santé']
  },
  {
    label: 'Sports & Outdoors',
    icon: '⚽',
    children: ['Sport']
  },
  {
    label: 'Electronics (General)',
    icon: '🔌',
    children: ['Électronique']
  }
];

/**
 * Build live stats per raw category from the loaded dataset.
 * Returns Map<category, { count, sources, withOffer, sumDisc, maxDisc, priceSum, priceCount }>
 */
function buildCategoryStats() {
  const stats = new Map();
  dataset.forEach(d => {
    const cat = d.category || 'Other';
    if (!stats.has(cat)) stats.set(cat, {
      count: 0, sources: new Set(),
      withOffer: 0, sumDisc: 0, maxDisc: 0,
      priceSum: 0, priceCount: 0
    });
    const s = stats.get(cat);
    s.count++;
    s.sources.add(d.source || 'Unknown');

    const disc = typeof d.discount_pct === 'number' ? d.discount_pct : 0;
    if (disc > 0 || d.offre_type) {
      s.withOffer++;
      s.sumDisc += disc;
      s.maxDisc = Math.max(s.maxDisc, disc);
    }

    const price = d.price_offre_mad || d.price_initial_mad || 0;
    if (price > 0 && price < 100000) { s.priceSum += price; s.priceCount++; }
  });
  return stats;
}

/**
 * Build source tag HTML string
 */
function sourceTagsHTML(sources) {
  return [...sources].sort().map(src => {
    const key = platformKey(src);
    return `<span class="tree-source-tag ${key}">${src}</span>`;
  }).join('');
}

/**
 * Build a coverage bar HTML (same as in the offres table)
 */
function coverageBarHTML(coverage) {
  const pct = coverage.toFixed(1);
  return `
    <div class="coverage-bar-wrap">
      <div class="coverage-bar">
        <div class="coverage-bar-fill" style="width:${Math.min(coverage, 100)}%"></div>
      </div>
      <span class="coverage-pct">${pct}%</span>
    </div>`;
}

/**
 * Render the category tree as a hierarchical table into #category-tree-table
 */
function renderCategoryTree() {
  const tbody = document.querySelector('#category-tree-table tbody');
  if (!tbody) return;
  tbody.innerHTML = '';

  const stats = buildCategoryStats();

  // Track group IDs for expand/collapse
  let groupIdx = 0;

  CATEGORY_TREE_MAP.forEach(group => {
    const activeChildren = group.children.filter(c => stats.has(c));
    if (activeChildren.length === 0) return;

    const gid = `tree-group-${groupIdx++}`;

    // Aggregate parent stats
    let pTotal = 0, pWithOffer = 0, pSumDisc = 0, pMaxDisc = 0;
    let pPriceSum = 0, pPriceCount = 0;
    const pSources = new Set();
    activeChildren.forEach(c => {
      const s = stats.get(c);
      pTotal += s.count;
      pWithOffer += s.withOffer;
      pSumDisc += s.sumDisc;
      pMaxDisc = Math.max(pMaxDisc, s.maxDisc);
      pPriceSum += s.priceSum;
      pPriceCount += s.priceCount;
      s.sources.forEach(src => pSources.add(src));
    });

    const pCoverage = pTotal > 0 ? (pWithOffer / pTotal) * 100 : 0;
    const pAvgDisc = pWithOffer > 0 ? (pSumDisc / pWithOffer).toFixed(1) + '%' : '—';
    const pBestDeal = pMaxDisc > 0 ? '-' + pMaxDisc.toFixed(0) + '%' : '—';
    const pAvgPrice = pPriceCount > 0 ? Math.round(pPriceSum / pPriceCount).toLocaleString() : '—';

    // Parent row
    const parentTr = document.createElement('tr');
    parentTr.className = 'tree-parent-row';
    parentTr.dataset.group = gid;
    parentTr.innerHTML = `
      <td>
        <span class="tree-row-toggle" data-group="${gid}">▶</span>
        <span class="tree-parent-icon">${group.icon}</span>
        <strong>${group.label}</strong>
      </td>
      <td class="tree-parent-count">${pTotal.toLocaleString()}</td>
      <td class="tree-parent-count">${pWithOffer.toLocaleString()}</td>
      <td>${coverageBarHTML(pCoverage)}</td>
      <td class="tree-parent-discount">${pAvgDisc}</td>
      <td class="discount-tag">${pBestDeal}</td>
      <td>${pAvgPrice}</td>
      <td><div class="tree-sources">${sourceTagsHTML(pSources)}</div></td>
    `;
    tbody.appendChild(parentTr);

    // Child rows (initially collapsed)
    activeChildren.forEach((catName, idx) => {
      const s = stats.get(catName);
      const coverage = s.count > 0 ? (s.withOffer / s.count) * 100 : 0;
      const avgDisc = s.withOffer > 0 ? (s.sumDisc / s.withOffer).toFixed(1) + '%' : '—';
      const bestDeal = s.maxDisc > 0 ? '-' + s.maxDisc.toFixed(0) + '%' : '—';
      const avgPrice = s.priceCount > 0 ? Math.round(s.priceSum / s.priceCount).toLocaleString() : '—';
      const isLast = idx === activeChildren.length - 1;

      const childTr = document.createElement('tr');
      childTr.className = `tree-child-row collapsed ${isLast ? 'last-child' : ''}`;
      childTr.dataset.parent = gid;
      childTr.innerHTML = `
        <td>
          <span class="tree-child-dot"></span>
          <span class="tree-child-name">${catName}</span>
        </td>
        <td>${s.count.toLocaleString()}</td>
        <td>${s.withOffer.toLocaleString()}</td>
        <td>${coverageBarHTML(coverage)}</td>
        <td>${avgDisc}</td>
        <td class="discount-tag">${bestDeal}</td>
        <td>${avgPrice}</td>
        <td><div class="tree-sources">${sourceTagsHTML(s.sources)}</div></td>
      `;
      tbody.appendChild(childTr);
    });

    // Toggle click on parent row
    parentTr.addEventListener('click', () => {
      const toggle = parentTr.querySelector('.tree-row-toggle');
      toggle.classList.toggle('expanded');
      tbody.querySelectorAll(`tr[data-parent="${gid}"]`).forEach(row => {
        row.classList.toggle('collapsed');
      });
    });
  });

  // Wire Expand / Collapse all buttons
  document.getElementById('expand-all-btn')?.addEventListener('click', () => {
    tbody.querySelectorAll('.tree-child-row').forEach(row => row.classList.remove('collapsed'));
    tbody.querySelectorAll('.tree-row-toggle').forEach(el => el.classList.add('expanded'));
  });
  document.getElementById('collapse-all-btn')?.addEventListener('click', () => {
    tbody.querySelectorAll('.tree-child-row').forEach(row => row.classList.add('collapsed'));
    tbody.querySelectorAll('.tree-row-toggle').forEach(el => el.classList.remove('expanded'));
  });
}

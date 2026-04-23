// ==========================================
//   AuraMarket Analytics — Core Dashboard
// ==========================================

// --- Chart Global Configuration ---
Chart.defaults.color = 'hsla(210, 15%, 70%, 1)';
Chart.defaults.font.family = "'Outfit', sans-serif";
Chart.defaults.plugins.tooltip.backgroundColor = 'hsla(230, 25%, 10%, 0.9)';
Chart.defaults.plugins.tooltip.padding = 12;
Chart.defaults.plugins.tooltip.cornerRadius = 8;
Chart.defaults.plugins.tooltip.borderColor = 'hsla(255, 255%, 255%, 0.1)';
Chart.defaults.plugins.tooltip.borderWidth = 1;

// --- State Management ---
let fullDataset = [];
let filteredDataset = [];

// --- Initialization ---
async function initDashboard() {
    const statusText = document.getElementById('total-products');
    if (statusText) statusText.innerText = "Connecting...";

    try {
        // Try multiple potential paths to handle various server root configurations
        const pathsToTry = [
            '../../data/processed/unified_dataset.json',
            'data/processed/unified_dataset.json',
            '/data/processed/unified_dataset.json'
        ];
        
        let response = null;
        let successfulPath = "";

        for (const path of pathsToTry) {
            try {
                console.log(`Attempting to load data from: ${path}`);
                const res = await fetch(path);
                if (res.ok) {
                    response = res;
                    successfulPath = path;
                    break; 
                }
            } catch (e) {
                console.warn(`Path ${path} failed or blocked.`);
            }
        }

        if (!response) {
            throw new Error(`Data Connectivity Error: Failed to find unified_dataset.json in any mapped location. Ensure you are running the server from the project root.`);
        }
        
        console.log(`Successfully connected via: ${successfulPath}`);
        fullDataset = await response.json();
        console.log(`Payload received: ${fullDataset.length.toLocaleString()} rows.`);
        
        filteredDataset = [...fullDataset];
        refreshDashboard();
        setupEventListeners();
        
    } catch (error) {
        console.error("Dashboard Critical Error:", error);
        handleFetchError(error);
    }
}

function handleFetchError(error) {
    const kpiElements = ['total-products', 'avg-price', 'avg-discount', 'avg-rating'];
    kpiElements.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.innerText = "ERROR";
            el.style.color = "#ef4444";
        }
    });

    const banner = document.createElement('div');
    banner.style.cssText = "position: fixed; top: 20px; right: 20px; background: #991b1b; color: #fee2e2; padding: 24px; border-radius: 12px; z-index: 10000; box-shadow: 0 20px 50px rgba(0,0,0,0.6); max-width: 450px; border: 1px solid #f87171; font-family: sans-serif;";
    banner.innerHTML = `
        <div style="display: flex; align-items: flex-start; gap: 12px;">
            <div style="background: #f87171; color: #991b1b; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; flex-shrink: 0;">!</div>
            <div>
                <h4 style="margin: 0 0 10px 0; font-size: 1.1rem;">Data Synchronization Failure</h4>
                <p style="font-size: 0.9rem; line-height: 1.5; margin: 0 0 15px 0;">${error.message}</p>
                <div style="background: rgba(0,0,0,0.2); padding: 12px; border-radius: 6px; font-size: 0.8rem;">
                    <strong>Common Fixes:</strong>
                    <ul style="margin: 8px 0 0 18px; padding: 0;">
                        <li>Run the dashboard from the <code>PFA/</code> root directory.</li>
                        <li>If using VS Code, right-click the <b>PFA folder</b> and select 'Open with Live Server'.</li>
                        <li>Ensure <code>data/processed/unified_dataset.json</code> exists.</li>
                    </ul>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(banner);
}

function refreshDashboard() {
    if (!filteredDataset.length) return;
    
    calculateKPIs(filteredDataset);
    renderPlatformDistribution(filteredDataset);
    renderPriceBarChart(filteredDataset);
    renderDealsTable(filteredDataset);
    renderCategoryTree(filteredDataset);
    renderOffresSection(filteredDataset, 'all');
    
    if (window.lucide) window.lucide.createIcons();
}

// --- KPI Calculations ---
function calculateKPIs(data) {
    const total = data.length;
    let totalPrice = 0, priceCount = 0;
    let totalDisc = 0, discCount = 0;
    let totalRating = 0, ratCount = 0;

    data.forEach(item => {
        const price = parseFloat(item.price_offre_mad || item.price_initial_mad);
        if (!isNaN(price) && price > 0 && price < 1000000) {
            totalPrice += price;
            priceCount++;
        }
        const disc = parseFloat(item.discount_pct);
        if (!isNaN(disc) && disc > 0) {
            totalDisc += disc;
            discCount++;
        }
        const rat = parseFloat(item.rating);
        if (!isNaN(rat) && rat > 0) {
            totalRating += rat;
            ratCount++;
        }
    });

    const avgPrice = priceCount > 0 ? (totalPrice / priceCount).toFixed(0) : 0;
    const avgDisc = discCount > 0 ? (totalDisc / discCount).toFixed(1) : 0;
    const avgRat = ratCount > 0 ? (totalRating / ratCount).toFixed(1) : 0;

    animateValue("total-products", total);
    animateValue("avg-price", avgPrice, " MAD");
    animateValue("avg-discount", avgDisc, "%");
    animateValue("avg-rating", avgRat, " / 5");
}

function animateValue(id, value, suffix = "") {
    const obj = document.getElementById(id);
    if (!obj) return;
    
    if (value === 0 || value === "0") {
        obj.innerHTML = "0" + suffix;
        return;
    }

    const startValue = 0;
    const duration = 1200;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easeProgress = 1 - Math.pow(1 - progress, 3);
        const current = easeProgress * (Number(value) - startValue) + startValue;
        
        obj.innerHTML = current.toLocaleString(undefined, {
            maximumFractionDigits: (Number(value) % 1 === 0) ? 0 : 1
        }) + suffix;

        if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
}

// --- Chart Rendering ---
let charts = {};

function renderPlatformDistribution(data) {
    const counts = {};
    data.forEach(d => counts[d.source] = (counts[d.source] || 0) + 1);

    const canvas = document.getElementById('sourceChart');
    if (!canvas) return;
    
    if (charts.source) charts.source.destroy();

    charts.source = new Chart(canvas.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: Object.keys(counts),
            datasets: [{
                data: Object.values(counts),
                backgroundColor: [
                    'hsla(250, 100%, 65%, 0.8)',
                    'hsla(210, 100%, 55%, 0.8)',
                    'hsla(150, 100%, 45%, 0.8)',
                    'hsla(35, 100%, 55%, 0.8)',
                    'hsla(330, 100%, 65%, 0.8)',
                    'hsla(210, 20%, 40%, 0.8)'
                ],
                borderWidth: 0,
                hoverOffset: 20
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '75%',
            plugins: {
                legend: { position: 'bottom', labels: { padding: 20, usePointStyle: true, color: '#94a3b8' } }
            }
        }
    });
}

function renderPriceBarChart(data) {
    const cats = {};
    data.forEach(d => {
        const p = parseFloat(d.price_offre_mad || d.price_initial_mad);
        if (!isNaN(p) && p > 0) {
            const catName = d.category || "Uncategorized";
            if (!cats[catName]) cats[catName] = { sum: 0, count: 0 };
            cats[catName].sum += p;
            cats[catName].count++;
        }
    });

    const sorted = Object.entries(cats)
        .map(([name, v]) => ({ name, avg: Math.round(v.sum / v.count) }))
        .sort((a, b) => b.avg - a.avg)
        .slice(0, 8);

    const canvas = document.getElementById('priceChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (charts.price) charts.price.destroy();

    const grad = ctx.createLinearGradient(0, 0, 0, 400);
    grad.addColorStop(0, 'hsla(250, 100%, 65%, 0.9)');
    grad.addColorStop(1, 'hsla(250, 100%, 65%, 0.1)');

    charts.price = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sorted.map(d => d.name),
            datasets: [{
                label: 'Avg Price',
                data: sorted.map(d => d.avg),
                backgroundColor: grad,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#64748b' } },
                x: { grid: { display: false }, ticks: { color: '#64748b', font: { size: 10 } } }
            }
        }
    });
}

function renderDealsTable(data) {
    const tbody = document.querySelector("#deals-table tbody");
    if (!tbody) return;
    tbody.innerHTML = "";

    const deals = [...data]
        .filter(d => parseFloat(d.discount_pct) > 0)
        .sort((a, b) => parseFloat(b.discount_pct) - parseFloat(a.discount_pct))
        .slice(0, 10);

    deals.forEach(d => {
        const tr = document.createElement("tr");
        const srcClass = (d.source || "amazon").toLowerCase().replace(" ", "");
        const price = parseFloat(d.price_offre_mad || d.price_initial_mad);
        tr.innerHTML = `
            <td><span class="badge badge-${srcClass}">${d.source}</span></td>
            <td style="max-width: 280px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                <a href="${d.link}" target="_blank" style="color: inherit; text-decoration: none;">${d.title_clean}</a>
            </td>
            <td><span class="discount-pill">-${parseFloat(d.discount_pct).toFixed(0)}%</span></td>
            <td style="font-weight: 600; color: #fff;">${price.toLocaleString()} MAD</td>
        `;
        tbody.appendChild(tr);
    });
}

// --- Category Tree Logic ---
const CATEGORY_TREE_MAP = [
  { label: 'Tech & Computing', icon: '💻', children: ['Informatique'] },
  { label: 'Mobile & Tablets', icon: '📱', children: ['Smartphones', 'Tablettes', 'Téléphones & Tablettes'] },
  { label: 'Home & Appliances', icon: '🏠', children: ['Maison', 'Maison & Cuisine', 'Électroménager'] },
  { label: 'Entertainment', icon: '🎮', children: ['Gaming', 'Jouets', 'Jeux & Jouets'] },
  { label: 'TV, Audio & Photo', icon: '📺', children: ['TV & Vidéo', 'TV & Home Cinéma', 'Audio', 'Photo & Caméra'] },
  { label: 'Fashion & Accessories', icon: '👗', children: ['Mode Femme', 'Mode Homme', 'Montres', 'Accessoires'] },
  { label: 'Beauty & Health', icon: '✨', children: ['Beauté', 'Beauté & Santé'] },
  { label: 'Sports & Outdoors', icon: '⚽', children: ['Sport'] },
  { label: 'Electronics (General)', icon: '🔌', children: ['Électronique'] },
  { label: 'Steam Digital Store', icon: '🎮', children: ['Steam Specials', 'Steam Top Sellers', 'Steam Popular New', 'Steam All Games'] }
];

function buildCategoryStats(data) {
    const stats = new Map();
    data.forEach(d => {
        const cat = d.category || 'Other';
        if (!stats.has(cat)) stats.set(cat, {
            count: 0, sources: new Set(),
            withOffer: 0, sumDisc: 0, maxDisc: 0,
            priceSum: 0, priceCount: 0
        });
        const s = stats.get(cat);
        s.count++;
        s.sources.add(d.source);
        const disc = parseFloat(d.discount_pct);
        if (!isNaN(disc) && disc > 0) {
            s.withOffer++;
            s.sumDisc += disc;
            s.maxDisc = Math.max(s.maxDisc, disc);
        }
        const p = parseFloat(d.price_offre_mad || d.price_initial_mad);
        if (!isNaN(p) && p > 0 && p < 1000000) { s.priceSum += p; s.priceCount++; }
    });
    return stats;
}

function renderCategoryTree(data) {
    const tbody = document.querySelector('#category-tree-table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const stats = buildCategoryStats(data);
    let groupIdx = 0;

    CATEGORY_TREE_MAP.forEach(group => {
        const activeChildren = group.children.filter(c => stats.has(c));
        if (activeChildren.length === 0) return;

        const gid = `tree-group-${groupIdx++}`;
        let pTotal = 0, pWithOffer = 0, pSumDisc = 0, pMaxDisc = 0, pPriceSum = 0, pPriceCount = 0;
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
        const pAvgPrice = pPriceCount > 0 ? Math.round(pPriceSum / pPriceCount) : 0;

        const parentTr = document.createElement('tr');
        parentTr.className = 'tree-parent-row';
        parentTr.innerHTML = `
            <td>
                <span class="tree-row-toggle" data-group="${gid}">▶</span>
                <span style="font-size: 1.1rem; margin-right: 8px;">${group.icon}</span>
                <strong>${group.label}</strong>
            </td>
            <td style="color: var(--accent-primary); font-weight: 700;">${pTotal.toLocaleString()}</td>
            <td>${pWithOffer.toLocaleString()}</td>
            <td>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="flex:1; height: 6px; background: rgba(255,255,255,0.05); border-radius: 10px; overflow: hidden;">
                        <div style="width: ${pCoverage}%; height: 100%; background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));"></div>
                    </div>
                    <span style="font-size: 0.75rem; min-width: 30px;">${pCoverage.toFixed(0)}%</span>
                </div>
            </td>
            <td>${pWithOffer > 0 ? (pSumDisc / pWithOffer).toFixed(1) : 0}%</td>
            <td style="color: var(--accent-success); font-weight: 700;">-${pMaxDisc.toFixed(0)}%</td>
            <td>${pAvgPrice.toLocaleString()}</td>
            <td><div style="display: flex; gap: 4px; flex-wrap: wrap;">${Array.from(pSources).map(src => `<span class="badge badge-${src.toLowerCase().replace(' ', '')}" style="font-size: 0.6rem; padding: 2px 6px;">${src}</span>`).join('')}</div></td>
        `;
        tbody.appendChild(parentTr);

        activeChildren.forEach((catName, idx) => {
            const s = stats.get(catName);
            const coverage = s.count > 0 ? (s.withOffer / s.count) * 100 : 0;
            const isLast = idx === activeChildren.length - 1;

            const childTr = document.createElement('tr');
            childTr.className = `tree-child-row collapsed ${isLast ? 'last-child' : ''}`;
            childTr.dataset.parent = gid;
            childTr.innerHTML = `
                <td><span class="tree-child-name">${catName}</span></td>
                <td>${s.count.toLocaleString()}</td>
                <td>${s.withOffer.toLocaleString()}</td>
                <td>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="flex:1; height: 4px; background: rgba(255,255,255,0.05); border-radius: 10px; overflow: hidden;">
                            <div style="width: ${coverage}%; height: 100%; background: hsla(250, 100%, 65%, 0.4);"></div>
                        </div>
                        <span style="font-size: 0.7rem;">${coverage.toFixed(0)}%</span>
                    </div>
                </td>
                <td>${s.withOffer > 0 ? (s.sumDisc / s.withOffer).toFixed(1) : 0}%</td>
                <td style="color: var(--accent-success); opacity: 0.8;">-${s.maxDisc.toFixed(0)}%</td>
                <td>${Math.round(s.priceSum / (s.priceCount || 1)).toLocaleString()}</td>
                <td><div style="display: flex; gap: 4px;">${Array.from(s.sources).map(src => `<span class="badge badge-${src.toLowerCase().replace(' ', '')}" style="font-size: 0.6rem; opacity: 0.8;">${src}</span>`).join('')}</div></td>
            `;
            tbody.appendChild(childTr);
        });

        parentTr.addEventListener('click', () => {
            const toggle = parentTr.querySelector('.tree-row-toggle');
            if (toggle) toggle.classList.toggle('expanded');
            tbody.querySelectorAll(`tr[data-parent="${gid}"]`).forEach(row => row.classList.toggle('collapsed'));
        });
    });

    const expandBtn = document.getElementById('expand-all-btn');
    const collapseBtn = document.getElementById('collapse-all-btn');
    if (expandBtn) expandBtn.onclick = () => {
        tbody.querySelectorAll('.tree-child-row').forEach(r => r.classList.remove('collapsed'));
        tbody.querySelectorAll('.tree-row-toggle').forEach(t => t.classList.add('expanded'));
    };
    if (collapseBtn) collapseBtn.onclick = () => {
        tbody.querySelectorAll('.tree-child-row').forEach(r => r.classList.add('collapsed'));
        tbody.querySelectorAll('.tree-row-toggle').forEach(t => t.classList.remove('expanded'));
    };
}

// --- Multi-Channel Offer Depth (Section Logic) ---
let offresByCatChartInst = null;
let offresTypeChartInst  = null;

function renderOffresSection(data, filter = 'all') {
    // 1. Filter dataset by selected source tab
    const filtered = filter === 'all' 
        ? data 
        : data.filter(d => (d.source || "").toLowerCase().includes(filter.toLowerCase()));
    
    const tbody = document.querySelector('#offres-category-table tbody');
    if (!tbody) return;
    tbody.innerHTML = "";

    // 2. Data aggregation for Categories within the current platform filter
    const cats = {};
    filtered.forEach(d => {
        const catName = d.category || "Other";
        if (!cats[catName]) cats[catName] = { total: 0, off: 0, disc: 0, max: 0 };
        cats[catName].total++;
        const disc = parseFloat(d.discount_pct);
        if (!isNaN(disc) && disc > 0) {
            cats[catName].off++;
            cats[catName].disc += disc;
            cats[catName].max = Math.max(cats[catName].max, disc);
        }
    });

    const sortedCats = Object.entries(cats)
        .sort((a,b) => b[1].off - a[1].off)
        .slice(0, 10);

    // 3. Render Table with Coverage Bars
    sortedCats.forEach(([name, s]) => {
        const tr = document.createElement("tr");
        const coverage = ((s.off / s.total) * 100).toFixed(0);
        tr.innerHTML = `
            <td><strong>${name}</strong></td>
            <td>${s.total.toLocaleString()}</td>
            <td>${s.off.toLocaleString()}</td>
            <td>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="flex:1; height: 4px; background: hsla(255,255,255,0.05); border-radius: 4px; overflow: hidden;">
                        <div style="width: ${coverage}%; height: 100%; background: var(--accent-secondary);"></div>
                    </div>
                    <span style="font-size: 0.75rem;">${coverage}%</span>
                </div>
            </td>
            <td style="font-weight: 500;">${(s.disc / (s.off || 1)).toFixed(1)}%</td>
            <td style="color: var(--accent-success); font-weight: 700;">-${s.max.toFixed(0)}%</td>
        `;
        tbody.appendChild(tr);
    });

    // 4. Chart 1: Average Discount % by Category
    const ctx1 = document.getElementById('offresByCatChart');
    if (ctx1) {
        if (offresByCatChartInst) offresByCatChartInst.destroy();
        
        const catLabels = sortedCats.map(([n]) => n.length > 15 ? n.slice(0, 14) + '…' : n);
        const catAvgDisc = sortedCats.map(([, s]) => s.off > 0 ? (s.disc / s.off).toFixed(1) : 0);
        
        const grad = ctx1.getContext('2d').createLinearGradient(0, 0, 400, 0);
        grad.addColorStop(0, 'hsla(150, 100%, 45%, 0.4)');
        grad.addColorStop(1, 'hsla(150, 100%, 45%, 0.8)');

        offresByCatChartInst = new Chart(ctx1.getContext('2d'), {
            type: 'bar',
            data: {
                labels: catLabels,
                datasets: [{
                    label: 'Avg Discount %',
                    data: catAvgDisc,
                    backgroundColor: grad,
                    borderRadius: 4,
                    borderWidth: 0
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#64748b' } },
                    y: { grid: { display: false }, ticks: { color: '#94a3b8' } }
                }
            }
        });
    }

    // 5. Chart 2: Offer Type Stacked Bar (Proportion Analysis)
    const ctx2 = document.getElementById('offresTypeChart');
    if (ctx2) {
        if (offresTypeChartInst) offresTypeChartInst.destroy();

        // Get unique platforms in the current filter
        const sources = [...new Set(filtered.map(d => d.source || "Unknown"))].sort();
        
        const typeStats = sources.map(s => {
            const platformData = filtered.filter(d => (d.source || "Unknown") === s);
            const total = platformData.length;
            const percentages = platformData.filter(d => d.offre_type === 'pourcentage').length;
            const flats = platformData.filter(d => d.offre_type === 'forfaite').length;
            return {
                source: s,
                pourcentage: (percentages / total * 100).toFixed(1),
                forfaite: (flats / total * 100).toFixed(1),
                none: ( (total - percentages - flats) / total * 100).toFixed(1)
            };
        });

        offresTypeChartInst = new Chart(ctx2.getContext('2d'), {
            type: 'bar',
            data: {
                labels: typeStats.map(t => t.source),
                datasets: [
                    {
                        label: 'Pourcentage Deals (%)',
                        data: typeStats.map(t => t.pourcentage),
                        backgroundColor: 'hsla(250, 100%, 65%, 0.75)',
                        borderRadius: 4
                    },
                    {
                        label: 'Fixed Reduction (%)',
                        data: typeStats.map(t => t.forfaite),
                        backgroundColor: 'hsla(210, 100%, 55%, 0.75)',
                        borderRadius: 4
                    },
                    {
                        label: 'Standard Pricing (%)',
                        data: typeStats.map(t => t.none),
                        backgroundColor: 'hsla(210, 15%, 20%, 0.5)',
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { stacked: true, grid: { display: false }, ticks: { color: '#94a3b8' } },
                    y: { stacked: true, grid: { color: 'rgba(255,255,255,0.05)' }, border: { display: false }, ticks: { color: '#64748b' } }
                },
                plugins: {
                    legend: { position: 'bottom', labels: { padding: 20, color: '#94a3b8', font: { size: 10 } } }
                }
            }
        });
    }
}

// --- Interaction Drivers ---
function setupEventListeners() {
    const search = document.getElementById('global-search');
    if (search) {
        search.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            filteredDataset = fullDataset.filter(d => 
                (d.title_clean || "").toLowerCase().includes(query) || 
                (d.category || "").toLowerCase().includes(query) ||
                (d.source || "").toLowerCase().includes(query)
            );
            refreshDashboard();
        });
    }

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            renderOffresSection(filteredDataset, btn.dataset.source);
        });
    });
}

// Launch
initDashboard();

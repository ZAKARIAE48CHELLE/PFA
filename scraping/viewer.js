// ─── Source state ─────────────────────────────────────────────────────────────
let avitoData = [];
let jumiaData = [];
let activeSource = 'all'; // 'all' | 'avito' | 'jumia'

// ─── Helpers ──────────────────────────────────────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Unified price getter: avito uses .price, jumia uses .price_offre
function getPrice(item) {
  if (item._src === 'jumia') return item.price_offre || '';
  return item.price || '';
}

function parsePrice(str = '') {
  const n = parseFloat(str.replace(/\s/g, '').replace(/Dhs?|DH|MAD/gi, '').replace(',', '.'));
  return isNaN(n) ? null : n;
}

// Category badge for Avito (from link) vs Jumia (from .category field)
function getCategory(item) {
  if (item._src === 'jumia') {
    const cat = item.category || 'Autres';
    const map = {
      'Téléphones & Tablettes': { label: '📱 ' + cat, cls: 'cat-telephones' },
      'Informatique':           { label: '💻 ' + cat, cls: 'cat-info' },
      'Électronique':           { label: '🔌 ' + cat, cls: 'cat-elec' },
      'Électroménager':         { label: '🏠 ' + cat, cls: 'cat-elec' },
      'Mode Homme':             { label: '👔 ' + cat, cls: 'cat-mode' },
      'Mode Femme':             { label: '👗 ' + cat, cls: 'cat-mode' },
      'Beauté & Santé':         { label: '💄 ' + cat, cls: 'cat-beaute' },
      'Sport & Loisir':         { label: '⚽ ' + cat, cls: 'cat-sport' },
      'Jeux & Jouets':          { label: '🎮 ' + cat, cls: 'cat-jeux' },
      'Maison & Cuisine':       { label: '🛋️ ' + cat, cls: 'cat-maison' },
      'Accessoires':            { label: '⌚ ' + cat, cls: 'cat-autres' },
    };
    return map[cat] || { label: '📦 ' + cat, cls: 'cat-autres' };
  }
  // Avito: detect from link
  const link = item.link || '';
  if (/appartements|maisons|villas|immobilier|riads/.test(link)) return { label: '🏠 Immobilier', cls: 'cat-immobilier' };
  if (/voitures/.test(link))                                      return { label: '🚗 Voitures',   cls: 'cat-voitures' };
  if (/smartphone|téléphone|telephone|iphone|samsung/.test(link)) return { label: '📱 Téléphones', cls: 'cat-telephones' };
  if (/motos|velos|scooter/.test(link))                           return { label: '🏍️ Motos',     cls: 'cat-motos' };
  if (item.category) return { label: '📦 ' + item.category,      cls: 'cat-autres' };
  return { label: '📦 Autres', cls: 'cat-autres' };
}

// ─── Card renderer ────────────────────────────────────────────────────────────
function renderCards(data) {
  const grid  = document.getElementById('grid');
  const empty = document.getElementById('emptyState');
  grid.innerHTML = '';

  if (!data.length) { empty.style.display = 'block'; return; }
  empty.style.display = 'none';

  data.forEach((item, i) => {
    const cat     = getCategory(item);
    const price   = getPrice(item);
    const noPrc   = !price || price === 'Prix non indiqué';
    const isJumia = item._src === 'jumia';

    // Offer badge (Jumia only)
    let offerBadge = '';
    if (isJumia && item.offre) {
      offerBadge = `<span class="offer-badge">${escHtml(item.offre.valeur_offre)}</span>`;
    }

    // Source badge
    const srcBadge = isJumia
      ? `<span class="source-badge jumia-badge">Jumia</span>`
      : `<span class="source-badge avito-badge">Avito</span>`;

    // Prices row — Jumia shows both original & offer
    let priceHtml = '';
    if (isJumia) {
      const orig = item.price_initial;
      if (orig) priceHtml += `<span class="card-price-old">${escHtml(orig)}</span>`;
      priceHtml += `<span class="card-price ${noPrc ? 'no-price' : ''}">${escHtml(price || 'Prix non indiqué')}</span>`;
    } else {
      priceHtml = `<span class="card-price ${noPrc ? 'no-price' : ''}">${escHtml(price || 'Prix non indiqué')}</span>`;
    }

    const card = document.createElement('article');
    card.className = 'card';
    card.style.animationDelay = `${Math.min(i, 40) * 0.025}s`;
    card.innerHTML = `
      <div class="card-top-row">
        <span class="card-category ${cat.cls}">${cat.label}</span>
        ${srcBadge}${offerBadge}
      </div>
      <p class="card-title" title="${escHtml(item.title || '')}">${escHtml(item.title || '—')}</p>
      <div class="card-prices">${priceHtml}</div>
      <div class="card-meta">
        ${item.seller ? `
        <div class="card-meta-row">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>
          <span>${escHtml(item.seller)}</span>
        </div>` : ''}
        ${item.location ? `
        <div class="card-meta-row">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="10" r="3"/>
            <path d="M12 2a8 8 0 0 0-8 8c0 5.25 8 14 8 14s8-8.75 8-14a8 8 0 0 0-8-8z"/>
          </svg>
          <span>${escHtml(item.location)}</span>
        </div>` : ''}
        ${(isJumia && item.date) ? `
        <div class="card-meta-row">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>
          </svg>
          <span>${escHtml(item.date)}</span>
        </div>` : ''}
      </div>
      ${item.link ? `<a class="card-link" href="${escHtml(item.link)}" target="_blank" rel="noopener">Voir l'annonce →</a>` : ''}
    `;
    grid.appendChild(card);
  });
}

// ─── Data loading ─────────────────────────────────────────────────────────────
async function loadJSON(file) {
  try {
    const r = await fetch(file);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  } catch (e) {
    console.warn(`⚠ Could not load ${file}:`, e.message);
    return [];
  }
}

// ─── Merged dataset (current view) ────────────────────────────────────────────
function getMerged() {
  if (activeSource === 'avito') return avitoData;
  if (activeSource === 'jumia') return jumiaData;
  return [...avitoData, ...jumiaData];
}

// ─── Category filter options populate ─────────────────────────────────────────
function populateCategories(data) {
  const sel = document.getElementById('categoryFilter');
  const prev = sel.value;
  // clear except first option
  while (sel.options.length > 1) sel.remove(1);

  const cats = new Set(data.map(d => getCategory(d).label));
  cats.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c; opt.textContent = c;
    sel.appendChild(opt);
  });
  sel.value = cats.has(prev) ? prev : '';
}

// ─── Stats bar ────────────────────────────────────────────────────────────────
function updateStats() {
  const el = document.getElementById('sourceStats');
  el.textContent = `Avito: ${avitoData.length.toLocaleString()} · Jumia: ${jumiaData.length.toLocaleString()}`;
}

function updateCount(n) {
  document.getElementById('listingCount').textContent = `${n.toLocaleString()} annonce${n !== 1 ? 's' : ''}`;
}

// ─── Filtering & sorting ──────────────────────────────────────────────────────
function applyFilters() {
  const search   = document.getElementById('searchInput').value.toLowerCase().trim();
  const catVal   = document.getElementById('categoryFilter').value;
  const priceVal = document.getElementById('priceFilter').value;
  const sortVal  = document.getElementById('sortSelect').value;

  let result = getMerged().filter(item => {
    // Search
    const text = `${item.title || ''} ${item.seller || ''} ${item.location || ''} ${item.category || ''}`.toLowerCase();
    if (search && !text.includes(search)) return false;

    // Category
    if (catVal && getCategory(item).label !== catVal) return false;

    // Price filter
    const price = getPrice(item);
    const noPrice = !price || price === 'Prix non indiqué';
    if (priceVal === 'stated'   && noPrice)  return false;
    if (priceVal === 'unstated' && !noPrice) return false;
    if (priceVal === 'offer'    && !item.offre) return false;

    return true;
  });

  // Sort
  if (sortVal === 'price-asc') {
    result.sort((a, b) => (parsePrice(getPrice(a)) ?? Infinity) - (parsePrice(getPrice(b)) ?? Infinity));
  } else if (sortVal === 'price-desc') {
    result.sort((a, b) => (parsePrice(getPrice(b)) ?? -1) - (parsePrice(getPrice(a)) ?? -1));
  } else if (sortVal === 'title-asc') {
    result.sort((a, b) => (a.title || '').localeCompare(b.title || '', 'fr'));
  }

  updateCount(result.length);
  renderCards(result);
}

// ─── Source switcher ──────────────────────────────────────────────────────────
function switchSource(src) {
  activeSource = src;
  document.querySelectorAll('.src-btn').forEach(b => b.classList.toggle('active', b.dataset.src === src));
  populateCategories(getMerged());
  // reset filters
  document.getElementById('categoryFilter').value = '';
  applyFilters();
}

// ─── Init ─────────────────────────────────────────────────────────────────────
async function init() {
  // Show load state
  document.getElementById('grid').innerHTML = `
    <div class="loader"><div class="spinner"></div><p>Chargement des deux sources…</p></div>`;

  const [avRaw, juRaw] = await Promise.all([
    loadJSON('avito_data.json'),
    loadJSON('jumia_data.json'),
    loadJSON('avito_data_old.json')
  ]);

  // Tag each item with its source
  avitoData = avRaw.map(d => ({ ...d, _src: 'avito' }));
  jumiaData = juRaw.map(d => ({ ...d, _src: 'jumia' }));

  if (!avitoData.length && !jumiaData.length) {
    document.getElementById('grid').innerHTML = `
      <div class="loader" style="color:#fc8181">
        <p>⚠️ Aucun fichier JSON chargé.</p>
        <p style="font-size:.8rem;margin-top:8px">Vérifiez que avito_data.json et/ou jumia_data.json sont présents et utilisez un serveur local (ex: python -m http.server 5500).</p>
      </div>`;
    return;
  }

  updateStats();
  populateCategories(getMerged());
  applyFilters();

  // Bind controls
  document.getElementById('searchInput').addEventListener('input', applyFilters);
  document.getElementById('categoryFilter').addEventListener('change', applyFilters);
  document.getElementById('priceFilter').addEventListener('change', applyFilters);
  document.getElementById('sortSelect').addEventListener('change', applyFilters);

  // Source switcher buttons
  document.querySelectorAll('.src-btn').forEach(btn => {
    btn.addEventListener('click', () => switchSource(btn.dataset.src));
  });
}

init();

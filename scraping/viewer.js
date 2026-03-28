// ─── Source state ─────────────────────────────────────────────────────────────
let avitoData  = [];
let jumiaData  = [];
let amazonData = [];
let activeSource = 'all'; // 'all' | 'avito' | 'jumia' | 'amazon'

// ─── Helpers ──────────────────────────────────────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Unified price getter
function getPrice(item) {
  if (item._src === 'avito')  return item.price || '';
  return item.price_offre || '';   // jumia & amazon
}

function parsePrice(str = '') {
  const n = parseFloat(
    str.replace(/\s/g, '')
       .replace(/Dhs?|DH|MAD|€/gi, '')
       .replace(',', '.')
  );
  return isNaN(n) ? null : n;
}

// Get first offre regardless of array vs object shape (Amazon = array, Jumia = object)
function getFirstOffer(item) {
  if (!item.offre) return null;
  if (Array.isArray(item.offre)) return item.offre[0] || null;
  return item.offre;
}

// Star rating from numeric string "4.3" → ★★★★☆
function starsHtml(rating) {
  const n = parseFloat(rating);
  if (isNaN(n)) return '';
  const full  = Math.floor(n);
  const half  = (n - full) >= 0.3 ? 1 : 0;
  const empty = 5 - full - half;
  return '★'.repeat(full) + (half ? '½' : '') + '☆'.repeat(empty) + ` <small>${n}</small>`;
}

// Category badge
function getCategory(item) {
  // Amazon — use .category field directly
  if (item._src === 'amazon') {
    const cat = item.category || 'Autres';
    const amazonMap = {
      'Smartphones':            { label: '📱 ' + cat, cls: 'cat-telephones' },
      'Informatique':           { label: '💻 ' + cat, cls: 'cat-info' },
      'Tablettes':              { label: '📱 ' + cat, cls: 'cat-telephones' },
      'TV & Home Cinéma':       { label: '📺 ' + cat, cls: 'cat-elec' },
      'Audio':                  { label: '🔊 ' + cat, cls: 'cat-elec' },
      'Jeux vidéo':             { label: '🎮 ' + cat, cls: 'cat-jeux' },
      'Mode':                   { label: '👗 ' + cat, cls: 'cat-mode' },
      'Maison':                 { label: '🛋️ ' + cat, cls: 'cat-maison' },
      'Beauté':                 { label: '💄 ' + cat, cls: 'cat-beaute' },
      'Sport':                  { label: '⚽ ' + cat, cls: 'cat-sport' },
      'Jouets':                 { label: '🧸 ' + cat, cls: 'cat-jeux' },
      'Cuisine':                { label: '🍳 ' + cat, cls: 'cat-maison' },
    };
    return amazonMap[cat] || { label: '📦 ' + cat, cls: 'cat-autres' };
  }

  // Jumia — category field
  if (item._src === 'jumia') {
    const cat = item.category || 'Autres';
    const jumiaMap = {
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
    return jumiaMap[cat] || { label: '📦 ' + cat, cls: 'cat-autres' };
  }

  // Avito — detect from link
  const link = item.link || '';
  if (/appartements|maisons|villas|immobilier|riads/.test(link)) return { label: '🏠 Immobilier',  cls: 'cat-immobilier' };
  if (/voitures/.test(link))                                      return { label: '🚗 Voitures',    cls: 'cat-voitures'   };
  if (/smartphone|t.l.phone|iphone|samsung/.test(link))          return { label: '📱 Téléphones',  cls: 'cat-telephones' };
  if (/motos|velos|scooter/.test(link))                          return { label: '🏍️ Motos',      cls: 'cat-motos'      };
  if (item.category) return { label: '📦 ' + item.category, cls: 'cat-autres' };
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
    const cat      = getCategory(item);
    const price    = getPrice(item);
    const noPrc    = !price || price === 'Prix non indiqué';
    const src      = item._src;
    const isAvito  = src === 'avito';
    const offer    = getFirstOffer(item);

    // Source badge
    const srcBadge = {
      avito:  `<span class="source-badge avito-badge">Avito</span>`,
      jumia:  `<span class="source-badge jumia-badge">Jumia</span>`,
      amazon: `<span class="source-badge amazon-badge">Amazon</span>`,
    }[src] || '';

    // Offer badge — show valeur_offre (% or label)
    let offerBadge = '';
    if (offer && offer.valeur_offre) {
      offerBadge = `<span class="offer-badge">${escHtml(offer.valeur_offre)}</span>`;
    }

    // Prices — show original (struck) + current
    let priceHtml = '';
    if (!isAvito) {
      if (item.price_initial) {
        priceHtml += `<span class="card-price-old">${escHtml(item.price_initial)}</span>`;
      }
      priceHtml += `<span class="card-price ${noPrc ? 'no-price' : ''}">${escHtml(price || 'Prix non indiqué')}</span>`;
    } else {
      priceHtml = `<span class="card-price ${noPrc ? 'no-price' : ''}">${escHtml(price || 'Prix non indiqué')}</span>`;
    }

    // Rating stars (Amazon + Jumia have it)
    const ratingRow = item.rating ? `
      <div class="card-meta-row rating-row">
        <span class="stars">${starsHtml(item.rating)}</span>
      </div>` : '';

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
        ${ratingRow}
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
        ${item.date ? `
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

// ─── Merged dataset ────────────────────────────────────────────────────────────
function getMerged() {
  if (activeSource === 'avito')  return avitoData;
  if (activeSource === 'jumia')  return jumiaData;
  if (activeSource === 'amazon') return amazonData;
  return [...avitoData, ...jumiaData, ...amazonData];
}

// ─── Category filter populate ─────────────────────────────────────────────────
function populateCategories(data) {
  const sel  = document.getElementById('categoryFilter');
  const prev = sel.value;
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
  document.getElementById('sourceStats').textContent =
    `Avito: ${avitoData.length.toLocaleString()} · Jumia: ${jumiaData.length.toLocaleString()} · Amazon: ${amazonData.length.toLocaleString()}`;
}

function updateCount(n) {
  document.getElementById('listingCount').textContent =
    `${n.toLocaleString()} annonce${n !== 1 ? 's' : ''}`;
}

// ─── Filtering & sorting ──────────────────────────────────────────────────────
function applyFilters() {
  const search   = document.getElementById('searchInput').value.toLowerCase().trim();
  const catVal   = document.getElementById('categoryFilter').value;
  const priceVal = document.getElementById('priceFilter').value;
  const sortVal  = document.getElementById('sortSelect').value;

  let result = getMerged().filter(item => {
    const text = `${item.title || ''} ${item.seller || ''} ${item.location || ''} ${item.category || ''}`.toLowerCase();
    if (search && !text.includes(search)) return false;
    if (catVal && getCategory(item).label !== catVal) return false;

    const price   = getPrice(item);
    const noPrice = !price || price === 'Prix non indiqué';
    if (priceVal === 'stated'   && noPrice)  return false;
    if (priceVal === 'unstated' && !noPrice) return false;
    if (priceVal === 'offer'    && !getFirstOffer(item)) return false;

    return true;
  });

  // Sort
  if (sortVal === 'price-asc') {
    result.sort((a, b) => (parsePrice(getPrice(a)) ?? Infinity) - (parsePrice(getPrice(b)) ?? Infinity));
  } else if (sortVal === 'price-desc') {
    result.sort((a, b) => (parsePrice(getPrice(b)) ?? -1) - (parsePrice(getPrice(a)) ?? -1));
  } else if (sortVal === 'title-asc') {
    result.sort((a, b) => (a.title || '').localeCompare(b.title || '', 'fr'));
  } else if (sortVal === 'rating-desc') {
    result.sort((a, b) => (parseFloat(b.rating) || 0) - (parseFloat(a.rating) || 0));
  }

  updateCount(result.length);
  renderCards(result);
}

// ─── Source switcher ──────────────────────────────────────────────────────────
function switchSource(src) {
  activeSource = src;
  document.querySelectorAll('.src-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.src === src)
  );
  populateCategories(getMerged());
  document.getElementById('categoryFilter').value = '';
  applyFilters();
}

// ─── Init ─────────────────────────────────────────────────────────────────────
async function init() {
  document.getElementById('grid').innerHTML =
    `<div class="loader"><div class="spinner"></div><p>Chargement des trois sources…</p></div>`;

  const [avRaw, juRaw, amRaw] = await Promise.all([
    loadJSON('avito/avito_data.json'),
    loadJSON('jumia_data.json'),
    loadJSON('amazon_data.json'),
  ]);

  avitoData  = avRaw.map(d => ({ ...d, _src: 'avito'  }));
  jumiaData  = juRaw.map(d => ({ ...d, _src: 'jumia'  }));
  amazonData = amRaw.map(d => ({ ...d, _src: 'amazon' }));

  if (!avitoData.length && !jumiaData.length && !amazonData.length) {
    document.getElementById('grid').innerHTML = `
      <div class="loader" style="color:#fc8181">
        <p>⚠️ Aucun fichier JSON chargé.</p>
        <p style="font-size:.8rem;margin-top:8px">
          Vérifiez que avito/avito_data.json, jumia_data.json et amazon_data.json
          sont présents et utilisez un serveur local (python -m http.server 5500).
        </p>
      </div>`;
    return;
  }

  updateStats();
  populateCategories(getMerged());
  applyFilters();

  document.getElementById('searchInput').addEventListener('input', applyFilters);
  document.getElementById('categoryFilter').addEventListener('change', applyFilters);
  document.getElementById('priceFilter').addEventListener('change', applyFilters);
  document.getElementById('sortSelect').addEventListener('change', applyFilters);

  document.querySelectorAll('.src-btn').forEach(btn =>
    btn.addEventListener('click', () => switchSource(btn.dataset.src))
  );
}

init();

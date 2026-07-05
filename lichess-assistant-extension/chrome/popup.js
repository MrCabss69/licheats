const API_BASE = 'http://127.0.0.1:8000';

// Heuristics for honest, sample-aware display.
const LOW_CONFIDENCE_DECISIVE = 15;
const LOW_SAMPLE_OPENING = 8;
const TOP_OPENINGS = 5;
const TOP_TIME_CONTROLS = 5;
const INITIAL_ANALYSIS_LIMIT = 100;
const DEEP_SYNC_LIMIT = 5000;
const SYNC_BATCH_SIZE = 1000;
const SYNC_POLL_MS = 1200;
const TAB_ORDER = ['prep', 'style', 'trends'];

const CASTLING_LABELS = {
  kingside: 'Castled short',
  queenside: 'Castled long',
  none: 'No castle',
};

const QUEEN_LABELS = {
  both_queens_present_final: 'Queens on board',
  both_queens_missing_final: 'Queens traded',
  opponent_queen_missing_final: 'Up a queen',
  player_queen_missing_final: 'Down a queen',
};

let currentNickname = null;
let currentCtx = null; // { nickname, yourColor, opponentColor } from content.js
let activeTab = 'prep';
let syncPollTimer = null;
let syncJobActive = false;
let lastRenderedSyncGames = 0;

// ---------- tiny DOM helpers (CSP-safe: no innerHTML with dynamic data) ----------
function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value == null) continue;
    if (key === 'class') node.className = value;
    else if (key === 'text') node.textContent = value;
    else if (key === 'style') node.setAttribute('style', value);
    else node.setAttribute(key, value);
  }
  for (const child of [].concat(children)) {
    if (child == null) continue;
    node.appendChild(typeof child === 'string' ? document.createTextNode(child) : child);
  }
  return node;
}

function svg(tag, attrs = {}) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  return node;
}

function $(id) { return document.getElementById(id); }

// ---------- formatting ----------
function capitalize(value) {
  if (!value) return '';
  return value[0].toUpperCase() + value.slice(1);
}

function decisive(bucket) {
  if (!bucket) return 0;
  return bucket.wins + bucket.losses + bucket.draws;
}

function clampPct(pct) {
  const value = Math.round(Number(pct) || 0);
  return Math.max(0, Math.min(100, value));
}

function winColor(pct) {
  if (pct >= 55) return 'var(--good)';
  if (pct < 45) return 'var(--bad)';
  return 'var(--even)';
}

function relativeTime(iso) {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const secs = Math.max(0, Math.round((Date.now() - then) / 1000));
  if (secs < 60) return 'just now';
  const mins = Math.round(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

function recordText(bucket) {
  return `${bucket.wins}-${bucket.losses}-${bucket.draws}`;
}

function wldSpan(bucket) {
  return el('span', { class: 'wld' }, [
    el('b', { class: 'w', text: String(bucket.wins) }), '-',
    el('b', { class: 'l', text: String(bucket.losses) }), '-',
    el('b', { class: 'd', text: String(bucket.draws) }),
  ]);
}

function metaParts(...parts) {
  return parts.filter(Boolean).join(' \u00b7 ');
}

function coverageParts(data) {
  const coverage = data.coverage || {};
  const analyzed = coverage.games_analyzed || data.games_count || 0;
  const total = coverage.total_known || null;
  const pct = total ? Math.round((Math.min(analyzed, total) / total) * 100) : null;
  return { analyzed, total, pct, isSyncing: Boolean(coverage.is_syncing) };
}

// ---------- reusable rows ----------
function metricLine(label, value) {
  return el('div', { class: 'metric-line' }, [
    el('span', { class: 'metric-label', text: label }),
    el('span', { class: 'metric-value', text: value }),
  ]);
}

function barRow(label, bucket) {
  const pct = clampPct(bucket.win_rate);
  const labelNode = typeof label === 'string'
    ? el('span', { class: 'row-title', text: label })
    : label;
  const fill = el('div', {
    class: 'bar-fill',
    style: `width:${pct}%;background:${winColor(bucket.win_rate)}`,
  });
  return el('div', { class: 'list-row' }, [
    el('div', { class: 'bar-head' }, [
      labelNode,
      el('span', { class: 'row-value', text: `${pct}%` }),
    ]),
    el('div', { class: 'bar-track' }, [fill]),
    el('div', { class: 'caption' }, [`n=${bucket.total} `, wldSpan(bucket)]),
  ]);
}

function sectionBlock(title, children, copy = null) {
  const body = [el('p', { class: 'section-title', text: title })];
  if (copy) body.push(el('p', { class: 'section-copy', text: copy }));
  body.push(...[].concat(children));
  return el('section', { class: 'section' }, body);
}

function emptyText(message) {
  return el('p', { class: 'empty', text: message });
}

function coverageMeter(data) {
  const coverage = coverageParts(data);
  if (!coverage.total) return null;
  const label = coverage.isSyncing
    ? `Syncing sample ${coverage.analyzed}/${coverage.total}`
    : `Sample coverage ${coverage.analyzed}/${coverage.total}`;
  return el('div', { class: 'coverage-meter', 'aria-label': label }, [
    el('div', { class: 'coverage-meter-top' }, [
      el('span', { class: 'coverage-label', text: label }),
      el('span', { class: 'coverage-value', text: `${coverage.pct}%` }),
    ]),
    el('div', { class: 'coverage-track' }, [
      el('div', { class: 'coverage-fill', style: `width:${coverage.pct}%` }),
    ]),
  ]);
}

// ---------- tabs ----------
function tabButton(tab) { return $(`tab-${tab}`); }
function tabPanel(tab) { return $(`${tab}Panel`); }

function setActiveTab(tab, { focus = false } = {}) {
  if (!TAB_ORDER.includes(tab)) return;
  activeTab = tab;
  for (const key of TAB_ORDER) {
    const selected = key === tab;
    const button = tabButton(key);
    const panel = tabPanel(key);
    button.setAttribute('aria-selected', selected ? 'true' : 'false');
    button.setAttribute('tabindex', selected ? '0' : '-1');
    panel.hidden = !selected;
  }
  if (focus) tabButton(tab).focus();
}

function moveTab(fromTab, delta) {
  const index = TAB_ORDER.indexOf(fromTab);
  const next = (index + delta + TAB_ORDER.length) % TAB_ORDER.length;
  setActiveTab(TAB_ORDER[next], { focus: true });
}

function initTabs() {
  for (const tab of TAB_ORDER) {
    const button = tabButton(tab);
    button.addEventListener('click', () => setActiveTab(tab));
    button.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
        event.preventDefault();
        moveTab(tab, 1);
      } else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
        event.preventDefault();
        moveTab(tab, -1);
      } else if (event.key === 'Home') {
        event.preventDefault();
        setActiveTab(TAB_ORDER[0], { focus: true });
      } else if (event.key === 'End') {
        event.preventDefault();
        setActiveTab(TAB_ORDER[TAB_ORDER.length - 1], { focus: true });
      }
    });
  }
}

// ---------- data selection ----------
function bucketEntries(table) {
  return Object.entries(table || {}).filter(([key, bucket]) => key !== 'unknown' && bucket.total > 0);
}

function prepEntries(data, ctx) {
  const opponentColor = ctx && ctx.opponentColor;
  if (opponentColor) {
    const colorEntries = bucketEntries((data.openings_by_color || {})[opponentColor]);
    if (colorEntries.length) {
      const strong = colorEntries.filter(([, bucket]) => bucket.total >= LOW_SAMPLE_OPENING);
      const fallback = colorEntries.filter(([, bucket]) => bucket.total >= 3);
      const pool = strong.length >= TOP_OPENINGS ? strong : fallback;
      if (pool.length) {
        return {
          title: `Prep against their ${capitalize(opponentColor)}`,
          copy: 'Lowest scoring opening lines in the color you are likely to face.',
          entries: pool.sort((a, b) => a[1].win_rate - b[1].win_rate || b[1].total - a[1].total),
        };
      }
    }
  }

  return {
    title: 'Their most-played openings',
    copy: opponentColor
      ? 'No reliable color-specific opening sample yet; showing volume instead.'
      : 'No board color context in this view; use volume to prioritize prep.',
    entries: bucketEntries(data.openings).sort((a, b) => b[1].total - a[1].total),
  };
}

function openingRow(name, bucket) {
  const title = el('span', { class: 'row-title', title: name }, [name]);
  if (bucket.total < LOW_SAMPLE_OPENING) title.appendChild(el('span', { class: 'tag', text: 'low sample' }));
  return barRow(title, bucket);
}

// ---------- hero ----------
function renderProfileSummary(data) {
  const profile = data.player || {};
  const displayName = profile.display_name || profile.username || currentNickname;
  const totalGames = data.total_games || 0;
  const bucket = {
    wins: data.wins || 0,
    losses: data.losses || 0,
    draws: data.draws || 0,
    win_rate: data.win_rate || 0,
  };

  setNickname(displayName);
  $('asOf').hidden = false;
  $('asOf').textContent = metaParts('Profile', relativeTime(data.generated_at), `${totalGames} public games`);

  const hero = $('heroVerdict');
  hero.replaceChildren();
  hero.appendChild(el('p', { class: 'verdict-label', text: 'Instant Lichess profile' }));
  hero.appendChild(el('div', { class: 'verdict-value' }, [
    el('span', { class: 'verdict-number', style: `color:${winColor(bucket.win_rate)}`, text: `${clampPct(bucket.win_rate)}%` }),
    el('span', { class: 'verdict-text', text: 'global win rate' }),
  ]));
  hero.appendChild(el('div', { class: 'hero-stats' }, [
    metricLine('Record', recordText(bucket)),
    metricLine('Blitz', data.ratings && data.ratings.blitz != null ? String(data.ratings.blitz) : 'n/a'),
    metricLine('Rapid', data.ratings && data.ratings.rapid != null ? String(data.ratings.rapid) : 'n/a'),
  ]));
  hero.hidden = false;
}

function renderHero(data, ctx) {
  const summary = data.summary;
  const profile = data.player || {};
  const displayName = profile.display_name || profile.username || currentNickname;
  const relative = relativeTime(data.generated_at);
  const source = data.source === 'refresh' ? 'Synced' : 'Cached';
  const coverage = coverageParts(data);
  const sample = coverage.total
    ? `${coverage.analyzed}/${coverage.total} games`
    : `${data.games_count} games`;

  setNickname(displayName);
  $('asOf').hidden = false;
  $('asOf').textContent = metaParts(source, relative, sample, coverage.isSyncing ? 'syncing' : null);

  const hero = $('heroVerdict');
  hero.replaceChildren();

  if (data.games_count === 0) {
    hero.appendChild(el('p', { class: 'verdict-label', text: 'No local games found for this opponent yet.' }));
    hero.appendChild(el('div', { class: 'hero-stats' }, [
      metricLine('Record', '0-0-0'),
      metricLine('Win rate', '0%'),
      metricLine('Avg opp', 'n/a'),
    ]));
    const meter = coverageMeter(data);
    if (meter) hero.appendChild(meter);
    hero.hidden = false;
    return;
  }

  const opponentColor = ctx && ctx.opponentColor;
  const colorBucket = opponentColor && data.by_color ? data.by_color[opponentColor] : null;
  const bucket = colorBucket && colorBucket.total > 0 ? colorBucket : summary;
  const pct = clampPct(bucket.win_rate);
  const hasColorVerdict = bucket === colorBucket;
  const lowSample = decisive(bucket) < LOW_CONFIDENCE_DECISIVE;
  const label = hasColorVerdict
    ? `You play ${capitalize(ctx.yourColor)} \u00b7 target their ${capitalize(opponentColor)}`
    : 'Overall local sample';
  const verdictText = hasColorVerdict
    ? `their ${capitalize(opponentColor)} win rate`
    : 'overall win rate';

  hero.appendChild(el('p', { class: 'verdict-label', text: label }));
  hero.appendChild(el('div', { class: 'verdict-value' }, [
    el('span', { class: 'verdict-number', style: `color:${winColor(bucket.win_rate)}`, text: `${pct}%` }),
    el('span', { class: 'verdict-text', text: verdictText }),
    lowSample ? el('span', { class: 'badge low', text: 'Low sample' }) : null,
  ]));
  hero.appendChild(el('div', { class: 'hero-stats' }, [
    metricLine('Record', recordText(summary)),
    metricLine('Overall', `${clampPct(summary.win_rate)}%`),
    metricLine(
      'Avg opp',
      summary.avg_opponent_rating != null ? String(Math.round(summary.avg_opponent_rating)) : 'n/a',
    ),
  ]));
  const meter = coverageMeter(data);
  if (meter) hero.appendChild(meter);
  hero.hidden = false;
}

// ---------- panels ----------
function renderPrepPanel(data, ctx) {
  const panel = $('prepPanel');
  panel.replaceChildren();

  if (data.games_count === 0) {
    panel.appendChild(emptyText('No games found yet. Try Refresh to sync public Lichess games.'));
    return;
  }

  const prep = prepEntries(data, ctx);
  const rows = prep.entries.slice(0, TOP_OPENINGS).map(([name, bucket]) => openingRow(name, bucket));
  panel.appendChild(rows.length
    ? sectionBlock(prep.title, rows, prep.copy)
    : emptyText('No opening data available for this sample.'));
}

function renderStylePanel(data) {
  const panel = $('stylePanel');
  panel.replaceChildren();

  const colorRows = [];
  for (const color of ['white', 'black']) {
    const bucket = data.by_color[color];
    if (bucket && bucket.total > 0) colorRows.push(barRow(`As ${capitalize(color)}`, bucket));
  }
  if (colorRows.length) panel.appendChild(sectionBlock('Color results', colorRows));

  const tendencyRows = [];
  for (const [key, label] of Object.entries(CASTLING_LABELS)) {
    const bucket = data.castling[key];
    if (bucket && bucket.total > 0) tendencyRows.push(barRow(label, bucket));
  }
  const queenRows = Object.entries(QUEEN_LABELS)
    .map(([key, label]) => [label, data.queen_presence[key]])
    .filter(([, bucket]) => bucket && bucket.total > 0)
    .sort((a, b) => b[1].total - a[1].total)
    .map(([label, bucket]) => barRow(label, bucket));
  tendencyRows.push(...queenRows);
  if (tendencyRows.length) {
    panel.appendChild(sectionBlock('Board tendencies', tendencyRows, 'Castling and queen-presence buckets from parsed games.'));
  }

  if (!panel.children.length) panel.appendChild(emptyText('No style buckets available for this sample.'));
}

function renderSparkline(data) {
  const points = data.rating_timeline;
  if (!points || points.length < 2) return null;

  const width = 360;
  const height = 48;
  const pad = 4;
  const ratings = points.map((point) => point.rating);
  const min = Math.min(...ratings);
  const max = Math.max(...ratings);
  const span = max - min || 1;
  const coords = points.map((point, index) => {
    const x = (index / (points.length - 1)) * (width - 2 * pad) + pad;
    const y = height - pad - ((point.rating - min) / span) * (height - 2 * pad);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');

  const chart = svg('svg', { class: 'spark', viewBox: `0 0 ${width} ${height}`, preserveAspectRatio: 'none' });
  chart.appendChild(svg('polyline', {
    points: coords,
    fill: 'none',
    stroke: 'var(--accent)',
    'stroke-width': '2.5',
    'stroke-linejoin': 'round',
    'stroke-linecap': 'round',
  }));
  return sectionBlock('Rating trend', [
    chart,
    el('p', {
      class: 'spark-meta',
      text: `${ratings[0]} to ${ratings[ratings.length - 1]}  (min ${min} \u00b7 max ${max})`,
    }),
  ]);
}

function renderTimeControls(data) {
  const entries = Object.entries(data.time_controls || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, TOP_TIME_CONTROLS);
  if (!entries.length) return null;

  return sectionBlock('Time controls', el('div', { class: 'compact-list' }, entries.map(([control, count]) =>
    el('div', { class: 'chip-row' }, [
      el('span', { class: 'chip-label', text: control }),
      el('span', { class: 'chip-value', text: `${count} games` }),
    ]),
  )));
}

function renderUnsupported(data) {
  if (!data.unsupported_metrics || !data.unsupported_metrics.length) return null;
  return el('section', { class: 'section note', text: data.unsupported_metrics.join(' ') });
}

function renderTrendsPanel(data) {
  const panel = $('trendsPanel');
  panel.replaceChildren();

  const sections = [
    renderSparkline(data),
    renderTimeControls(data),
    renderUnsupported(data),
  ].filter(Boolean);

  if (sections.length) {
    for (const section of sections) panel.appendChild(section);
  } else {
    panel.appendChild(emptyText('No trend data available for this sample.'));
  }
}

// ---------- orchestration ----------
function render(data) {
  renderHero(data, currentCtx);
  renderPrepPanel(data, currentCtx);
  renderStylePanel(data);
  renderTrendsPanel(data);
  setActiveTab(activeTab);
  $('content').hidden = false;
  $('refreshBtn').hidden = false;
}

// ---------- state machine ----------
function show(state, message, { preserveHero = false, preserveContent = false } = {}) {
  $('skeleton').hidden = state !== 'loading' || preserveContent;
  $('errorBox').hidden = state !== 'error';

  if ((state === 'loading' || state === 'error' || state === 'idle') && !preserveContent) {
    $('content').hidden = true;
  }
  if ((state === 'loading' || state === 'error') && !preserveHero) {
    $('asOf').hidden = true;
    $('heroVerdict').hidden = true;
  }
  if (state === 'error' && message != null) $('errorMsg').textContent = message;

  const status = $('status');
  if (message != null) status.textContent = message;
  status.hidden = state === 'ok' && !message;
}

function setNickname(nickname) {
  $('opponentNickname').textContent = nickname || 'Not found';
}

async function loadProfileSummary(username) {
  show('loading', 'Loading instant profile...');
  try {
    const encoded = encodeURIComponent(username);
    const response = await fetch(`${API_BASE}/players/${encoded}/profile-summary`);
    const body = await response.json();
    if (!response.ok) {
      throw new Error(body && body.error ? body.error.message : `HTTP ${response.status}`);
    }
    renderProfileSummary(body);
    show('loading', 'Profile loaded. Building prep sample...', { preserveHero: true });
  } catch (error) {
    const offline = error instanceof TypeError;
    show('error', offline
      ? 'Local Licheats API unreachable. Start it with: uv run licheats-api'
      : `Profile failed: ${error.message}`);
    throw error;
  }
}

async function loadAnalysis(
  username,
  { refresh = false, limit = INITIAL_ANALYSIS_LIMIT, preserveHero = false, passive = false } = {},
) {
  const btn = $('refreshBtn');
  btn.classList.add('spin');
  btn.disabled = true;
  show('loading', 'Loading local analysis...', { preserveHero, preserveContent: passive });
  try {
    const encoded = encodeURIComponent(username);
    const url = `${API_BASE}/players/${encoded}/analysis?limit=${limit}&refresh=${refresh}`;
    const response = await fetch(url);
    const body = await response.json();
    if (!response.ok) {
      throw new Error(body && body.error ? body.error.message : `HTTP ${response.status}`);
    }
    render(body);
    show('ok', `Analysis ${body.source === 'refresh' ? 'synced from Lichess' : 'loaded from local cache'}.`);
  } catch (error) {
    const offline = error instanceof TypeError; // fetch network failure
    show('error', offline
      ? 'Local Licheats API unreachable. Start it with: uv run licheats-api'
      : `Analysis failed: ${error.message}`);
  } finally {
    btn.classList.remove('spin');
    btn.disabled = syncJobActive;
  }
}

function clearSyncPoll() {
  if (syncPollTimer) clearTimeout(syncPollTimer);
  syncPollTimer = null;
  syncJobActive = false;
  lastRenderedSyncGames = 0;
}

function syncTargetText(status) {
  const target = status.total_known ? Math.min(status.limit, status.total_known) : status.limit;
  return `${status.fetched_games}/${target}`;
}

async function pollSyncJob(jobId) {
  try {
    const response = await fetch(`${API_BASE}/sync-jobs/${encodeURIComponent(jobId)}`);
    const status = await response.json();
    if (!response.ok) throw new Error(status.detail || `HTTP ${response.status}`);
    const progressMessage = `Syncing public games in background (${syncTargetText(status)}).`;

    show('loading', progressMessage, {
      preserveHero: true,
      preserveContent: true,
    });

    const shouldRender = status.status === 'complete'
      || status.fetched_games >= Math.max(INITIAL_ANALYSIS_LIMIT, lastRenderedSyncGames + SYNC_BATCH_SIZE);
    if (currentNickname && shouldRender) {
      lastRenderedSyncGames = status.fetched_games;
      const limit = Math.min(Math.max(status.fetched_games, INITIAL_ANALYSIS_LIMIT), DEEP_SYNC_LIMIT);
      await loadAnalysis(currentNickname, { limit, preserveHero: true, passive: true });
    }

    if (status.status === 'queued' || status.status === 'running') {
      show('loading', progressMessage, { preserveHero: true, preserveContent: true });
      syncPollTimer = setTimeout(() => pollSyncJob(jobId), SYNC_POLL_MS);
      return;
    }

    syncJobActive = false;
    syncPollTimer = null;
    $('refreshBtn').disabled = false;
    $('refreshBtn').classList.remove('spin');
    if (status.status === 'complete') {
      show('ok', `Background sync complete (${status.fetched_games} games).`);
    } else {
      show('error', `Background sync failed: ${status.error || 'unknown error'}`, { preserveHero: true, preserveContent: true });
    }
  } catch (error) {
    syncJobActive = false;
    syncPollTimer = null;
    $('refreshBtn').disabled = false;
    $('refreshBtn').classList.remove('spin');
    show('error', `Sync status failed: ${error.message}`, { preserveHero: true, preserveContent: true });
  }
}

async function startBackgroundSync(username) {
  clearSyncPoll();
  syncJobActive = true;
  const btn = $('refreshBtn');
  btn.classList.add('spin');
  btn.disabled = true;
  show('loading', 'Starting background sync...', { preserveHero: true, preserveContent: true });
  try {
    const encoded = encodeURIComponent(username);
    const url = `${API_BASE}/players/${encoded}/sync-jobs?limit=${DEEP_SYNC_LIMIT}&include_moves=false&page_size=${SYNC_BATCH_SIZE}`;
    const response = await fetch(url, { method: 'POST' });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(body && body.error ? body.error.message : `HTTP ${response.status}`);
    }
    lastRenderedSyncGames = 0;
    pollSyncJob(body.id);
  } catch (error) {
    syncJobActive = false;
    btn.classList.remove('spin');
    btn.disabled = false;
    show('error', `Could not start background sync: ${error.message}`, { preserveHero: true, preserveContent: true });
  }
}

function requestNickname() {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const tab = tabs && tabs[0];
    if (!tab || !tab.id) {
      show('idle', 'No active Lichess tab found.');
      return;
    }
    chrome.tabs.sendMessage(tab.id, { action: 'fetchNickname' }, (response) => {
      if (chrome.runtime.lastError) {
        show('idle', 'Open a Lichess game page to detect an opponent.');
        return;
      }
      currentCtx = response || null;
      const nickname = response && response.nickname;
      currentNickname = nickname;
      setNickname(nickname);
      if (!nickname) {
        show('idle', 'Could not detect an opponent on this page.');
        return;
      }
      loadProfileSummary(nickname)
        .catch(() => null)
        .finally(() => loadAnalysis(nickname, { preserveHero: true }));
    });
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  $('refreshBtn').addEventListener('click', () => {
    if (currentNickname) startBackgroundSync(currentNickname);
  });
  $('retryBtn').addEventListener('click', () => {
    if (currentNickname) {
      loadProfileSummary(currentNickname)
        .catch(() => null)
        .finally(() => loadAnalysis(currentNickname, { preserveHero: true }));
    }
    else requestNickname();
  });
  requestNickname();
});

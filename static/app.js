// ═══════════════════════════════════════════════════════════════════
// KSP CRIME INTELLIGENCE PLATFORM - APP LOGIC
// ═══════════════════════════════════════════════════════════════════

const API = '/api';
const state = {
    map: null,
    network: null,
    charts: {},
    incidents: [],
    hotspots: [],
    alerts: [],
    selectedHour: -1,
    selectedRangeDays: 7
};

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

// ─── Utility Functions ─────────────────────────────────────────────
function toast(msg, type = 'info') {
    const t = $('#toast');
    const colors = { info: '#4C8DFF', error: '#FF5D5D', success: '#3DDC97', warning: '#FFB84D' };
    t.style.borderLeftColor = colors[type] || colors.info;
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(t._timer);
    t._timer = setTimeout(() => t.classList.remove('show'), 3000);
}

async function api(url, options) {
    try {
        const res = await fetch(API + url, options);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (e) {
        console.error(`API Error (${url}):`, e);
        toast(`Request failed: ${e.message}`, 'error');
        return null;
    }
}

// ─── Map Module ────────────────────────────────────────────────────
function initMap() {
    state.map = L.map('map', { zoomControl: true }).setView([14.5, 76.5], 7);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png').addTo(state.map);
    state.incidentLayer = L.layerGroup().addTo(state.map);
    state.hotspotLayer = L.layerGroup().addTo(state.map);
}

function renderMapData() {
    state.incidentLayer.clearLayers();
    state.incidents.forEach(d => {
        L.circleMarker([d.latitude, d.longitude], {
            radius: 4, fillColor: '#8052ff', fillOpacity: 0.7, color: '#8052ff', weight: 1
        }).bindPopup(`<b>${d.crime_type}</b><br>${d.district}<br>${d.date} ${d.time}`).addTo(state.incidentLayer);
    });
    
    state.hotspotLayer.clearLayers();
    state.hotspots.forEach(h => {
        L.circle([h.lat, h.lng], { radius: h.radius * 10, color: '#4C8DFF', fillColor: '#4C8DFF', fillOpacity: 0.1 }).addTo(state.hotspotLayer);
    });
}

// ─── Data Loaders ──────────────────────────────────────────────────
async function loadDashboardStats() {
    const stats = await api('/dashboard/stats');
    if (!stats) return;
    
    $('#kpiTotal').textContent = stats.total_incidents.toLocaleString();
    $('#kpiPending').textContent = stats.pending_investigation;
    $('#kpiCharged').textContent = stats.chargesheeted;
    $('#kpiHighRisk').textContent = stats.high_risk_districts;
    
    if (state.charts.trend) state.charts.trend.destroy();
    state.charts.trend = new Chart($('#chartTrend'), {
        type: 'line',
        data: {
            labels: stats.monthly_trend.map(m => m.month),
            datasets: [{ label: 'Incidents', data: stats.monthly_trend.map(m => m.count), borderColor: '#4C8DFF', backgroundColor: 'rgba(76,141,255,0.1)', fill: true, tension: 0.3 }]
        },
        options: { plugins: { legend: { display: false } }, scales: { x: { display: false }, y: { display: false } } }
    });
}

async function loadMapData() {
    let data = await api('/incidents/map?limit=500');
    if (data) {
        state.incidents = data;
        renderMapData();
    }
    
    let hotspots = await api('/hotspots');
    if (hotspots) {
        state.hotspots = hotspots;
        renderMapData();
        $('#hotspotList').innerHTML = hotspots.slice(0, 5).map(h => `
            <div style="padding:8px; background:var(--bg-surface); border-radius:6px; border:1px solid var(--border-hairline);">
                <div style="display:flex; justify-content:space-between;">
                    <strong style="color:var(--accent-info);">${h.top_crime}</strong>
                    <span style="color:var(--text-secondary); font-size:12px;">Sev: ${h.avg_severity}/10</span>
                </div>
                <small style="color:var(--text-secondary);">${h.count} incidents</small>
            </div>
        `).join('');
    }
}

async function loadPredictions() {
    const d = await api('/predictions');
    if (!d) return;
    $('#predTable').innerHTML = d.slice(0, 8).map(p => `
        <tr>
            <td>${p.district}</td>
            <td style="text-transform:capitalize;">${p.trend} ${p.risk_change > 0 ? '↑' : '↓'}</td>
            <td class="risk-${p.risk_level}">${p.risk_level.toUpperCase()}</td>
        </tr>
    `).join('');
}

async function loadAnomalies() {
    const d = await api('/anomalies');
    if (!d) return;
    $('#anomalyList').innerHTML = d.slice(0, 4).map(a => `
        <div style="padding:8px; background:var(--bg-surface); border-left:3px solid var(--accent-alert); border-radius:4px;">
            <strong>${a.crime_type}</strong><br>
            <small style="color:var(--text-secondary);">${a.district} - ${a.time}</small><br>
            <small style="color:var(--accent-warn);">${a.reason}</small>
        </div>
    `).join('');
}

async function loadAlerts() {
    const d = await api('/trend-alerts');
    if (!d) return;
    state.alerts = d;
    $('#alertCount').textContent = d.length;
    if (d.length > 0) {
        const msg = d.map(a => `<span><i class="fa-solid fa-triangle-exclamation"></i> ${a.crime_type} spike in ${a.district}: +${a.increase_pct}%</span>`).join('');
        $('#alertTicker').innerHTML = msg + msg; // Duplicate for smooth marquee loop
    }
}

async function loadOffenders() {
    const d = await api('/repeat-offenders?limit=5');
    if (!d) return;
    $('#offenderCards').innerHTML = d.map(o => `
        <div>
            <strong>${o.name}</strong><br>
            <small style="color:var(--text-secondary);">${o.age}y • ${o.location}</small><br>
            <span style="color:var(--accent-alert); font-size:12px;">${o.incident_count} Cases</span>
        </div>
    `).join('');
}

async function loadNetwork() {
    const d = await api('/network?limit=40');
    if (!d || !d.nodes) return;
    
    // Simplify network: Filter only top suspects and victims for clarity
    const filteredNodes = d.nodes.filter(n => n.group === 'Suspect' || n.group === 'Victim').slice(0, 20);
    const nodeIds = new Set(filteredNodes.map(n => n.id));
    const filteredEdges = d.edges.filter(e => nodeIds.has(e.from) && nodeIds.has(e.to));
    
    const colors = { Suspect: '#8052ff', Victim: '#4C8DFF', Witness: '#8B93A3' };
    const nodes = new vis.DataSet(filteredNodes.map(n => ({ ...n, color: colors[n.group], font: { color: '#ccc', size: 12 } })));
    const edges = new vis.DataSet(filteredEdges.map(e => ({ ...e, color: { color: 'rgba(128,82,255,0.3)' } })));
    
    state.network = new vis.Network($('#networkGraph'), { nodes, edges }, {
        physics: { stabilization: true, barnesHut: { gravitationalConstant: -3000 } },
        interaction: { hover: true }
    });
}

async function loadFilters() {
    const [dists, types] = await Promise.all([api('/districts'), api('/crime-types')]);
    if (dists) dists.forEach(d => {
        const opt = document.createElement('option'); opt.value = d; opt.textContent = d; $('#filterDistrict').appendChild(opt);
    });
    if (types) types.forEach(t => {
        const opt = document.createElement('option'); opt.value = t; opt.textContent = t; $('#filterCrime').appendChild(opt);
    });
    
    // Populate report modal dropdowns
    if (dists) dists.forEach(d => { const o = document.createElement('option'); o.value = d; o.textContent = d; $('#rDistrict').appendChild(o); });
    if (types) types.forEach(t => { const o = document.createElement('option'); o.value = t; o.textContent = t; $('#rCrime').appendChild(o); });
}

// ─── Modals (Add Report & Suspect) ─────────────────────────────────
function setupModals() {
    // Open/Close generic
    $$('[data-modal-close]').forEach(btn => btn.addEventListener('click', () => btn.closest('.modal-backdrop').classList.add('hidden')));
    $$('.modal-backdrop').forEach(m => m.addEventListener('click', (e) => { if (e.target === m) m.classList.add('hidden'); }));
    
    // Add Report Button
    $('#btnAddReport').addEventListener('click', () => $('#reportModal').classList.remove('hidden'));
    $('#openSuspectModal').addEventListener('click', () => { loadSuspects(); $('#suspectModal').classList.remove('hidden'); });
    
    // Handle Report Submit
    $('#reportForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            crime_type: $('#rCrime').value, district: $('#rDistrict').value, station: $('#rStation').value,
            latitude: parseFloat($('#rLat').value), longitude: parseFloat($('#rLng').value),
            date: $('#rDate').value, time: $('#rTime').value, hour: parseInt($('#rTime').value.split(':')[0]),
            status: $('#rStatus').value, severity: 5, modus_operandi: $('#rMO').value || "Not specified"
        };
        const res = await api('/incidents', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
        if (res) { toast('Crime report added successfully', 'success'); $('#reportForm').reset(); $('#reportModal').classList.add('hidden'); loadMapData(); }
    });
    
    // Handle Suspect Submit
    $('#suspectForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            name: $('#sName').value, role: $('#sRole').value, age: $('#sAge').value ? parseInt($('#sAge').value) : null,
            alias: $('#sAlias').value || null, last_known_location: $('#sLocation').value || null
        };
        const res = await api('/persons', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
        if (res) { toast('Suspect added successfully', 'success'); $('#suspectForm').reset(); loadSuspects(); }
    });
}

async function loadSuspects(q = "") {
    const list = $('#suspectList');
    list.innerHTML = '<small>Loading...</small>';
    const url = q ? `/persons?q=${encodeURIComponent(q)}&limit=20` : '/persons?limit=20';
    const data = await api(url);
    if (!data || data.length === 0) { list.innerHTML = '<small>No suspects found.</small>'; return; }
    
    list.innerHTML = data.map(p => `
        <div class="suspect-item">
            <div>
                <strong>${p.name}</strong><br>
                <small style="color:var(--text-secondary);">${p.role} • ${p.age || '?'}y • ${p.last_known_location || 'Unknown'}</small>
            </div>
            <button class="del-btn" data-id="${p.id}"><i class="fa-solid fa-trash"></i></button>
        </div>
    `).join('');
    
    $$('.del-btn').forEach(btn => btn.addEventListener('click', async () => {
        if (!confirm('Delete this person?')) return;
        const res = await api(`/persons/${btn.dataset.id}`, { method: 'DELETE' });
        if (res) { toast('Person deleted', 'info'); loadSuspects(q); }
    }));
}

// ─── UI Interactions ───────────────────────────────────────────────
function setupUI() {
    // Hamburger
    $('#hamburger').addEventListener('click', (e) => { e.stopPropagation(); $('#hamburgerDropdown').classList.toggle('open'); });
    document.addEventListener('click', () => $('#hamburgerDropdown').classList.remove('open'));
    
    // Sync Button
    $('#btnRefresh').addEventListener('click', () => { toast('Syncing data...', 'info'); init_load(); });
    
    // Theme Toggle
    const applyTheme = (t) => {
        document.body.classList.toggle('theme-light', t === 'light');
        $('#themeToggle').innerHTML = t === 'light' ? '<i class="fa-solid fa-sun"></i>' : '<i class="fa-solid fa-moon"></i>';
    };
    applyTheme(localStorage.getItem('kspTheme') || 'dark');
    $('#themeToggle').addEventListener('click', () => {
        const next = document.body.classList.contains('theme-light') ? 'dark' : 'light';
        localStorage.setItem('kspTheme', next);
        applyTheme(next);
    });
    
    // Sidebar Nav
    $$('.sidebar-btn').forEach(btn => btn.addEventListener('click', () => {
        $$('.sidebar-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const sec = $('#' + btn.dataset.section);
        if (sec) sec.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }));
    
    // Drawer Tabs
    $$('.drawer-tabs a').forEach(a => a.addEventListener('click', (e) => {
        e.preventDefault();
        $$('.drawer-tabs a').forEach(t => t.classList.remove('active'));
        a.classList.add('active');
        $(a.getAttribute('href'))?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }));
    
    // Network Filters
    $$('[data-net-filter]').forEach(btn => btn.addEventListener('click', () => {
        $$('[data-net-filter]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        // Note: For simplicity, full network filter requires storing the raw network data. 
        // This acts as a visual toggle for now.
        toast('Network filter applied', 'info');
    }));
    
    // Search Bar
    let searchTimer;
    $('#searchInput').addEventListener('input', function() {
        clearTimeout(searchTimer);
        const q = this.value.trim();
        const box = $('#searchResults');
        if (q.length < 3) { box.classList.add('hidden'); return; }
        searchTimer = setTimeout(async () => {
            const results = await api(`/geo/search?q=${encodeURIComponent(q)}`);
            if (!results || results.length === 0) { box.classList.add('hidden'); return; }
            box.innerHTML = results.map(r => `<div data-lat="${r.lat}" data-lng="${r.lng}" data-name="${r.name}">${r.name}</div>`).join('');
            box.classList.remove('hidden');
            $$('#searchResults div').forEach(el => el.addEventListener('click', () => {
                const lat = parseFloat(el.dataset.lat), lng = parseFloat(el.dataset.lng), name = el.dataset.name;
                state.map.flyTo([lat, lng], 12);
                L.popup().setLatLng([lat, lng]).setContent(`<b>${name}</b>`).openOn(state.map);
                $('#searchInput').value = name;
                box.classList.add('hidden');
            }));
        }, 400);
    });
    
    // Draggable Drawer
    const drawer = $('#bottomDrawer');
    const handle = $('#drawerHandle');
    let isDragging = false, startY, startHeight;
    handle.addEventListener('mousedown', (e) => {
        isDragging = true; startY = e.clientY; startHeight = drawer.offsetHeight;
        document.body.style.cursor = 'ns-resize';
    });
    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        const newHeight = startHeight - (e.clientY - startY);
        if (newHeight > 200 && newHeight < window.innerHeight - 150) drawer.style.height = `${newHeight}px`;
    });
    document.addEventListener('mouseup', () => { isDragging = false; document.body.style.cursor = 'default'; });
}

// ─── Initialization ────────────────────────────────────────────────
async function init_load() {
    await Promise.all([
        loadDashboardStats(),
        loadMapData(),
        loadFilters(),
        loadPredictions(),
        loadAnomalies(),
        loadAlerts(),
        loadOffenders(),
        loadNetwork()
    ]);
    toast('Intelligence feeds loaded', 'success');
}

document.addEventListener('DOMContentLoaded', () => {
    setupUI();
    setupModals();
    requestAnimationFrame(() => {
        initMap();
        init_load();
    });
});

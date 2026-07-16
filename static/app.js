/* ═══════════════════════════════════════════════════════════════════
   KSP Crime Intelligence Platform — Complete Application Logic
   ═══════════════════════════════════════════════════════════════════ */

// ═══════════════════════════════════════════════════════════════════
// SECTION 1: STATE & CONFIGURATION
// ═══════════════════════════════════════════════════════════════════

// Auto-detect: served from FastAPI → relative URL, else absolute
const isServed = window.location.port === '8000';
let API = isServed ? '/api' : 'http://localhost:8000/api';

const CRIME_COLORS = {
    'Theft':'#8052ff','Robbery':'#ff4d6d','Burglary':'#ffb829','Murder':'#ff1744',
    'Assault':'#ff7a90','Cyber Crime':'#4aa8ff','Drug Offense':'#b46bff',
    'Vehicle Theft':'#ffb829','Chain Snatching':'#ffe071','Fraud':'#25c7b7',
    'Kidnapping':'#ff4d6d','Rioting':'#ff8d4d','Arson':'#ff5f33',
    'Sexual Offense':'#d92c5f','Cheating':'#ffd166'
};

// Application state
const state = {
    map: null,
    network: null,
    charts: {},
    boundaryLayer: null,
    stationLayer: null,
    incidentLayer: null,
    hotspotLayer: null,
    redzoneLayer: null,
    drilldownLayer: null,
    districtCrimeMap: {},
    allIncidents: [],
    allHotspots: [],
    trendAlerts: [],
    advancedMode: false,
    drilledDistrict: null,
    selectedHour: -1,
    selectedRangeDays: 7,
    usingFallback: false
};


// ═══════════════════════════════════════════════════════════════════
// SECTION 2: DETERMINISTIC FALLBACK DATA GENERATOR
// ═══════════════════════════════════════════════════════════════════

function makeRng(seed) {
    let s = seed;
    return function() { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; };
}
function pick(rng, arr) { return arr[Math.floor(rng() * arr.length)]; }
function wPick(rng, arr, w) {
    let t = w.reduce((a,b)=>a+b,0), r = rng()*t, a = 0;
    for (let i=0;i<arr.length;i++) { a+=w[i]; if(r<=a) return arr[i]; }
    return arr[arr.length-1];
}

function generateFallbackData() {
    const rng = makeRng(42);
    const DISTS = [
        {n:"Bangalore Urban",lat:12.97,lng:77.59},{n:"Bangalore Rural",lat:13.0,lng:77.5},
        {n:"Mysore",lat:12.30,lng:76.64},{n:"Hubli-Dharwad",lat:15.36,lng:75.12},
        {n:"Mangalore",lat:12.91,lng:74.86},{n:"Belgaum",lat:15.85,lng:74.50},
        {n:"Gulbarga",lat:17.33,lng:76.83},{n:"Davangere",lat:14.46,lng:75.93},
        {n:"Bellary",lat:15.14,lng:76.92},{n:"Shimoga",lat:13.93,lng:75.57},
        {n:"Tumkur",lat:13.34,lng:77.10},{n:"Raichur",lat:16.21,lng:77.35},
        {n:"Hassan",lat:13.01,lng:76.10},{n:"Udupi",lat:13.34,lng:74.74},
        {n:"Chitradurga",lat:14.23,lng:76.39},{n:"Mandya",lat:12.52,lng:76.90},
        {n:"Bidar",lat:17.91,lng:77.52},{n:"Dakshina Kannada",lat:12.85,lng:75.0},
        {n:"Uttara Kannada",lat:14.55,lng:74.50},{n:"Koppal",lat:15.35,lng:76.15},
        {n:"Gadag",lat:15.42,lng:75.63},{n:"Haveri",lat:14.79,lng:75.40},
        {n:"Bagalkot",lat:16.19,lng:75.69},{n:"Chamarajanagar",lat:11.92,lng:76.94},
        {n:"Kodagu",lat:12.34,lng:75.81},{n:"Ramanagara",lat:12.72,lng:77.28},
        {n:"Yadgir",lat:16.77,lng:77.13}
    ];
    const CR = ["Theft","Robbery","Burglary","Murder","Assault","Cyber Crime","Drug Offense","Vehicle Theft","Chain Snatching","Fraud","Kidnapping","Rioting","Arson","Sexual Offense","Cheating"];
    const CW = [15,8,10,3,12,10,7,12,8,7,2,3,1,3,6];
    const SEV = {Theft:3,Robbery:5,Burglary:4,Murder:10,Assault:6,"Cyber Crime":7,"Drug Offense":6,"Vehicle Theft":4,"Chain Snatching":3,Fraud:5,Kidnapping:9,Rioting:6,Arson:7,"Sexual Offense":9,Cheating:4};
    const ST = ["Under Investigation","Chargesheet Filed","Closed - Untraced","Convicted","Acquitted","Pending Trial"];
    const STA = ["Town PS","Rural PS","Central PS","East PS","West PS","North PS","South PS","Highway PS","Cyber PS","Women PS"];
    const MO = ["Break-in rear window","Distraction technique","Impersonation","Pickpocketing","Cyber phishing","Forced entry","Surveillance","Stolen vehicle","Social engineering","Fake documents","Snatching from vehicle","Hacking WiFi","Armed confrontation"];
    const FN = ["Ravi","Suresh","Manoj","Pradeep","Kumar","Venkatesh","Rajesh","Mohan","Nagaraj","Ganesh","Lakshmi","Sujatha","Geetha","Priya","Anitha"];
    const LN = ["Kumar","Reddy","Gowda","Sharma","Patil","Naik","Rao","Hegde","Shetty","Pai","Bhat","Kulkarni","Desai","Joshi"];
    const HW = [1,1,1,1,1,2,3,4,3,3,4,5,6,6,5,5,5,6,7,8,7,5,4,2];

    // Generate 2000 incidents with station names
    const incidents = [];
    const distCounts = {};
    for (let i = 0; i < 2000; i++) {
        const d = pick(rng, DISTS);
        const ct = wPick(rng, CR, CW);
        const hour = wPick(rng, Array.from({length:24},(_,i)=>i), HW);
        const m = 202301 + Math.floor(rng()*24);
        const day = 1 + Math.floor(rng()*28);
        const station = d.n.split(' ')[0] + " " + pick(rng, STA);
        incidents.push({
            id:i+1, crime_type:ct, district:d.n, station:station,
            latitude: d.lat+(rng()-0.5)*0.3, longitude: d.lng+(rng()-0.5)*0.3,
            date: `${Math.floor(m/100)}-${String(m%100).padStart(2,'0')}-${String(day).padStart(2,'0')}`,
            time: String(hour).padStart(2,'0')+':'+String(Math.floor(rng()*60)).padStart(2,'0'),
            hour: hour, severity: SEV[ct], status: pick(rng, ST), modus_operandi: pick(rng, MO)
        });
        distCounts[d.n] = (distCounts[d.n]||0) + 1;
    }

    // Hotspots
    const hotspots = DISTS.filter(d=>(distCounts[d.n]||0)>8).slice(0,12).map(d=>({
        lat:d.lat, lng:d.lng, count:distCounts[d.n]||15,
        top_crime:"Theft", top_crime_count:Math.floor((distCounts[d.n]||15)*0.3),
        peak_hour:18+Math.floor(rng()*4), avg_severity:+(4+rng()*4).toFixed(1),
        radius:Math.min(200,(distCounts[d.n]||15)*3)
    }));

    // Monthly trend
    const monthly = [];
    for (let m=0;m<24;m++) {
        monthly.push({month:`${2023+Math.floor(m/12)}-${String((m%12)+1).padStart(2,'0')}`, count:140+Math.floor(rng()*120)});
    }

    // Crime types
    const byType = CR.map(c=>({type:c, count:Math.floor(rng()*400)+50})).sort((a,b)=>b.count-a.count);

    // Hourly
    const hourly = Array.from({length:24},(_,h)=>({hour:h, count:Math.floor(40+160*Math.sin((h-4)/24*Math.PI*2)*0.5+rng()*40)}));

    // Severity
    const severity = [{level:"Low",count:700},{level:"Medium",count:900},{level:"High",count:350},{level:"Critical",count:50}];

    // District crime for map coloring
    const distCrime = DISTS.map(d=>({district:d.n, count:distCounts[d.n]||Math.floor(rng()*40)+5, avg_sev:+(3+rng()*5).toFixed(1)}));

    // Network
    const nodes = [], edges = [];
    for (let i=0;i<45;i++) {
        const role = i<18?"Suspect":i<33?"Victim":"Witness";
        nodes.push({id:String(i+1), label:pick(rng,FN)+" "+pick(rng,LN), title:pick(rng,FN)+" — "+role, group:role, value:role==="Suspect"?14:7});
    }
    for (let i=0;i<55;i++) {
        const from=String(1+Math.floor(rng()*45));
        let to=String(1+Math.floor(rng()*45)); while(to===from) to=String(1+Math.floor(rng()*45));
        edges.push({from, to, label:i<22?pick(rng,["Known Associate","Co-accused","Same Gang","Family Connection"]):"Co-involved", title:"linked", value:Math.floor(rng()*8)+1, dashes:i>=22});
    }

    // Predictions
    const predictions = DISTS.slice(0,18).map(d=>{
        const ch=Math.round((rng()-0.4)*60);
        return {district:d.n, historical_avg:+(140+rng()*100).toFixed(1), p1:Math.floor(140+rng()*100), p2:Math.floor(140+rng()*100), p3:Math.floor(140+rng()*100), trend:ch>10?"increasing":ch<-10?"decreasing":"stable", risk_change:ch, risk_level:ch>20?"high":ch>5?"medium":"low"};
    }).sort((a,b)=>b.risk_change-a.risk_change);

    // Anomalies
    const anomalies = incidents.slice(0,18).map(inc=>({...inc, reason:`Unusual ${inc.crime_type} in ${inc.district} at ${inc.time}`}));

    // Trend alerts
    const alerts = DISTS.slice(0,6).map(d=>{const p=Math.floor(30+rng()*120); return {district:d.n, crime_type:pick(rng,CR.slice(0,5)), recent:Math.floor(10+rng()*30), previous:Math.floor(5+rng()*15), increase_pct:p, severity:p>100?"critical":p>50?"high":"medium"};});

    // Offenders
    const offenders = Array.from({length:12},(_,i)=>{
        const name=pick(rng,FN)+" "+pick(rng,LN);
        const ds=[pick(rng,DISTS).n, pick(rng,DISTS).n];
        return {id:i+1, name, alias:name.charAt(0)+"."+name.split(" ")[1], age:25+Math.floor(rng()*30), gender:Math.random()>0.5?"Male":"Female", location:ds[0], incident_count:3+Math.floor(rng()*8), crime_types:[pick(rng,CR),pick(rng,CR)], methods:[pick(rng,MO),pick(rng,MO)], districts:[...new Set(ds)]};
    }).sort((a,b)=>b.incident_count-a.incident_count);

    // Socio-economic
    const socio = DISTS.map(d=>({district:d.n, crime_count:distCounts[d.n]||Math.floor(rng()*40)+5, avg_severity:+(3+rng()*5).toFixed(1), population_density:Math.floor(200+rng()*7800), urbanization_rate:+(0.2+rng()*0.75).toFixed(2), literacy_rate:+(0.6+rng()*0.35).toFixed(2), poverty_index:+(0.05+rng()*0.35).toFixed(2)}));

    // District drill-down data
    const drillDown = {};
    DISTS.forEach(d => {
        const dInc = incidents.filter(i=>i.district===d.n);
        const stations = {};
        const types = {};
        const hours = {};
        dInc.forEach(i => {
            stations[i.station] = (stations[i.station]||0)+1;
            types[i.crime_type] = (types[i.crime_type]||0)+1;
            hours[i.hour] = (hours[i.hour]||0)+1;
        });
        drillDown[d.n] = {
            total: dInc.length,
            avg_sev: dInc.length ? +(dInc.reduce((a,i)=>a+i.severity,0)/dInc.length).toFixed(1) : 0,
            stations: Object.entries(stations).map(([s,c])=>({station:s,count:c})).sort((a,b)=>b.count-a.count),
            types: Object.entries(types).map(([t,c])=>({type:t,count:c})).sort((a,b)=>b.count-a.count),
            hours: Array.from({length:24},(_,h)=>({hour:h, count:hours[h]||0}))
        };
    });

    return {
        stats:{total_incidents:2000, pending_investigation:500, chargesheeted:400, districts_active:27, stations_active:95, high_risk_districts:7, monthly_trend:monthly, by_crime_type:byType, by_district:DISTS.map(d=>({district:d.n,count:distCounts[d.n]||10})).sort((a,b)=>b.count-a.count).slice(0,10), hourly_distribution:hourly, severity_distribution:severity, district_crime:distCrime},
        incidents, hotspots, network:{nodes,edges}, predictions, anomalies, alerts, offenders, socio, drillDown,
        districts: DISTS.map(d=>d.n)
    };
}

// GENERATE FALLBACK DATA IMMEDIATELY — before anything else
const FALLBACK = generateFallbackData();


// ═══════════════════════════════════════════════════════════════════
// SECTION 3: API & UTILITY FUNCTIONS
// ═══════════════════════════════════════════════════════════════════

async function api(url) {
    try {
        const controller = new AbortController();
        const timeout = setTimeout(()=>controller.abort(), 15000);
        const r = await fetch(API + url, {signal: controller.signal});
        clearTimeout(timeout);
        if (!r.ok) throw new Error(r.status);
        return await r.json();
    } catch(e) {
        return null;
    }
}

function toast(msg, type) {
    const t = document.getElementById('toast');
    if (!t) return;
    if (t.dataset.lastMsg === msg && Date.now() - Number(t.dataset.lastAt || 0) < 1200) return;
    t.dataset.lastMsg = msg;
    t.dataset.lastAt = Date.now();
    const colors = {info:'#8052ff', error:'#FF2D2D', success:'#15846e', warning:'#FFB84D'};
    t.style.borderLeftColor = colors[type||'info']||colors.info;
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(t._timer);
    t._timer = setTimeout(()=>t.classList.remove('show'), 3500);
}

function animateCount(el, target) {
    if (!el) return;
    const dur=800, start=performance.now();
    const from=parseInt(el.textContent.replace(/,/g,''))||0;
    (function step(now){
        const p=Math.min((now-start)/dur,1);
        const e=1-Math.pow(1-p,3);
        el.textContent=Math.round(from+(target-from)*e).toLocaleString();
        if(p<1) requestAnimationFrame(step);
    })(start);
}

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

function showEmpty(el, msg) {
    if (!el) return;
    el.innerHTML = el.tagName === 'TBODY'
        ? `<tr><td colspan="5" class="empty-state">${msg}</td></tr>`
        : `<div class="empty-state">${msg}</div>`;
}


// ═══════════════════════════════════════════════════════════════════
// SECTION 4: MAP MODULE
// ═══════════════════════════════════════════════════════════════════

function initMap() {
    state.map = L.map('map', {zoomControl:true, attributionControl:false}).setView([14.5, 76.5], 7);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {maxZoom:18}).addTo(state.map);
    state.incidentLayer = L.layerGroup().addTo(state.map);
    state.hotspotLayer = L.layerGroup().addTo(state.map);
    state.redzoneLayer = L.layerGroup().addTo(state.map);
    state.drilldownLayer = L.layerGroup();
}

function crimeColor(type) { return CRIME_COLORS[type] || '#8052ff'; }

function renderIncidents(data) {
    state.incidentLayer.clearLayers();
    if (!data || !data.length) return;
    data.forEach(d => {
        const c = crimeColor(d.crime_type);
        L.circleMarker([d.latitude, d.longitude], {
            radius: 3, fillColor: c, fillOpacity: 0.55,
            color: c, weight: 0.5, opacity: 0.7
        }).bindPopup(`
            <div style="font-size:12px;min-width:150px">
                <div style="font-family:Inter;font-size:16px;color:${c};letter-spacing:1px">${d.crime_type}</div>
                <div style="margin-top:4px;color:#aaa">${d.district} — ${d.station}</div>
                <div style="color:#888">${d.date} ${d.time}</div>
                <div style="margin-top:4px"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${c};margin-right:4px"></span>Severity: ${d.severity}/10</div>
                <div style="color:#666;margin-top:2px">${d.status}</div>
            </div>
        `).addTo(state.incidentLayer);
    });
}

function renderHotspots(hotspots) {
    state.hotspotLayer.clearLayers();
    const list = $('#hotspotList');
    if (!list) return;
    if (!hotspots || !hotspots.length) {
        showEmpty(list, 'No hotspots for the current filters');
        return;
    }
    list.innerHTML = hotspots.slice(0,10).map((h,i) => {
        const icon = L.divIcon({
            className: '',
            html: '<div class="hotspot-pulse" style="width:40px;height:40px;position:relative"><div class="ring"></div><div class="ring"></div><div class="hotspot-dot" style="position:absolute;top:15px;left:15px"></div></div>',
            iconSize: [40,40], iconAnchor: [20,20]
        });
        L.marker([h.lat, h.lng], {icon}).bindPopup(`
            <div style="font-size:12px"><div style="font-family:Inter;font-size:16px;color:#8052ff">HOTSPOT #${i+1}</div>
            <div style="color:#aaa;margin-top:4px">${h.top_crime}: ${h.top_crime_count} cases</div>
            <div style="color:#888">Peak: ${h.peak_hour}:00 | Avg Sev: ${h.avg_severity}</div></div>
        `).addTo(state.hotspotLayer);
        L.circle([h.lat, h.lng], {
            radius: h.radius*10, fillColor:'#8052ff', fillOpacity:0.05,
            color:'#8052ff', weight:1, opacity:0.2
        }).addTo(state.hotspotLayer);
        const cls = h.avg_severity>=7?'risk-high':h.avg_severity>=5?'risk-medium':'risk-low';
        return `<div class="bg-[#0a0a0a] border border-[#1a1a1a] rounded p-2 hover:border-accent/30 cursor-pointer transition" onclick="MapModule.flyToHotspot(${h.lat},${h.lng})">
            <div class="flex items-center justify-between mb-1"><span class="font-display text-accent text-sm">#${i+1}</span><span class="text-[10px] px-1.5 py-0.5 rounded ${cls}">${h.avg_severity}/10</span></div>
            <p class="text-white text-xs font-semibold">${h.top_crime}</p>
            <p class="text-[10px] text-silver mt-0.5">${h.count} incidents — Peak: ${h.peak_hour}:00</p></div>`;
    }).join('');
}

function renderRedZones(alerts, distCoords) {
    state.redzoneLayer.clearLayers();
    if (!alerts || !distCoords) return;
    alerts.forEach(a => {
        const dc = distCoords.find(d => d.n === a.district);
        if (!dc) return;
        const icon = L.divIcon({
            className: '',
            html: '<div class="redzone-pulse" style="width:50px;height:50px;position:relative"><div class="ring"></div><div class="ring"></div><div class="ring"></div><div class="redzone-dot" style="position:absolute;top:19px;left:19px"></div></div>',
            iconSize: [50,50], iconAnchor: [25,25]
        });
        L.marker([dc.lat, dc.lng], {icon}).bindPopup(`
            <div style="font-size:12px"><div style="font-family:Inter;font-size:16px;color:#FF2D2D;letter-spacing:1px">TREND ALERT</div>
            <div style="color:#ff6666;margin-top:4px">${a.crime_type} in ${a.district}</div>
            <div style="color:#aaa">+${a.increase_pct}% increase</div>
            <div style="color:#888">${a.recent} recent vs ${a.previous} prior</div></div>
        `).addTo(state.redzoneLayer);
    });
}

const MapModule = {
    flyToHotspot(lat, lng) {
        if (state.map) state.map.flyTo([lat, lng], 11, {duration: 1});
    },

    async loadBoundaries() {
        const loader = $('#boundaryLoader');
        if (loader) loader.style.display = 'flex';
        const data = await api('/geo/boundaries');
        if (loader) loader.style.display = 'none';
        if (!data || !data.features || !data.features.length) {
            toast('Overpass: Boundaries unavailable (retry on SYNC)', 'error');
            return;
        }
        const counts = Object.values(state.districtCrimeMap).map(d=>d.count);
        const maxC = Math.max(...counts, 1);
        function getColor(name) {
            const info = state.districtCrimeMap[name];
            if (!info) return {fill:'rgba(100,100,100,0.15)',border:'#444'};
            const r = info.count/maxC;
            if(r>0.6) return {fill:'rgba(255,45,45,0.35)',border:'#FF2D2D'};
            if(r>0.35) return {fill:'rgba(128,82,255,0.3)',border:'#8052ff'};
            if(r>0.15) return {fill:'rgba(255,214,0,0.2)',border:'#ffb829'};
            return {fill:'rgba(0,230,118,0.15)',border:'#15846e'};
        }
        if (state.boundaryLayer) state.map.removeLayer(state.boundaryLayer);
        state.boundaryLayer = L.geoJSON(data, {
            style: f => {const c=getColor(f.properties.name_normalized||f.properties.name); return {fillColor:c.fill,color:c.border,weight:1.5,opacity:0.8,fillOpacity:0.5};},
            onEachFeature: (f, layer) => {
                const name=f.properties.name, norm=f.properties.name_normalized||name;
                const info=state.districtCrimeMap[norm]||{count:0,avg_sev:0};
                layer.bindPopup(`<div style="font-size:12px;min-width:200px"><div style="font-family:Inter;font-size:18px;color:#8052ff;letter-spacing:1px">${name}</div><div style="margin-top:6px;display:grid;grid-template-columns:1fr 1fr;gap:4px"><div style="background:#1a1a1a;padding:4px 8px;border-radius:3px"><div style="font-size:9px;color:#666;text-transform:uppercase">Incidents</div><div style="font-family:Inter;font-size:20px;color:#fff">${info.count}</div></div><div style="background:#1a1a1a;padding:4px 8px;border-radius:3px"><div style="font-size:9px;color:#666;text-transform:uppercase">Avg Severity</div><div style="font-family:Inter;font-size:20px;color:${info.avg_sev>=7?'#FF2D2D':info.avg_sev>=5?'#8052ff':'#15846e'}">${info.avg_sev}</div></div></div><div style="margin-top:6px;font-size:9px;color:#444">Source: OpenStreetMap Overpass API</div></div>`);
                layer.on('mouseover', function(){this.setStyle({weight:3,fillOpacity:0.7})});
                layer.on('mouseout', function(){state.boundaryLayer.resetStyle(this)});
                // Click to drill down if in advanced mode
                if (state.advancedMode) {
                    layer.on('click', function(){ AdvViz.drillIntoDistrict(norm); });
                }
            }
        }).addTo(state.map);
        const legend = $('#districtLegend');
        if (legend) legend.classList.remove('hidden');
        toast('Overpass: '+data.features.length+' real district boundaries loaded','success');
    },

    async loadStations() {
        const data = await api('/geo/stations');
        if (!data || !data.length) return;
        if (state.stationLayer) state.map.removeLayer(state.stationLayer);
        state.stationLayer = L.layerGroup();
        const icon = L.divIcon({className:'',html:'<div class="station-marker-icon"></div>',iconSize:[10,10],iconAnchor:[5,5]});
        data.forEach(s => {
            L.marker([s.lat, s.lng], {icon}).bindPopup(`<div style="font-size:11px"><div style="font-family:Inter;font-size:14px;color:#4488ff"><i class="fa-solid fa-shield-halved" style="margin-right:4px"></i>POLICE STATION</div><div style="color:#ddd;margin-top:4px">${s.name}</div>${s.addr?'<div style="color:#666;font-size:10px">'+s.addr+'</div>':''}<div style="color:#444;font-size:9px;margin-top:4px">Source: OpenStreetMap</div></div>`).addTo(state.stationLayer);
        });
        state.stationLayer.addTo(state.map);
        toast('Overpass: '+data.length+' police station POIs loaded','success');
    }
};


// ═══════════════════════════════════════════════════════════════════
// SECTION 5: CHART MODULE
// ═══════════════════════════════════════════════════════════════════

Chart.defaults.color='#8B93A3'; Chart.defaults.borderColor='#242B38';
Chart.defaults.font.family="'IBM Plex Sans', sans-serif"; Chart.defaults.font.size=11;
Chart.defaults.plugins.legend.labels.boxWidth=10; Chart.defaults.plugins.legend.labels.padding=8;

function renderStats(d) {
    if (!d) return;
    state.districtCrimeMap = {};
    (d.district_crime||[]).forEach(x=>{state.districtCrimeMap[x.district]={count:x.count,avg_sev:x.avg_sev};});
    const vals = [d.total_incidents,d.pending_investigation,d.chargesheeted,d.districts_active,d.stations_active,d.high_risk_districts];
    $$('.stat-num[data-count]').forEach((el,i)=>animateCount(el, vals[i]||0));

    if(state.charts.trend) state.charts.trend.destroy();
    state.charts.trend = new Chart($('#chartTrend'),{type:'line',data:{labels:d.monthly_trend.map(m=>m.month),datasets:[{label:'Incidents',data:d.monthly_trend.map(m=>m.count),borderColor:'#4C8DFF',backgroundColor:'rgba(76,141,255,0.12)',fill:true,tension:0.35,pointRadius:2,pointBackgroundColor:'#4C8DFF',borderWidth:2}]},options:{responsive:true,plugins:{legend:{display:true,labels:{boxWidth:10}},tooltip:{mode:'index',intersect:false}},scales:{x:{title:{display:true,text:'Month'},ticks:{maxRotation:45,font:{size:9}},grid:{color:'rgba(36,43,56,0.55)'}},y:{title:{display:true,text:'Incidents'},beginAtZero:true,grid:{color:'rgba(36,43,56,0.75)'}}}}});

    const top8=(d.by_crime_type||[]).slice(0,8);
    if(state.charts.types) state.charts.types.destroy();
    state.charts.types = new Chart($('#chartTypes'),{type:'bar',data:{labels:top8.map(t=>t.type),datasets:[{label:'Incidents',data:top8.map(t=>t.count),backgroundColor:top8.map(t=>CRIME_COLORS[t.type]||'#4C8DFF'),borderRadius:3,borderSkipped:false}]},options:{indexAxis:'y',responsive:true,plugins:{legend:{display:false}},scales:{x:{title:{display:true,text:'Incidents'},beginAtZero:true,grid:{color:'rgba(36,43,56,0.75)'}},y:{grid:{display:false},ticks:{font:{size:10}}}}}});

    const hData=(d.hourly_distribution||[]).map(h=>h.count), hMax=Math.max(...hData,1);
    if(state.charts.hourly) state.charts.hourly.destroy();
    state.charts.hourly = new Chart($('#chartHourly'),{type:'bar',data:{labels:(d.hourly_distribution||[]).map(h=>h.hour+':00'),datasets:[{label:'Incidents',data:hData,backgroundColor:hData.map(v=>v>=hMax*0.8?'#FF5D5D':v>=hMax*0.5?'#FFB84D':'rgba(76,141,255,0.38)'),borderRadius:2,borderSkipped:false}]},options:{responsive:true,plugins:{legend:{display:false}},scales:{x:{title:{display:true,text:'Hour'},ticks:{font:{size:8},maxRotation:0},grid:{display:false}},y:{title:{display:true,text:'Incidents'},beginAtZero:true,grid:{color:'rgba(36,43,56,0.75)'}}}}});

    const sevOrder=['Low','Medium','High','Critical'], sevColors=['#3DDC97','#FFB84D','#D94F3D','#FF5D5D'];
    if(state.charts.severity) state.charts.severity.destroy();
    state.charts.severity = new Chart($('#chartSeverity'),{type:'bar',data:{labels:sevOrder,datasets:[{label:'Incidents',data:sevOrder.map(l=>(d.severity_distribution.find(s=>s.level===l)||{}).count||0),backgroundColor:sevColors,borderRadius:3,borderSkipped:false}]},options:{indexAxis:'y',responsive:true,plugins:{legend:{display:false}},scales:{x:{title:{display:true,text:'Incidents'},beginAtZero:true,grid:{color:'rgba(255,255,255,0.06)'}},y:{grid:{display:false}}}}});
}

function renderSocio(data) {
    if (!data) return;
    if(state.charts.socio) state.charts.socio.destroy();
    state.charts.socio = new Chart($('#chartSocio'),{type:'bubble',data:{datasets:[{label:'Districts',data:data.map(s=>({x:s.urbanization_rate*100,y:s.crime_count,r:Math.max(3,Math.sqrt(s.population_density)/3)})),backgroundColor:data.map(s=>s.poverty_index>0.3?'rgba(255,45,45,0.5)':s.poverty_index>0.2?'rgba(128,82,255,0.5)':s.poverty_index>0.1?'rgba(255,214,0,0.4)':'rgba(0,230,118,0.3)'),borderColor:data.map(s=>s.poverty_index>0.3?'#FF2D2D':s.poverty_index>0.2?'#8052ff':s.poverty_index>0.1?'#ffb829':'#15846e'),borderWidth:1}]},options:{responsive:true,plugins:{legend:{display:true,labels:{boxWidth:10}},tooltip:{callbacks:{label:ctx=>{const s=data[ctx.dataIndex];return s.district+': '+s.crime_count+' crimes, '+Math.round(s.urbanization_rate*100)+'% urban';}}}},scales:{x:{title:{display:true,text:'Urbanization %',color:'#8B93A3',font:{size:10}},grid:{color:'rgba(255,255,255,0.06)'}},y:{title:{display:true,text:'Crime Count',color:'#8B93A3',font:{size:10}},grid:{color:'rgba(255,255,255,0.06)'},beginAtZero:true}}}});
}

function applyRangeFilter(data) {
    if (!state.selectedRangeDays || !data || !data.length) return data || [];
    const dates = data.map(i=>new Date(i.date)).filter(d=>!Number.isNaN(d.getTime()));
    if (!dates.length) return data;
    const maxDate = new Date(Math.max(...dates.map(d=>d.getTime())));
    const start = new Date(maxDate);
    start.setDate(start.getDate() - state.selectedRangeDays + 1);
    return data.filter(i => {
        const d = new Date(i.date);
        return !Number.isNaN(d.getTime()) && d >= start && d <= maxDate;
    });
}


// ═══════════════════════════════════════════════════════════════════
// SECTION 6: NETWORK MODULE
// ═══════════════════════════════════════════════════════════════════

function renderNetwork(d) {
    if (!d || !d.nodes) return;
    const cm = {Suspect:'#8052ff',Victim:'#A0A0A0',Witness:'#555555'};
    const nodes = new vis.DataSet(d.nodes.map(n=>({...n, color:{background:cm[n.group]||'#555',border:cm[n.group]||'#555',highlight:{background:'#fff',border:'#8052ff'}}, font:{color:'#ccc',size:10,face:'Inter'}, shape:'dot', borderWidth:1})));
    const edges = new vis.DataSet(d.edges.map(e=>({...e, color:{color:e.dashes?'#333':'rgba(128,82,255,0.4)'}, width:Math.max(0.5,(e.value||1)/5), dashes:e.dashes?[5,5]:false, font:{color:'#555',size:8,face:'Inter',strokeWidth:0}, smooth:{type:'continuous'}})));
    if (state.network) state.network.destroy();
    state.network = new vis.Network($('#networkGraph'),{nodes,edges},{physics:{stabilization:{iterations:150},barnesHut:{gravitationalConstant:-3000,springLength:80,springConstant:0.04}},interaction:{hover:true,tooltipDelay:100},nodes:{scaling:{min:4,max:30}}});
}


// ═══════════════════════════════════════════════════════════════════
// SECTION 7: DATA LOADERS
// ═══════════════════════════════════════════════════════════════════

async function loadMapData() {
    const district = $('#filterDistrict').value;
    const crime = $('#filterCrime').value;
    let url = '/incidents/map?limit=2000';
    if (district) url += '&district='+encodeURIComponent(district);
    if (crime) url += '&crime_type='+encodeURIComponent(crime);

    let data = await api(url);
    if (!data) data = FALLBACK.incidents;
    if (district) data = data.filter(i=>i.district===district);
    if (crime) data = data.filter(i=>i.crime_type===crime);
    data = applyRangeFilter(data);
    state.allIncidents = data;

    // Apply time filter if active
    if (state.selectedHour >= 0) {
        data = data.filter(d => d.hour === state.selectedHour);
    }
    renderIncidents(data);

    let hotspots = await api('/hotspots');
    if (!hotspots) hotspots = FALLBACK.hotspots;
    state.allHotspots = hotspots;
    renderHotspots(hotspots);
}

async function loadPredictions() {
    let d = await api('/predictions');
    if (!d) d = FALLBACK.predictions;
    if (!d || !d.length) { showEmpty($('#predTable'), 'No prediction data available'); return; }
    $('#predTable').innerHTML = d.slice(0,15).map(p=>{
        const ti=p.trend==='increasing'?'fa-arrow-trend-up text-danger':p.trend==='decreasing'?'fa-arrow-trend-down text-success':'fa-minus text-silver';
        const rc=p.risk_level==='high'?'risk-high':p.risk_level==='medium'?'risk-medium':'risk-low';
        const cc=p.risk_change>0?'text-danger':p.risk_change<0?'text-success':'text-silver';
        return `<tr><td class="font-semibold text-white">${p.district}</td><td><i class="fa-solid ${ti} mr-1"></i><span class="capitalize">${p.trend}</span></td><td class="text-white">${p.p1}</td><td><span class="text-[10px] px-1.5 py-0.5 rounded ${rc}">${p.risk_level.toUpperCase()}</span></td><td class="${cc} font-semibold">${p.risk_change>0?'+':''}${p.risk_change}%</td></tr>`;
    }).join('');
}

async function loadAnomalies() {
    let d = await api('/anomalies');
    if (!d) d = FALLBACK.anomalies;
    if (!d || !d.length) { showEmpty($('#anomalyList'), 'No anomalies detected'); return; }
    $('#anomalyList').innerHTML = d.slice(0,15).map(a=>`<div class="bg-[#0a0a0a] border border-[#220000] rounded p-2 hover:border-danger/30 transition"><div class="flex items-center justify-between mb-1"><span class="text-[10px] font-display text-danger tracking-wider">ANOMALY #${a.id}</span><span class="text-[10px] text-silver">${a.date}</span></div><p class="text-white text-xs font-semibold">${a.crime_type} — ${a.district}</p><p class="text-[10px] text-[#888] mt-0.5">${a.station} | ${a.time} | Sev: ${a.severity}/10</p><p class="text-[10px] text-[#ff6666] mt-1 italic">${a.reason}</p></div>`).join('');
}

async function loadAlerts() {
    let d = await api('/trend-alerts');
    if (!d) d = FALLBACK.alerts;
    if (!d || !d.length) {
        state.trendAlerts = [];
        $('#alertTicker').innerHTML = '<span>No active trend alerts</span>';
        const badge = document.querySelector('.alert-button span');
        if (badge) badge.textContent = '0';
        return;
    }
    state.trendAlerts = d;
    const badge = document.querySelector('.alert-button span');
    if (badge) badge.textContent = d.length;
    const msgs = d.map(a=>`<span class="${a.severity==='critical'?'text-danger':a.severity==='high'?'text-[#ff9944]':'text-warning'} mx-6"><i class="fa-solid fa-triangle-exclamation mr-1"></i>${a.crime_type} spike in ${a.district}: +${a.increase_pct}% (${a.recent} vs ${a.previous})</span>`);
    $('#alertTicker').innerHTML = msgs.join('')+msgs.join('');

    // Show red zones on map if in advanced mode
    if (state.advancedMode) {
        const distCoords = [
            {n:"Bangalore Urban",lat:12.97,lng:77.59},{n:"Mysore",lat:12.30,lng:76.64},
            {n:"Hubli-Dharwad",lat:15.36,lng:75.12},{n:"Mangalore",lat:12.91,lng:74.86},
            {n:"Belgaum",lat:15.85,lng:74.50},{n:"Gulbarga",lat:17.33,lng:76.83},
            {n:"Davangere",lat:14.46,lng:75.93},{n:"Bellary",lat:15.14,lng:76.92},
            {n:"Shimoga",lat:13.93,lng:75.57},{n:"Tumkur",lat:13.34,lng:77.10},
            {n:"Raichur",lat:16.21,lng:77.35},{n:"Hassan",lat:13.01,lng:76.10},
            {n:"Udupi",lat:13.34,lng:74.74},{n:"Chitradurga",lat:14.23,lng:76.39},
            {n:"Mandya",lat:12.52,lng:76.90},{n:"Bidar",lat:17.91,lng:77.52},
            {n:"Koppal",lat:15.35,lng:76.15},{n:"Gadag",lat:15.42,lng:75.63},
            {n:"Haveri",lat:14.79,lng:75.40},{n:"Bagalkot",lat:16.19,lng:75.69},
            {n:"Chamarajanagar",lat:11.92,lng:76.94},{n:"Kodagu",lat:12.34,lng:75.81},
            {n:"Ramanagara",lat:12.72,lng:77.28},{n:"Yadgir",lat:16.77,lng:77.13},
            {n:"Bangalore Rural",lat:13.0,lng:77.5},{n:"Dakshina Kannada",lat:12.85,lng:75.0},
            {n:"Uttara Kannada",lat:14.55,lng:74.50}
        ];
        renderRedZones(d, distCoords);
    }
}

async function loadOffenders() {
    let d = await api('/repeat-offenders?limit=12');
    if (!d) d = FALLBACK.offenders;
    if (!d || !d.length) { showEmpty($('#offenderCards'), 'No repeat offenders found'); return; }
    $('#offenderCards').innerHTML = d.map(o=>`<div class="bg-[#0a0a0a] border border-[#1a1a1a] rounded p-3 min-w-[260px] max-w-[280px] shrink-0 hover:border-accent/30 transition"><div class="flex items-center gap-2.5 mb-2"><div class="w-9 h-9 rounded-full bg-accent-dim flex items-center justify-center text-accent font-display text-sm">${o.name.charAt(0)}</div><div><p class="text-white text-sm font-semibold leading-tight">${o.name}</p><p class="text-[10px] text-silver">${o.alias?'"'+o.alias+'"':o.location} | ${o.age}y</p></div></div><div class="flex items-center gap-1.5 mb-2"><span class="bg-danger/20 text-danger text-[10px] px-1.5 py-0.5 rounded font-semibold">${o.incident_count} CASES</span><span class="text-[10px] text-silver">${o.districts.length} jurisd.</span></div><p class="text-[10px] text-[#666] uppercase tracking-wider">Crimes</p><div class="flex flex-wrap gap-1 mt-0.5">${o.crime_types.slice(0,4).map(c=>'<span class="text-[10px] px-1.5 py-0.5 rounded border border-[#222] text-silver">'+c+'</span>').join('')}</div><p class="text-[10px] text-[#666] uppercase tracking-wider mt-1.5">Modus Operandi</p><p class="text-[10px] text-[#999] leading-snug mt-0.5">${o.methods.slice(0,2).join(' | ')}</p></div>`).join('');
}

async function loadWeather() {
    const data = await api('/geo/weather-cities');
    if (!data || !data.length) return;
    const bar = $('#weatherBar');
    bar.querySelectorAll('.weather-chip').forEach(chip=>chip.remove());
    data.forEach(w=>{
        const chip = document.createElement('div');
        chip.className = 'weather-chip';
        const ic = w.weathercode<=1?'#ffb829':w.weathercode<=3?'#aaa':w.weathercode<=65?'#4488ff':'#FF2D2D';
        chip.innerHTML = `<i class="fa-solid ${w.icon}" style="color:${ic}"></i><span class="text-white font-semibold">${w.city}</span><span class="text-silver">${w.temperature}°C</span>`;
        bar.appendChild(chip);
    });
}

async function loadFilters() {
    const [dists, types] = await Promise.all([api('/districts'), api('/crime-types')]);
    const dList = dists || FALLBACK.districts || [];
    const tList = types || FALLBACK.stats.by_crime_type.map(t=>t.type) || [];
    const dSel = $('#filterDistrict'), tSel = $('#filterCrime');
    dSel.querySelectorAll('option:not(:first-child)').forEach(o=>o.remove());
    tSel.querySelectorAll('option:not(:first-child)').forEach(o=>o.remove());
    dList.forEach(d=>{const o=document.createElement('option');o.value=d;o.textContent=d;dSel.appendChild(o)});
    tList.forEach(t=>{const o=document.createElement('option');o.value=t;o.textContent=t;tSel.appendChild(o)});
}


// ═══════════════════════════════════════════════════════════════════
// SECTION 8: ADVANCED VISUALIZATION
// ═══════════════════════════════════════════════════════════════════

const AdvViz = {
    toggle() {
        state.advancedMode = !state.advancedMode;
        const panel = $('#advPanel');
        const slider = $('#timeSlider');
        if (state.advancedMode) {
            panel.classList.add('open');
            slider.classList.add('visible');
            this.populateDistrictList();
            // Re-show red zones
            if (state.trendAlerts.length) {
                const distCoords = [
                    {n:"Bangalore Urban",lat:12.97,lng:77.59},{n:"Mysore",lat:12.30,lng:76.64},
                    {n:"Hubli-Dharwad",lat:15.36,lng:75.12},{n:"Mangalore",lat:12.91,lng:74.86},
                    {n:"Belgaum",lat:15.85,lng:74.50},{n:"Gulbarga",lat:17.33,lng:76.83},
                    {n:"Davangere",lat:14.46,lng:75.93},{n:"Bellary",lat:15.14,lng:76.92},
                    {n:"Shimoga",lat:13.93,lng:75.57},{n:"Tumkur",lat:13.34,lng:77.10},
                    {n:"Raichur",lat:16.21,lng:77.35},{n:"Hassan",lat:13.01,lng:76.10},
                    {n:"Udupi",lat:13.34,lng:74.74},{n:"Chitradurga",lat:14.23,lng:76.39},
                    {n:"Mandya",lat:12.52,lng:76.90},{n:"Bidar",lat:17.91,lng:77.52},
                    {n:"Koppal",lat:15.35,lng:76.15},{n:"Gadag",lat:15.42,lng:75.63},
                    {n:"Haveri",lat:14.79,lng:75.40},{n:"Bagalkot",lat:16.19,lng:75.69},
                    {n:"Chamarajanagar",lat:11.92,lng:76.94},{n:"Kodagu",lat:12.34,lng:75.81},
                    {n:"Ramanagara",lat:12.72,lng:77.28},{n:"Yadgir",lat:16.77,lng:77.13},
                    {n:"Bangalore Rural",lat:13.0,lng:77.5},{n:"Dakshina Kannada",lat:12.85,lng:75.0},
                    {n:"Uttara Kannada",lat:14.55,lng:74.50}
                ];
                renderRedZones(state.trendAlerts, distCoords);
            }
            toast('Advanced Visualization enabled','success');
        } else {
            panel.classList.remove('open');
            slider.classList.remove('visible');
            state.redzoneLayer.clearLayers();
            this.resetDrillDown();
            // Reset time filter
            state.selectedHour = -1;
            $('#hourSlider').value = -1;
            $('#hourLabel').textContent = 'All Hours';
            $$('.time-slider-bar .btn-sm').forEach(b=>b.classList.remove('active'));
            renderIncidents(state.allIncidents);
            toast('Advanced Visualization disabled','info');
        }
        // Invalidate map size after panel animation
        setTimeout(()=>{ if(state.map) state.map.invalidateSize(); }, 400);
    },

    populateDistrictList() {
        const list = $('#drillDistrictList');
        if (!list) return;
        const counts = {};
        state.allIncidents.forEach(i=>{counts[i.district]=(counts[i.district]||0)+1;});
        const sorted = Object.entries(counts).sort((a,b)=>b[1]-a[1]);
        list.innerHTML = sorted.map(([name,count])=>`
            <div class="drill-district-item" onclick="AdvViz.drillIntoDistrict('${name.replace(/'/g,"\\'")}')">
                <span class="text-silver">${name}</span>
                <span class="count">${count}</span>
            </div>
        `).join('');
    },

    async drillIntoDistrict(districtName) {
        state.drilledDistrict = districtName;
        // Fetch drill-down data
        let dd = await api('/incidents/district/'+encodeURIComponent(districtName));
        if (!dd) dd = FALLBACK.drillDown[districtName];
        if (!dd) { toast('No drill-down data for '+districtName,'error'); return; }

        // Hide district list, show drill view
        $('#drillDistrictList').style.display = 'none';
        $('#drillState').style.display = 'block';
        $('#drillDistrictName').textContent = districtName.toUpperCase();

        // Stats
        $('#drillStats').innerHTML = `
            <div class="drill-stat-grid">
                <div class="drill-stat-box"><div class="label">Incidents</div><div class="value">${dd.total}</div></div>
                <div class="drill-stat-box"><div class="label">Avg Severity</div><div class="value" style="color:${dd.avg_sev>=7?'#FF2D2D':dd.avg_sev>=5?'#8052ff':'#15846e'}">${dd.avg_sev}</div></div>
            </div>`;

        // Station list
        const maxS = Math.max(...dd.stations.map(s=>s.count), 1);
        $('#drillStations').innerHTML = dd.stations.slice(0,8).map(s=>`
            <div class="drill-list-item">
                <span class="name">${s.station}</span>
                <span class="val">${s.count}</span>
            </div>
            <div class="drill-bar"><div class="drill-bar-fill" style="width:${(s.count/maxS*100).toFixed(0)}%"></div></div>
        `).join('');

        // Crime type mini chart
        if (state.charts.drillCrime) state.charts.drillCrime.destroy();
        const topTypes = dd.types.slice(0,6);
        state.charts.drillCrime = new Chart($('#drillCrimeChart'),{
            type:'bar',
            data:{labels:topTypes.map(t=>t.type), datasets:[{data:topTypes.map(t=>t.count), backgroundColor:topTypes.map(t=>CRIME_COLORS[t.type]||'#666'), borderRadius:2, borderSkipped:false}]},
            options:{indexAxis:'y', responsive:true, plugins:{legend:{display:false}}, scales:{x:{beginAtZero:true,grid:{color:'rgba(255,255,255,0.06)'},ticks:{font:{size:9}}},y:{grid:{display:false},ticks:{font:{size:9}}}}}
        });

        // Hourly mini chart
        if (state.charts.drillTime) state.charts.drillTime.destroy();
        state.charts.drillTime = new Chart($('#drillTimeChart'),{
            type:'bar',
            data:{labels:dd.hours.map(h=>h.hour+':00'), datasets:[{data:dd.hours.map(h=>h.count), backgroundColor:dd.hours.map(h=>h.count>=maxS*0.7?'#8052ff':h.count>=maxS*0.4?'rgba(128,82,255,0.5)':'rgba(128,82,255,0.2)'), borderRadius:1, borderSkipped:false}]},
            options:{responsive:true, plugins:{legend:{display:false}}, scales:{x:{ticks:{font:{size:7},maxRotation:0}},y:{beginAtZero:true,grid:{color:'rgba(255,255,255,0.06)'},ticks:{font:{size:8}}}}}
        });

        // Map: zoom to district and show station markers
        const districtInc = state.allIncidents.filter(i=>i.district===districtName);
        if (districtInc.length) {
            const lat = districtInc.reduce((a,i)=>a+i.latitude,0)/districtInc.length;
            const lng = districtInc.reduce((a,i)=>a+i.longitude,0)/districtInc.length;
            state.map.flyTo([lat, lng], 11, {duration: 1.2});

            // Hide state-level, show district-level
            state.incidentLayer.clearLayers();
            state.hotspotLayer.clearLayers();

            // Show district incidents
            let filtered = districtInc;
            if (state.selectedHour >= 0) filtered = filtered.filter(i=>i.hour===state.selectedHour);
            renderIncidents(filtered);

            // Show station markers
            state.drilldownLayer.clearLayers();
            dd.stations.forEach(s => {
                const sInc = districtInc.filter(i=>i.station===s.station);
                let sLat, sLng;
                if (sInc.length) {
                    sLat = sInc.reduce((a,i)=>a+i.latitude,0)/sInc.length;
                    sLng = sInc.reduce((a,i)=>a+i.longitude,0)/sInc.length;
                } else {
                    sLat = lat + (Math.random()-0.5)*0.1;
                    sLng = lng + (Math.random()-0.5)*0.1;
                }
                const icon = L.divIcon({className:'',html:'<div class="station-marker-icon"></div>',iconSize:[10,10],iconAnchor:[5,5]});
                L.marker([sLat, sLng], {icon}).bindPopup(`
                    <div style="font-size:11px"><div style="font-family:Inter;font-size:14px;color:#4aa8ff">${s.station}</div>
                    <div style="color:#ddd;margin-top:4px">${s.count} incidents</div>
                    <div style="color:#888">Avg Severity: ${s.avg_sev}</div></div>
                `).addTo(state.drilldownLayer);
            });
            state.drilldownLayer.addTo(state.map);

            // Draw a circle to indicate district area
            L.circle([lat, lng], {
                radius: 15000, fillColor:'#8052ff', fillOpacity:0.03,
                color:'#8052ff', weight:1, opacity:0.15, dashArray:'5,5'
            }).addTo(state.drilldownLayer);
        }

        setTimeout(()=>{ if(state.map) state.map.invalidateSize(); }, 500);
        toast('Drilled into: '+districtName,'info');
    },

    resetDrillDown() {
        state.drilledDistrict = null;
        state.drilldownLayer.clearLayers();
        state.map.removeLayer(state.drilldownLayer);
        $('#drillDistrictList').style.display = 'block';
        $('#drillState').style.display = 'none';
        // Restore state view
        state.map.flyTo([14.5, 76.5], 7, {duration: 1});
        // Re-render all incidents
        let data = state.allIncidents;
        if (state.selectedHour >= 0) data = data.filter(d=>d.hour===state.selectedHour);
        renderIncidents(data);
        renderHotspots(state.allHotspots);
    },

    setTimeFilter(hour) {
        state.selectedHour = hour;
        const label = $('#hourLabel');
        label.textContent = hour >= 0 ? hour+':00 — '+(hour+1)+':00' : 'All Hours';

        // Filter incidents on map
        let data = state.allIncidents;
        if (hour >= 0) data = data.filter(d=>d.hour===hour);

        if (state.drilledDistrict) {
            data = data.filter(d=>d.district===state.drilledDistrict);
        }
        renderIncidents(data);

        // Update active button states
        $$('.time-slider-bar .btn-sm').forEach(b=>b.classList.remove('active'));
        if (hour >= 0) {
            const btn = $(`[data-hour="${hour}"]`);
            if (btn) btn.classList.add('active');
        }
    }
};


// ═══════════════════════════════════════════════════════════════════
// SECTION 9: UI INTERACTIONS
// ═══════════════════════════════════════════════════════════════════

function setupUI() {
    // Sidebar navigation
    $$('.sidebar-btn[data-section]').forEach(btn=>{
        btn.addEventListener('click', ()=>{
            $$('.sidebar-btn').forEach(b=>{b.classList.remove('active');b.classList.add('text-silver')});
            btn.classList.add('active'); btn.classList.remove('text-silver');
            const sec = $('#sec-'+btn.dataset.section);
            if (sec) sec.scrollIntoView({behavior:'smooth', block:'start'});
        });
    });

    // Hamburger menu
    const hamburger = $('#hamburger');
    const dropdown = $('#hamburgerDropdown');
    if (hamburger && dropdown) {
        hamburger.addEventListener('click', (e)=>{
            e.stopPropagation();
            hamburger.classList.toggle('active');
            dropdown.classList.toggle('open');
        });
        document.addEventListener('click', ()=>{
            hamburger.classList.remove('active');
            dropdown.classList.remove('open');
        });
    }

    // Advanced viz button in hamburger
    const advBtn = $('#btnAdvViz');
    if (advBtn) advBtn.addEventListener('click', ()=>{
        if (dropdown) dropdown.classList.remove('open');
        if (hamburger) hamburger.classList.remove('active');
        AdvViz.toggle();
    });

    const resetTime = $('#btnResetTime');
    if (resetTime) resetTime.addEventListener('click', ()=>{
        if (dropdown) dropdown.classList.remove('open');
        if (hamburger) hamburger.classList.remove('active');
        const slider = $('#hourSlider');
        if (slider) slider.value = -1;
        AdvViz.setTimeFilter(-1);
        toast('Time filter reset', 'info');
    });

    // Close adv panel
    const closeAdv = $('#closeAdvPanel');
    if (closeAdv) closeAdv.addEventListener('click', ()=> AdvViz.toggle());

    // Back from drill-down
    const backDrill = $('#btnResetDrill');
    if (backDrill) backDrill.addEventListener('click', ()=> AdvViz.resetDrillDown());

    // Filters (Null-safe to prevent script crash)
    const filterDistrict = $('#filterDistrict');
    if (filterDistrict) filterDistrict.addEventListener('change', loadMapData);
    
    const filterCrime = $('#filterCrime');
    if (filterCrime) filterCrime.addEventListener('change', loadMapData);

    // Refresh (Null-safe)
    const btnRefresh = $('#btnRefresh');
    if (btnRefresh) btnRefresh.addEventListener('click', ()=>{
        toast('Syncing all intelligence feeds...','info');
        loadAll();
    });

    const alertBtn = document.querySelector('.alert-button');
    if (alertBtn) alertBtn.addEventListener('click', ()=>{
        document.querySelector('#anomalyLens')?.scrollIntoView({behavior:'smooth', block:'start'});
        toast(state.trendAlerts.length ? `${state.trendAlerts.length} active trend alerts` : 'No active trend alerts', state.trendAlerts.length ? 'warning' : 'info');
    });

    $$('.quick-range button').forEach(btn=>{
        btn.addEventListener('click', ()=>{
            $$('.quick-range button').forEach(b=>b.classList.remove('active'));
            btn.classList.add('active');
            const label = btn.textContent.trim();
            state.selectedRangeDays = label === '24h' ? 1 : label === '30d' ? 30 : 7;
            toast(`Range set to ${btn.textContent.trim()}`, 'info');
            loadMapData();
        });
    });

    $$('.layer-toggle input').forEach((input, idx)=>{
        input.addEventListener('change', ()=>{
            const layer = [state.hotspotLayer, state.stationLayer, null, state.redzoneLayer][idx];
            if (layer && state.map) {
                input.checked ? layer.addTo(state.map) : state.map.removeLayer(layer);
            }
            toast(`${input.closest('label').innerText.trim()} ${input.checked ? 'shown' : 'hidden'}`, 'info');
        });
    });

    // Time slider
    const slider = $('#hourSlider');
    if (slider) {
        slider.addEventListener('input', (e)=>{
            const h = parseInt(e.target.value);
            AdvViz.setTimeFilter(h >= 0 ? h : -1);
        });
    }

    // Time quick-select buttons
    $$('.time-preset').forEach(btn=>{
        btn.addEventListener('click', ()=>{
            const h = parseInt(btn.dataset.hour);
            if (slider) slider.value = h;
            AdvViz.setTimeFilter(h);
        });
    });

    // Nominatim search (Null-safe to prevent script crash)
    let searchTimeout;
    const searchInput = $('#searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const q = this.value.trim();
            const box = $('#searchResults');
            if (!box) return;
            if (q.length < 3) { box.classList.add('hidden'); return; }
            searchTimeout = setTimeout(async ()=>{
                const results = await api('/geo/search?q='+encodeURIComponent(q));
                if (!results || !results.length) { box.classList.add('hidden'); return; }
                box.innerHTML = results.map(r=>`<div onclick="flyToSearch(${r.lat},${r.lng},'${r.name.replace(/'/g,"\\'")}')">${r.name} <span style="color:#444">— ${r.type}</span></div>`).join('');
                box.classList.remove('hidden');
            }, 400);
        });
        searchInput.addEventListener('blur', ()=>{ 
            setTimeout(()=>{ const box = $('#searchResults'); if(box) box.classList.add('hidden'); }, 200); 
        });
    }

    if (hamburger) hamburger.addEventListener('keydown', (e)=>{
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            hamburger.click();
        }
    });
}

function flyToSearch(lat, lng, name) {
    if (!state.map) return;
    state.map.flyTo([lat, lng], 14, {duration:1.5});
    $('#searchResults').classList.add('hidden');
    $('#searchInput').value = name;
    const m = L.circleMarker([lat,lng],{radius:8,fillColor:'#fff',fillOpacity:0.8,color:'#8052ff',weight:2}).addTo(state.map);
    m.bindPopup('<div style="font-size:11px"><b>'+name+'</b><br><span style="color:#666">Nominatim geocoded</span></div>').openPopup();
    setTimeout(()=>state.map.removeLayer(m), 15000);
}


// ═══════════════════════════════════════════════════════════════════
// SECTION 10: INITIALIZATION — THE CRITICAL FIX
// ═══════════════════════════════════════════════════════════════════

async function loadAll() {
    // 1. Stats & charts (needed first for districtCrimeMap)
    let stats = await api('/dashboard/stats');
    if (!stats) { stats = FALLBACK.stats; state.usingFallback = true; }
    renderStats(stats);

    // 2. Load filters
    await loadFilters();

    // 3. Parallel load everything else
    await Promise.all([
        loadMapData(),
        MapModule.loadBoundaries(),
        MapModule.loadStations(),
        renderNetwork(await api('/network?limit=70') || FALLBACK.network),
        loadPredictions(),
        loadAnomalies(),
        loadAlerts(),
        loadOffenders(),
        loadWeather(),
        renderSocio(await api('/socio-economic') || FALLBACK.socio)
    ]);

    // Show fallback badge if needed
    if (state.usingFallback) {
        const badge = $('#fallbackBadge');
        if (badge) badge.style.display = 'block';
        toast('Running in FALLBACK mode — backend unavailable','error');
    } else {
        toast('All intelligence feeds operational','success');
    }
}

document.addEventListener('DOMContentLoaded', ()=>{
    // Setup all UI event listeners FIRST
    setupUI();

    // Initialize map AFTER a frame to ensure DOM is laid out
    requestAnimationFrame(()=>{
        requestAnimationFrame(()=>{
            initMap();

            // ALWAYS call loadAll — whether backend is up or not
            // This is the critical fix: previously this was only called
            // inside the .then() of fetch('/health'), so fallback
            // data was never used when backend was down.
            loadAll();
        });
    });
});
/* ================================================================
   PS2 additions: theme toggle, suspect CRUD
   ================================================================ */
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  /* ---------- 1. Theme toggle (persisted in localStorage) ---------- */
  // FIX: Targeting class instead of ID to match your CSS
  const themeBtn = $(".theme-toggle-btn"); 
  const applyTheme = (t) => {
    document.body.classList.toggle("theme-light", t === "light");
    if (themeBtn) {
      themeBtn.innerHTML = t === "light"
        ? '<i class="fa-solid fa-sun"></i>'
        : '<i class="fa-solid fa-moon"></i>';
    }
  };
  applyTheme(localStorage.getItem("kspTheme") || "dark");
  themeBtn?.addEventListener("click", () => {
    const next = document.body.classList.contains("theme-light") ? "dark" : "light";
    localStorage.setItem("kspTheme", next);
    applyTheme(next);
  });

  /* ---------- 2. Suspect CRUD ---------- */
  const modal = $("#suspectModal");
  const openModal = () => { modal?.classList.remove("hidden"); loadSuspects(); };
  const closeModal = () => modal?.classList.add("hidden");
  $("#suspectFab")?.addEventListener("click", openModal);
  $("#suspectClose")?.addEventListener("click", closeModal);
  modal?.addEventListener("click", (e) => { if (e.target === modal) closeModal(); });

  async function loadSuspects(q = "") {
    const list = $("#suspectList");
    if (!list) return;
    list.innerHTML = '<small style="color:var(--text-muted)">Loading...</small>';
    try {
      const url = q ? `/api/persons?q=${encodeURIComponent(q)}&limit=50`
                    : `/api/persons?limit=50`;
      const res = await fetch(url);
      const data = await res.json();
      if (!Array.isArray(data) || data.length === 0) {
        list.innerHTML = '<small style="color:var(--text-muted)">No suspects found.</small>';
        return;
      }
      list.innerHTML = data.map(p => `
        <div class="suspect-item" data-id="${p.id}">
          <div class="info">
            <strong>
              <span class="role-badge ${p.role}">${p.role}</span>
              ${escapeHtml(p.name)} ${p.alias ? `<em style="color:var(--text-muted)">(${escapeHtml(p.alias)})</em>` : ""}
            </strong>
            <small>${p.age ? p.age + "y" : ""} ${p.gender || ""} • ${escapeHtml(p.last_known_location || "Unknown")} • ${p.incident_count} case(s)</small>
          </div>
          <button class="del-btn" data-del="${p.id}"><i class="fa-solid fa-trash"></i></button>
        </div>`).join("");
      $$('[data-del]', list).forEach(btn => btn.addEventListener("click", () => deleteSuspect(btn.dataset.del)));
    } catch (err) {
      console.error(err);
      list.innerHTML = '<small style="color:var(--text-muted)">Failed to load.</small>';
    }
  }

  async function deleteSuspect(id) {
    if (!confirm("Delete this suspect? This removes all their associations.")) return;
    try {
      const res = await fetch(`/api/persons/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error(await res.text());
      loadSuspects($("#sSearch")?.value.trim() || "");
    } catch (err) {
      alert("Delete failed: " + err.message);
    }
  }

  $("#sSave")?.addEventListener("click", async () => {
    const name = $("#sName").value.trim();
    if (name.length < 2) { alert("Name is required (min 2 chars)"); return; }
    const payload = {
      name,
      role: $("#sRole").value,
      alias: $("#sAlias").value.trim() || null,
      age: $("#sAge").value ? Number($("#sAge").value) : null,
      gender: $("#sGender").value || null,
      last_known_location: $("#sLocation").value.trim() || null,
      notes: $("#sNotes").value.trim() || null,
      incident_id: $("#sIncident").value ? Number($("#sIncident").value) : null,
    };
    try {
      const res = await fetch("/api/persons", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Failed");
      ["sName", "sAlias", "sAge", "sLocation", "sIncident", "sNotes"].forEach(id => { $("#" + id).value = ""; });
      loadSuspects();
    } catch (err) {
      alert("Save failed: " + err.message);
    }
  });

  let searchTimer;
  $("#sSearch")?.addEventListener("input", (e) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => loadSuspects(e.target.value.trim()), 300);
  });

  function escapeHtml(s) {
    return String(s ?? "").replace(/[&<>"']/g, c =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  /* ---------- 3. REMOVED BROKEN BUTTON OVERRIDES ---------- */
  // The duplicate event listeners for hamburger, advViz, refresh, etc. 
  // have been removed from here to prevent them from overriding setupUI().
})();

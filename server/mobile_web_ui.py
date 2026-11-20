"""Installable Mobile Web App (PWA) for Drivers & Students served at /app.

Drivers and students can open http://<YOUR-LAPTOP-IP>:5000/app on any Android
or iPhone browser and tap 'Add to Home Screen' — no 1.5-hour APK compile needed!
"""

MOBILE_APP_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="theme-color" content="#0f172a">
<link rel="manifest" href="/manifest.json">
<title>Bus Tracking App</title>
<style>
  :root { --bg:#0f172a; --card:#1e293b; --border:#334155; --amber:#f59e0b; --blue:#3b82f6; --green:#10b981; --red:#ef4444; --text:#f8fafc; --muted:#94a3b8; }
  * { box-sizing:border-box; font-family:system-ui,-apple-system,sans-serif; }
  body { margin:0; background:var(--bg); color:var(--text); min-height:100vh; }
  .app { max-width:460px; margin:0 auto; padding:16px; }
  .screen { display:none; }
  .screen.active { display:block; }
  .card { background:var(--card); border:1px solid var(--border); border-radius:14px; padding:16px; margin-bottom:12px; }
  h1 { margin:0 0 6px; font-size:22px; color:var(--amber); text-align:center; }
  h2 { margin:0 0 10px; font-size:17px; color:var(--amber); }
  .sub { color:var(--muted); font-size:13px; text-align:center; margin-bottom:14px; }
  input { width:100%; background:#0f172a; color:var(--text); border:1px solid var(--border); border-radius:10px; padding:11px 12px; margin-bottom:10px; font-size:14px; }
  button { width:100%; border:none; border-radius:10px; padding:12px; font-weight:700; font-size:14px; cursor:pointer; margin-bottom:8px; }
  .btn-amber { background:var(--amber); color:#0f172a; }
  .btn-blue { background:var(--blue); color:#fff; }
  .btn-green { background:var(--green); color:#fff; }
  .btn-red { background:var(--red); color:#fff; }
  .btn-dark { background:#334155; color:#fff; }
  .row { display:flex; gap:8px; }
  .row > * { flex:1; }
  .topbar { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }
  .topbar h2 { margin:0; }
  .topbar button { width:auto; padding:7px 12px; margin:0; font-size:12px; }
  .badge { display:inline-block; padding:3px 8px; border-radius:99px; font-size:11px; font-weight:700; }
  .b-green { background:rgba(16,185,129,.2); color:#34d399; }
  .b-amber { background:rgba(245,158,11,.2); color:#fbbf24; }
  .b-red { background:rgba(239,68,68,.2); color:#f87171; }
  canvas { width:100%; height:220px; background:#0b1220; border:1px solid var(--border); border-radius:12px; display:block; }
  .legend { font-size:11px; color:var(--muted); text-align:center; margin-top:6px; }
  .item { background:#0f172a; border:1px solid var(--border); border-radius:10px; padding:10px; margin-bottom:8px; font-size:13px; }
  #toast { position:fixed; bottom:16px; left:50%; transform:translateX(-50%); background:var(--green); color:#0f172a; padding:10px 16px; border-radius:10px; font-weight:700; font-size:13px; display:none; z-index:99; max-width:90%; text-align:center; }
</style>
</head>
<body>
<div class="app">

  <!-- SCREEN 1: ROLE SELECT -->
  <div id="sc-role" class="screen active">
    <div style="text-align:center; padding:18px 0 6px;">
      <img src="/assets/icons/app_icon.png" alt="Bus Icon" style="width:76px;height:76px;border-radius:18px;">
    </div>
    <h1>Bus Tracking System</h1>
    <div class="sub">Live GPS Tracking, Approvals &amp; Instant Alerts</div>
    <div class="card">
      <h2>Choose Your Portal</h2>
      <button class="btn-amber" onclick="openAuth('driver')">Sign in as Driver</button>
      <button class="btn-blue" onclick="openAuth('student')">Sign in as Student</button>
    </div>
    <div class="sub">Tip: Tap your phone browser menu &rarr; <strong>Add to Home Screen</strong> to install this as an app!</div>
  </div>

  <!-- SCREEN 2: SEPARATE DRIVER / STUDENT AUTH -->
  <div id="sc-auth" class="screen">
    <div class="topbar">
      <button class="btn-dark" onclick="showScreen('sc-role')">&larr; Back</button>
      <h2 id="authTitle">Sign In</h2>
    </div>
    <div class="row" style="margin-bottom:10px;">
      <button id="tabLogin" class="btn-blue" onclick="setAuthMode('login')">Sign In</button>
      <button id="tabReg" class="btn-dark" onclick="setAuthMode('register')">Create Account</button>
    </div>
    <div class="card">
      <div id="regFields" style="display:none;">
        <input id="aName" placeholder="Full Name">
        <input id="aPhone" placeholder="Phone Number (optional)">
      </div>
      <input id="aEmail" type="email" placeholder="Email (e.g. driver1@bus.com)">
      <input id="aPass" type="password" placeholder="Password" value="password123">
      <button id="authSubmitBtn" class="btn-amber" onclick="submitAuth()">Sign In</button>
      <div class="sub" style="margin:6px 0 0;">Demo: driver1@bus.com or student1@bus.com (password123)</div>
    </div>
  </div>

  <!-- SCREEN 3: STUDENT ROUTE SELECTION -->
  <div id="sc-route" class="screen">
    <div class="topbar">
      <h2>Select Bus Route</h2>
      <button class="btn-red" onclick="signOut()">Sign Out</button>
    </div>
    <div id="routeStatus" class="card" style="font-size:13px; color:var(--amber);">Choose your bus route to send an approval request to the driver.</div>
    <div id="routesList"></div>
  </div>

  <!-- SCREEN 4: STUDENT DASHBOARD -->
  <div id="sc-student" class="screen">
    <div class="topbar">
      <h2 id="stWelcome">Live Bus Tracker</h2>
      <button class="btn-red" onclick="signOut()">Sign Out</button>
    </div>
    <div class="card" style="font-size:13px; line-height:1.6;">
      <div id="stDriver"></div>
      <div id="stSchedule" style="color:var(--amber); font-weight:600;"></div>
      <div id="stPickup" style="color:var(--green);"></div>
      <div id="stDest" style="color:var(--muted);"></div>
    </div>
    <div class="card">
      <canvas id="mapCanvas" width="400" height="220"></canvas>
      <div class="legend">&#9679; Amber: Bus &nbsp; &#9679; Blue: You &nbsp; &#9679; Green: Pickup &nbsp; &#9679; Red: Destination</div>
    </div>
    <button class="btn-amber" onclick="sendWaitPrompt()">WAIT! I'm Late — Tell Driver My Time</button>
    <div class="card">
      <h2>Live Notifications</h2>
      <div id="stNotifs"></div>
    </div>
  </div>

  <!-- SCREEN 5: DRIVER DASHBOARD -->
  <div id="sc-driver" class="screen">
    <div class="topbar">
      <h2 id="drWelcome">Driver Panel</h2>
      <button class="btn-red" onclick="signOut()">Sign Out</button>
    </div>
    <div class="card" style="font-size:13px; line-height:1.6;">
      <div id="drRouteInfo" style="font-weight:700;"></div>
      <div id="drCount" style="color:var(--green); font-weight:700;"></div>
      <div id="drGpsStatus" style="color:var(--muted); margin-bottom:8px;">Live Location: OFF</div>
      <div class="row">
        <button id="drShareBtn" class="btn-green" onclick="toggleDriverGPS()">Start Live GPS</button>
        <button class="btn-blue" onclick="simulateNextStop()">Next Stop Alert</button>
      </div>
    </div>
    <div class="card">
      <h2>Student Wait Requests</h2>
      <div id="drWaits"></div>
    </div>
    <div class="card">
      <h2>Student Approvals &amp; Roster</h2>
      <div id="drStudents"></div>
    </div>
  </div>

</div>
<div id="toast"></div>

<script>
let currentRole = 'student';
let authMode = 'login';
let currentUser = null;
let currentRoute = null;
let pollTimer = null;
let gpsWatchId = null;
let simStopIdx = 0;
let seenNotifs = new Set();

function toast(msg, err=false) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.background = err ? '#ef4444' : '#10b981';
  t.style.color = err ? '#fff' : '#0f172a';
  t.style.display = 'block';
  setTimeout(() => t.style.display = 'none', 3200);
}

function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}

async function api(url, method='GET', body=null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Error');
  return data;
}

function openAuth(role) {
  currentRole = role;
  document.getElementById('authTitle').textContent = role === 'driver' ? 'Driver Portal' : 'Student Portal';
  document.getElementById('aEmail').placeholder = role === 'driver' ? 'driver1@bus.com' : 'student1@bus.com';
  setAuthMode('login');
  showScreen('sc-auth');
}

function setAuthMode(mode) {
  authMode = mode;
  const isReg = mode === 'register';
  document.getElementById('regFields').style.display = isReg ? 'block' : 'none';
  document.getElementById('tabLogin').className = isReg ? 'btn-dark' : 'btn-blue';
  document.getElementById('tabReg').className = isReg ? 'btn-blue' : 'btn-dark';
  document.getElementById('authSubmitBtn').textContent = (isReg ? 'Register as ' : 'Sign In as ') + (currentRole === 'driver' ? 'Driver' : 'Student');
}

async function submitAuth() {
  try {
    const email = document.getElementById('aEmail').value.trim();
    const password = document.getElementById('aPass').value.trim();
    let res;
    if (authMode === 'register') {
      res = await api('/api/auth/register', 'POST', {
        name: document.getElementById('aName').value.trim(),
        phone: document.getElementById('aPhone').value.trim(),
        email, password, role: currentRole
      });
    } else {
      res = await api('/api/auth/login', 'POST', { email, password, role: currentRole });
    }
    currentUser = res.user;
    if (currentUser.role === 'driver') {
      showScreen('sc-driver');
      startPolling(refreshDriver);
    } else {
      await routeStudentAfterLogin();
    }
  } catch (e) { toast(e.message, true); }
}

function startPolling(fn) {
  if (pollTimer) clearInterval(pollTimer);
  fn();
  pollTimer = setInterval(fn, 3000);
}

function signOut() {
  if (pollTimer) clearInterval(pollTimer);
  if (gpsWatchId !== null && navigator.geolocation) navigator.geolocation.clearWatch(gpsWatchId);
  gpsWatchId = null;
  currentUser = null;
  currentRoute = null;
  showScreen('sc-role');
}

// --- STUDENT FLOW ---
async function routeStudentAfterLogin() {
  const st = await api(`/api/student/${currentUser.id}/status`);
  if (st.enrolled && st.enrollment.status === 'approved') {
    showScreen('sc-student');
    startPolling(refreshStudent);
  } else {
    showScreen('sc-route');
    startPolling(refreshStudentRoutes);
  }
}

async function refreshStudentRoutes() {
  if (!currentUser) return;
  const st = await api(`/api/student/${currentUser.id}/status`);
  if (st.enrolled && st.enrollment.status === 'approved') {
    showScreen('sc-student');
    startPolling(refreshStudent);
    return;
  }
  if (st.enrolled && st.enrollment.status === 'pending') {
    document.getElementById('routeStatus').textContent =
      `Waiting for driver ${st.route.driver_name} (${st.route.bus_number}) to approve your request...`;
  }
  const data = await api('/api/routes');
  document.getElementById('routesList').innerHTML = data.routes.map(r => `
    <div class="card">
      <strong>${r.bus_number} - ${r.route_name}</strong><br>
      <small style="color:#94a3b8">Driver: ${r.driver_name} | Students: ${r.approved_student_count}/${r.capacity}</small><br>
      <small style="color:#f59e0b">Dep: ${r.departure_time} &rarr; Arr: ${r.arrival_time} (${r.destination_name})</small>
      <button class="btn-green" style="margin-top:10px;" onclick="requestRoute(${r.id})">Select Route &amp; Request Approval</button>
    </div>
  `).join('');
}

async function requestRoute(routeId) {
  await api('/api/enrollments/request', 'POST', { student_id: currentUser.id, route_id: routeId });
  toast('Approval request sent to driver!');
  refreshStudentRoutes();
}

async function refreshStudent() {
  if (!currentUser) return;
  const st = await api(`/api/student/${currentUser.id}/status`);
  if (!st.enrolled || st.enrollment.status !== 'approved') return;
  currentRoute = st.route;
  const enr = st.enrollment;

  document.getElementById('stWelcome').textContent = `Hi, ${currentUser.name}`;
  const liveBadge = currentRoute.is_sharing_location
    ? '<span class="badge b-green">LIVE GPS</span>'
    : '<span class="badge b-amber">OFFLINE</span>';
  document.getElementById('stDriver').innerHTML = `<strong>Driver:</strong> ${currentRoute.driver_name} (${currentRoute.bus_number}) ${liveBadge}`;
  document.getElementById('stSchedule').textContent = `Departure: ${currentRoute.departure_time}  |  Arrival: ${currentRoute.arrival_time}`;
  document.getElementById('stPickup').textContent = `Pickup Point: ${enr.pickup_stop_name || 'Assigned by driver'}`;
  document.getElementById('stDest').textContent = `Destination: ${currentRoute.destination_name}`;

  drawMap(
    [currentRoute.current_lat, currentRoute.current_lon],
    enr.student_lat ? [enr.student_lat, enr.student_lon] : (enr.pickup_lat ? [enr.pickup_lat, enr.pickup_lon] : null),
    enr.pickup_lat ? [enr.pickup_lat, enr.pickup_lon] : null,
    [currentRoute.destination_lat, currentRoute.destination_lon]
  );

  const ndata = await api(`/api/notifications/${currentUser.id}`);
  for (const n of ndata.notifications) {
    if (!n.is_read && !seenNotifs.has(n.id)) {
      seenNotifs.add(n.id);
      toast(`${n.title}: ${n.message}`);
    }
  }
  document.getElementById('stNotifs').innerHTML = ndata.notifications.slice(0, 8).map(n => `
    <div class="item"><strong style="color:#f59e0b">${n.title}</strong><br>${n.message}</div>
  `).join('') || '<div style="color:#94a3b8;font-size:13px;">No notifications yet.</div>';
}

async function sendWaitPrompt() {
  if (!currentRoute) return;
  const msg = prompt("What time will you reach the bus? (e.g. 5 mins - 07:55 AM)", "5 minutes");
  if (!msg) return;
  await api('/api/wait-requests', 'POST', { student_id: currentUser.id, route_id: currentRoute.id, eta_message: msg });
  toast('Wait request sent to driver!');
}

function drawMap(bus, student, pickup, dest) {
  const c = document.getElementById('mapCanvas');
  const ctx = c.getContext('2d');
  ctx.clearRect(0, 0, c.width, c.height);
  const pts = [bus, student, pickup, dest].filter(Boolean);
  if (!pts.length) return;
  const lats = pts.map(p => p[0]), lons = pts.map(p => p[1]);
  const minLat = Math.min(...lats), maxLat = Math.max(...lats);
  const minLon = Math.min(...lons), maxLon = Math.max(...lons);
  const latSpan = Math.max(maxLat - minLat, 0.005);
  const lonSpan = Math.max(maxLon - minLon, 0.005);
  const pad = 28;
  const toXY = (p) => [
    pad + ((p[1] - minLon) / lonSpan) * (c.width - pad * 2),
    c.height - pad - ((p[0] - minLat) / latSpan) * (c.height - pad * 2)
  ];

  // Grid
  ctx.strokeStyle = '#1e293b'; ctx.lineWidth = 1;
  for (let i = 1; i < 5; i++) {
    ctx.beginPath(); ctx.moveTo(c.width*i/5, 0); ctx.lineTo(c.width*i/5, c.height); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, c.height*i/5); ctx.lineTo(c.width, c.height*i/5); ctx.stroke();
  }
  // Route line
  const linePts = [bus, pickup, dest].filter(Boolean).map(toXY);
  if (linePts.length >= 2) {
    ctx.strokeStyle = 'rgba(245,158,11,0.6)'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(linePts[0][0], linePts[0][1]);
    for (let i = 1; i < linePts.length; i++) ctx.lineTo(linePts[i][0], linePts[i][1]);
    ctx.stroke();
  }
  const drawDot = (p, color, label) => {
    if (!p) return;
    const [x, y] = toXY(p);
    ctx.fillStyle = color; ctx.beginPath(); ctx.arc(x, y, 8, 0, Math.PI*2); ctx.fill();
    ctx.fillStyle = '#f8fafc'; ctx.font = 'bold 11px sans-serif'; ctx.fillText(label, x + 10, y + 4);
  };
  drawDot(dest, '#ef4444', 'Dest');
  drawDot(pickup, '#10b981', 'Pickup');
  drawDot(student, '#3b82f6', 'You');
  drawDot(bus, '#f59e0b', 'BUS');
}

// --- DRIVER FLOW ---
async function refreshDriver() {
  if (!currentUser) return;
  document.getElementById('drWelcome').textContent = `Driver: ${currentUser.name}`;
  const rdata = await api(`/api/driver/${currentUser.id}/route`);
  currentRoute = rdata.route;
  if (!currentRoute) {
    document.getElementById('drRouteInfo').textContent = 'No route assigned yet. Create one from the Laptop Admin Panel.';
    return;
  }
  document.getElementById('drRouteInfo').textContent = `${currentRoute.bus_number} | ${currentRoute.route_name} -> ${currentRoute.destination_name}`;
  document.getElementById('drCount').textContent = `Students in Bus: ${currentRoute.approved_student_count} / ${currentRoute.capacity} | Dep: ${currentRoute.departure_time} | Arr: ${currentRoute.arrival_time}`;

  const wdata = await api(`/api/routes/${currentRoute.id}/wait-requests`);
  document.getElementById('drWaits').innerHTML = wdata.wait_requests.map(w => `
    <div class="item">
      <strong>${w.student_name}</strong> <span class="badge ${w.status==='pending'?'b-amber':'b-green'}">${w.status}</span><br>
      ETA: ${w.eta_message}
      ${w.status === 'pending' ? `
        <div class="row" style="margin-top:8px;">
          <button class="btn-green" onclick="respondWait(${w.id}, 'approved')">OK (Wait)</button>
          <button class="btn-red" onclick="respondWait(${w.id}, 'denied')">Deny</button>
        </div>` : ''}
    </div>
  `).join('') || '<div style="color:#94a3b8;font-size:13px;">No wait requests.</div>';

  const edata = await api(`/api/routes/${currentRoute.id}/enrollments`);
  document.getElementById('drStudents').innerHTML = edata.enrollments.map(e => `
    <div class="item">
      <strong>${e.student_name}</strong> <span class="badge ${e.status==='approved'?'b-green':'b-amber'}">${e.status}</span><br>
      <small style="color:#94a3b8">Pickup: ${e.pickup_stop_name || 'Unassigned'}</small>
      ${e.status === 'pending' ? `
        <div class="row" style="margin-top:8px;">
          <button class="btn-green" onclick="decideEnr(${e.id}, 'approved')">Approve</button>
          <button class="btn-red" onclick="decideEnr(${e.id}, 'rejected')">Reject</button>
        </div>` : ''}
    </div>
  `).join('') || '<div style="color:#94a3b8;font-size:13px;">No students yet.</div>';
}

function toggleDriverGPS() {
  if (!currentRoute) return;
  const btn = document.getElementById('drShareBtn');
  if (gpsWatchId !== null) {
    navigator.geolocation.clearWatch(gpsWatchId);
    gpsWatchId = null;
    btn.textContent = 'Start Live GPS';
    btn.className = 'btn-green';
    document.getElementById('drGpsStatus').textContent = 'Live Location: OFF';
    api(`/api/routes/${currentRoute.id}/location`, 'POST', { lat: currentRoute.current_lat, lon: currentRoute.current_lon, is_sharing: false });
    return;
  }
  if (!navigator.geolocation) {
    toast('Phone GPS unavailable over HTTP — use Next Stop Alert to test.', true);
    return;
  }
  btn.textContent = 'Stop Live GPS';
  btn.className = 'btn-red';
  document.getElementById('drGpsStatus').textContent = 'Live Location: ON (GPS Active)';
  gpsWatchId = navigator.geolocation.watchPosition(
    async (pos) => {
      const res = await api(`/api/routes/${currentRoute.id}/location`, 'POST', {
        lat: pos.coords.latitude, lon: pos.coords.longitude, is_sharing: true
      });
      document.getElementById('drGpsStatus').textContent = `Live GPS: ${pos.coords.latitude.toFixed(5)}, ${pos.coords.longitude.toFixed(5)}`;
      if (res.arrived_stops_notified && res.arrived_stops_notified.length) {
        toast('Auto-notified students: Arrived at ' + res.arrived_stops_notified.join(', '));
      }
    },
    () => toast('Allow location permission or tap Next Stop Alert.', true),
    { enableHighAccuracy: true }
  );
}

async function simulateNextStop() {
  if (!currentRoute || !currentRoute.stops.length) return;
  const stop = currentRoute.stops[simStopIdx % currentRoute.stops.length];
  simStopIdx++;
  const res = await api(`/api/routes/${currentRoute.id}/location`, 'POST', { lat: stop.lat, lon: stop.lon, is_sharing: true });
  document.getElementById('drGpsStatus').textContent = `Live Location: ${stop.stop_name}`;
  if (res.arrived_stops_notified && res.arrived_stops_notified.length) {
    toast('Auto-notified all students: Bus arrived at ' + res.arrived_stops_notified.join(', '));
  } else {
    toast('Moved bus to ' + stop.stop_name);
  }
}

async function decideEnr(id, decision) {
  await api(`/api/enrollments/${id}/decision`, 'POST', { decision });
  toast('Student ' + decision);
  refreshDriver();
}

async function respondWait(id, decision) {
  await api(`/api/wait-requests/${id}/respond`, 'POST', { decision });
  toast('Notification sent to student!');
  refreshDriver();
}
</script>
</body>
</html>
"""

PWA_MANIFEST_JSON = {
    "name": "Bus Tracking System",
    "short_name": "BusTracker",
    "start_url": "/app",
    "display": "standalone",
    "background_color": "#0f172a",
    "theme_color": "#0f172a",
    "icons": [
        {
            "src": "/assets/icons/app_icon.png",
            "sizes": "512x512",
            "type": "image/png",
        }
    ],
}

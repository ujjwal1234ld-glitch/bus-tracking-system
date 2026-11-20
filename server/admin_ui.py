"""Admin Control Panel & Mobile APK Download pages served directly by the laptop server.

Pure Python strings — zero external frameworks required.
"""

ADMIN_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bus Tracking System - Laptop Admin Control Panel</title>
<style>
  :root {
    --bg: #0f172a; --card: #1e293b; --border: #334155;
    --primary: #f59e0b; --blue: #3b82f6; --green: #10b981; --red: #ef4444;
    --text: #f8fafc; --muted: #94a3b8;
  }
  * { box-sizing: border-box; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }
  body { margin: 0; background: var(--bg); color: var(--text); padding: 20px; }
  .wrap { max-width: 1180px; margin: 0 auto; }
  header { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 20px; }
  h1 { margin: 0; font-size: 24px; color: var(--primary); }
  .sub { color: var(--muted); font-size: 13px; margin-top: 4px; }
  .pill { background: #1e293b; border: 1px solid var(--border); padding: 8px 14px; border-radius: 10px; font-size: 13px; }
  .pill strong { color: var(--primary); }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 20px; }
  .stat { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 14px; }
  .stat .k { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }
  .stat .v { font-size: 26px; font-weight: 700; margin-top: 6px; }
  .tabs { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
  .tab { background: var(--card); color: var(--text); border: 1px solid var(--border); padding: 9px 16px; border-radius: 8px; cursor: pointer; font-weight: 600; }
  .tab.active { background: var(--primary); color: #0f172a; border-color: var(--primary); }
  .panel { display: none; background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 18px; margin-bottom: 18px; }
  .panel.active { display: block; }
  .row { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; align-items: center; }
  input, select { background: #0f172a; color: var(--text); border: 1px solid var(--border); padding: 8px 10px; border-radius: 8px; font-size: 13px; }
  button { border: none; padding: 8px 14px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 13px; }
  .btn-primary { background: var(--primary); color: #0f172a; }
  .btn-blue { background: var(--blue); color: white; }
  .btn-green { background: var(--green); color: white; }
  .btn-red { background: var(--red); color: white; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }
  th, td { text-align: left; padding: 9px 10px; border-bottom: 1px solid var(--border); }
  th { color: var(--muted); font-weight: 600; }
  .badge { padding: 3px 8px; border-radius: 999px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
  .b-green { background: rgba(16,185,129,0.2); color: #34d399; }
  .b-amber { background: rgba(245,158,11,0.2); color: #fbbf24; }
  .b-red { background: rgba(239,68,68,0.2); color: #f87171; }
  .b-blue { background: rgba(59,130,246,0.2); color: #60a5fa; }
  #toast { position: fixed; bottom: 18px; right: 18px; background: var(--green); color: #0f172a; padding: 10px 16px; border-radius: 10px; font-weight: 700; display: none; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>Bus Tracking System — Laptop Admin Control Panel</h1>
      <div class="sub">Control your SQLite database, drivers, 30-student bus routes, live GPS, and mobile APK downloads from your laptop.</div>
    </div>
    <div class="row" style="margin:0;">
      <div class="pill">Mobile Server URL: <strong id="lanUrl">Loading...</strong></div>
      <a href="/download" target="_blank"><button class="btn-blue">Mobile APK Download Page</button></a>
      <a href="/api/admin/backup-db"><button class="btn-primary">Download DB Backup</button></a>
    </div>
  </header>

  <div class="grid">
    <div class="stat"><div class="k">Drivers</div><div class="v" id="stDrivers">0</div></div>
    <div class="stat"><div class="k">Students</div><div class="v" id="stStudents">0</div></div>
    <div class="stat"><div class="k">Bus Routes</div><div class="v" id="stRoutes">0</div></div>
    <div class="stat"><div class="k">Approved Riders</div><div class="v" id="stApproved">0</div></div>
    <div class="stat"><div class="k">Pending Approvals</div><div class="v" id="stPending">0</div></div>
    <div class="stat"><div class="k">Pending Wait Alerts</div><div class="v" id="stWaits">0</div></div>
  </div>

  <div class="tabs">
    <button class="tab active" onclick="showTab('routes', this)">Bus Routes & Live GPS</button>
    <button class="tab" onclick="showTab('users', this)">Drivers & Students DB</button>
    <button class="tab" onclick="showTab('enrollments', this)">Approvals & Pickups</button>
    <button class="tab" onclick="showTab('waits', this)">Wait Requests & Alerts</button>
    <button class="tab" onclick="seedDemo()" style="margin-left:auto; background:#1e3a5f; color:#93c5fd;">Seed Demo (1 Driver + 30 Students)</button>
  </div>

  <!-- TAB 1: ROUTES & LIVE GPS -->
  <div id="tab-routes" class="panel active">
    <h3 style="margin-top:0;">Create New Bus Route</h3>
    <div class="row">
      <select id="rtDriver"></select>
      <input id="rtBusNum" placeholder="Bus Number (e.g. BUS-102)">
      <input id="rtName" placeholder="Route Name">
      <input id="rtDest" placeholder="Destination" value="University Main Campus">
      <input id="rtDep" placeholder="Departure" value="07:30 AM" style="width:105px;">
      <input id="rtArr" placeholder="Arrival" value="08:20 AM" style="width:105px;">
      <input id="rtCap" type="number" value="30" style="width:75px;" title="Capacity">
      <button class="btn-green" onclick="createRoute()">Create Route</button>
    </div>
    <table>
      <thead><tr><th>ID</th><th>Bus & Route</th><th>Driver</th><th>Students</th><th>Schedule</th><th>Live GPS</th><th>Actions</th></tr></thead>
      <tbody id="routesTable"></tbody>
    </table>
  </div>

  <!-- TAB 2: USERS DATABASE -->
  <div id="tab-users" class="panel">
    <h3 style="margin-top:0;">Register New Driver or Student</h3>
    <div class="row">
      <select id="uRole"><option value="student">Student</option><option value="driver">Driver</option></select>
      <input id="uName" placeholder="Full Name">
      <input id="uEmail" placeholder="Email">
      <input id="uPhone" placeholder="Phone">
      <input id="uPass" type="password" placeholder="Password" value="password123">
      <button class="btn-green" onclick="createUser()">Add Account</button>
    </div>
    <table>
      <thead><tr><th>ID</th><th>Role</th><th>Name</th><th>Email</th><th>Phone</th><th>Action</th></tr></thead>
      <tbody id="usersTable"></tbody>
    </table>
  </div>

  <!-- TAB 3: ENROLLMENTS & APPROVALS -->
  <div id="tab-enrollments" class="panel">
    <div class="row">
      <h3 style="margin:0;">Student Enrollments by Route</h3>
      <select id="enrRouteSelect" onchange="loadEnrollments()"></select>
      <button class="btn-blue" onclick="loadEnrollments()">Refresh</button>
    </div>
    <table>
      <thead><tr><th>Student</th><th>Email</th><th>Status</th><th>Pickup Stop</th><th>Actions</th></tr></thead>
      <tbody id="enrollmentsTable"></tbody>
    </table>
  </div>

  <!-- TAB 4: WAIT REQUESTS & NOTIFICATIONS -->
  <div id="tab-waits" class="panel">
    <div class="row">
      <h3 style="margin:0;">Student Wait Requests</h3>
      <select id="waitRouteSelect" onchange="loadWaits()"></select>
      <button class="btn-blue" onclick="loadWaits()">Refresh</button>
    </div>
    <table>
      <thead><tr><th>Student</th><th>ETA Message</th><th>Status</th><th>Action</th></tr></thead>
      <tbody id="waitsTable"></tbody>
    </table>
    <h3 style="margin-top:20px;">Recent System Notifications</h3>
    <table>
      <thead><tr><th>Time</th><th>User</th><th>Title</th><th>Message</th></tr></thead>
      <tbody id="notifsTable"></tbody>
    </table>
  </div>
</div>

<div id="toast"></div>

<script>
let cachedRoutes = [];
let cachedUsers = [];

function toast(msg, isErr=false) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.background = isErr ? '#ef4444' : '#10b981';
  t.style.color = isErr ? '#fff' : '#0f172a';
  t.style.display = 'block';
  setTimeout(() => t.style.display = 'none', 2800);
}

function showTab(name, btn) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  if (btn) btn.classList.add('active');
  if (name === 'enrollments') loadEnrollments();
  if (name === 'waits') loadWaits();
}

async function api(url, method='GET', body=null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Request failed');
  return data;
}

async function refreshAll() {
  try {
    const data = await api('/api/admin/overview');
    document.getElementById('lanUrl').textContent = data.lan_url;
    document.getElementById('stDrivers').textContent = data.stats.drivers;
    document.getElementById('stStudents').textContent = data.stats.students;
    document.getElementById('stRoutes').textContent = data.stats.routes;
    document.getElementById('stApproved').textContent = data.stats.approved_enrollments;
    document.getElementById('stPending').textContent = data.stats.pending_enrollments;
    document.getElementById('stWaits').textContent = data.stats.pending_wait_requests;

    cachedRoutes = data.routes;
    cachedUsers = data.users;
    renderRoutes();
    renderUsers();
    renderNotifications(data.recent_notifications);
    populateRouteSelects();
  } catch (e) {
    toast(e.message, true);
  }
}

function populateRouteSelects() {
  const driverSel = document.getElementById('rtDriver');
  const drivers = cachedUsers.filter(u => u.role === 'driver');
  driverSel.innerHTML = drivers.map(d => `<option value="${d.id}">${d.name} (${d.email})</option>`).join('') || '<option value="">Create a driver first</option>';

  for (const id of ['enrRouteSelect', 'waitRouteSelect']) {
    const sel = document.getElementById(id);
    const prev = sel.value;
    sel.innerHTML = cachedRoutes.map(r => `<option value="${r.id}">${r.bus_number} - ${r.route_name}</option>`).join('');
    if (prev && cachedRoutes.some(r => String(r.id) === prev)) sel.value = prev;
  }
}

function renderRoutes() {
  const tb = document.getElementById('routesTable');
  tb.innerHTML = cachedRoutes.map(r => `
    <tr>
      <td>#${r.id}</td>
      <td><strong>${r.bus_number}</strong><br><span style="color:#94a3b8">${r.route_name}</span></td>
      <td>${r.driver_name}</td>
      <td><span class="badge b-green">${r.approved_student_count} / ${r.capacity}</span></td>
      <td>Dep: ${r.departure_time}<br>Arr: ${r.arrival_time}<br><small style="color:#94a3b8">${r.destination_name}</small></td>
      <td><span class="badge ${r.is_sharing_location ? 'b-green' : 'b-amber'}">${r.is_sharing_location ? 'LIVE' : 'OFFLINE'}</span><br><small>${r.current_lat.toFixed(4)}, ${r.current_lon.toFixed(4)}</small></td>
      <td><button class="btn-blue" onclick="resetTrip(${r.id})">Reset Trip</button></td>
    </tr>
  `).join('') || '<tr><td colspan="7" style="color:#94a3b8">No routes yet.</td></tr>';
}

function renderUsers() {
  const tb = document.getElementById('usersTable');
  tb.innerHTML = cachedUsers.map(u => `
    <tr>
      <td>#${u.id}</td>
      <td><span class="badge ${u.role === 'driver' ? 'b-amber' : 'b-blue'}">${u.role}</span></td>
      <td>${u.name}</td>
      <td>${u.email}</td>
      <td>${u.phone || '-'}</td>
      <td><button class="btn-red" onclick="deleteUser(${u.id})">Delete</button></td>
    </tr>
  `).join('');
}

function renderNotifications(notifs) {
  const tb = document.getElementById('notifsTable');
  tb.innerHTML = notifs.map(n => `
    <tr>
      <td><small>${n.created_at}</small></td>
      <td>${n.user_name} (${n.user_role})</td>
      <td><strong>${n.title}</strong></td>
      <td>${n.message}</td>
    </tr>
  `).join('') || '<tr><td colspan="4" style="color:#94a3b8">No notifications yet.</td></tr>';
}

async function createUser() {
  try {
    await api('/api/auth/register', 'POST', {
      role: document.getElementById('uRole').value,
      name: document.getElementById('uName').value,
      email: document.getElementById('uEmail').value,
      phone: document.getElementById('uPhone').value,
      password: document.getElementById('uPass').value,
    });
    toast('Account created!');
    refreshAll();
  } catch (e) { toast(e.message, true); }
}

async function deleteUser(id) {
  if (!confirm('Delete this user account?')) return;
  try {
    await api(`/api/admin/users/${id}/delete`, 'POST');
    toast('User deleted.');
    refreshAll();
  } catch (e) { toast(e.message, true); }
}

async function createRoute() {
  try {
    await api('/api/routes', 'POST', {
      driver_id: Number(document.getElementById('rtDriver').value),
      bus_number: document.getElementById('rtBusNum').value,
      route_name: document.getElementById('rtName').value,
      destination_name: document.getElementById('rtDest').value,
      departure_time: document.getElementById('rtDep').value,
      arrival_time: document.getElementById('rtArr').value,
      capacity: Number(document.getElementById('rtCap').value || 30),
    });
    toast('Bus route created!');
    refreshAll();
  } catch (e) { toast(e.message, true); }
}

async function resetTrip(routeId) {
  await api(`/api/routes/${routeId}/reset-trip`, 'POST');
  toast('Trip stop-arrival alerts reset.');
  refreshAll();
}

async function loadEnrollments() {
  const rid = document.getElementById('enrRouteSelect').value;
  if (!rid) return;
  const data = await api(`/api/routes/${rid}/enrollments`);
  const tb = document.getElementById('enrollmentsTable');
  tb.innerHTML = data.enrollments.map(e => `
    <tr>
      <td><strong>${e.student_name}</strong></td>
      <td>${e.student_email}</td>
      <td><span class="badge ${e.status==='approved'?'b-green':e.status==='pending'?'b-amber':'b-red'}">${e.status}</span></td>
      <td>${e.pickup_stop_name || 'Unassigned'}</td>
      <td>
        <button class="btn-green" onclick="decideEnr(${e.id}, 'approved')">Approve</button>
        <button class="btn-red" onclick="decideEnr(${e.id}, 'rejected')">Reject</button>
      </td>
    </tr>
  `).join('') || '<tr><td colspan="5" style="color:#94a3b8">No students on this route yet.</td></tr>';
}

async function decideEnr(id, decision) {
  try {
    await api(`/api/enrollments/${id}/decision`, 'POST', { decision });
    toast('Enrollment updated!');
    loadEnrollments();
    refreshAll();
  } catch (e) { toast(e.message, true); }
}

async function loadWaits() {
  const rid = document.getElementById('waitRouteSelect').value;
  if (!rid) return;
  const data = await api(`/api/routes/${rid}/wait-requests`);
  const tb = document.getElementById('waitsTable');
  tb.innerHTML = data.wait_requests.map(w => `
    <tr>
      <td><strong>${w.student_name}</strong></td>
      <td>${w.eta_message}</td>
      <td><span class="badge ${w.status==='approved'?'b-green':w.status==='pending'?'b-amber':'b-red'}">${w.status}</span></td>
      <td>
        ${w.status === 'pending' ? `
          <button class="btn-green" onclick="respondWait(${w.id}, 'approved')">OK (Wait)</button>
          <button class="btn-red" onclick="respondWait(${w.id}, 'denied')">Deny</button>
        ` : 'Completed'}
      </td>
    </tr>
  `).join('') || '<tr><td colspan="4" style="color:#94a3b8">No wait requests yet.</td></tr>';
}

async function respondWait(id, decision) {
  try {
    await api(`/api/wait-requests/${id}/respond`, 'POST', { decision });
    toast('Notification sent to student!');
    loadWaits();
    refreshAll();
  } catch (e) { toast(e.message, true); }
}

async function seedDemo() {
  try {
    await api('/api/admin/seed-demo', 'POST');
    toast('Seeded 1 driver, 1 route, and 30 students!');
    refreshAll();
  } catch (e) { toast(e.message, true); }
}

refreshAll();
setInterval(refreshAll, 5000);
</script>
</body>
</html>
"""


def render_download_page(lan_url: str, apk_ready: bool) -> str:
    """Mobile-friendly page where drivers and students can download the APK from your laptop."""
    if apk_ready:
        action_html = (
            '<a href="/download/app.apk" class="btn">Download Bus Tracker APK (Android)</a>'
            '<p class="note">After installing, open the app and enter this Server URL on the Welcome screen:</p>'
        )
    else:
        action_html = (
            '<div class="warn">APK file not placed in <code>downloads/bustracker.apk</code> yet.</div>'
            '<p class="note">Build the APK using <code>buildozer -v android debug</code> (or Google Colab), '
            'copy the generated <code>.apk</code> into <code>downloads/bustracker.apk</code> on your laptop, '
            'and refresh this page so drivers and students can download it directly!</p>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Download Bus Tracking App</title>
<style>
  body {{ margin:0; background:#0f172a; color:#f8fafc; font-family:system-ui,sans-serif; display:flex; align-items:center; justify-content:center; min-height:100vh; padding:20px; }}
  .card {{ max-width:440px; width:100%; background:#1e293b; border:1px solid #334155; border-radius:16px; padding:26px; text-align:center; }}
  h1 {{ color:#f59e0b; margin:0 0 8px; font-size:24px; }}
  p {{ color:#cbd5e1; font-size:14px; line-height:1.5; }}
  .btn {{ display:block; background:#10b981; color:#fff; text-decoration:none; padding:14px 18px; border-radius:10px; font-weight:700; margin:18px 0; font-size:16px; }}
  .url {{ background:#0f172a; border:1px solid #334155; padding:12px; border-radius:10px; font-family:monospace; color:#fbbf24; font-size:15px; word-break:break-all; }}
  .warn {{ background:rgba(245,158,11,0.18); color:#fbbf24; padding:12px; border-radius:10px; font-size:13px; margin:16px 0; }}
  .note {{ font-size:13px; color:#94a3b8; }}
</style>
</head>
<body>
  <div class="card">
    <h1>Bus Tracking System</h1>
    <p>Mobile App for Bus Drivers &amp; Students (Android APK)</p>
    {action_html}
    <div class="url">{lan_url}</div>
  </div>
</body>
</html>
"""

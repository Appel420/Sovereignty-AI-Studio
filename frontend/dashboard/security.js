export function render(el, orgId) {
  el.innerHTML = `
    <h2>Security Dashboard</h2>
    <div id="audit-filters">
      <select id="action-filter">
        <option value="">All Actions</option>
        <option value="ai_call">AI Calls</option>
        <option value="login">Logins</option>
        <option value="data_access">Data Access</option>
        <option value="auth_change">Auth Changes</option>
        <option value="permission_change">Permission Changes</option>
      </select>
      <button id="refresh-audit">Refresh</button>
    </div>
    <div id="audit-stats"></div>
    <table id="audit-table">
      <thead><tr><th>Time</th><th>User</th><th>Action</th><th>Resource</th><th>Details</th></tr></thead>
      <tbody id="audit-body"></tbody>
    </table>
  `;
  async function load(action) {
    const url = action ? `/api/audit?orgId=${orgId}&action=${action}` : `/api/audit?orgId=${orgId}`;
    const res = await fetch(url);
    const data = await res.json();
    document.getElementById("audit-body").innerHTML =
      data.map(log => `<tr>
        <td>${new Date(log.created_at).toLocaleString()}</td>
        <td>${log.user_id}</td>
        <td>${log.action}</td>
        <td>${log.resource_type || '-'}</td>
        <td><pre>${JSON.stringify(log.details, null, 2)}</pre></td>
      </tr>`).join("");
    document.getElementById("audit-stats").innerHTML =
      `<p>Total events: ${data.length}</p>`;
  }
  document.getElementById("refresh-audit").onclick = () => {
    const action = document.getElementById("action-filter").value;
    load(action);
  };
  load();
}

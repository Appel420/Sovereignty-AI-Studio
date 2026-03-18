export function render(el, orgId) {
  el.innerHTML = `
    <h2>Analytics Dashboard</h2>
    <div id="usage-stats"></div>
    <div id="provider-breakdown"></div>
    <div id="cost-tracking"></div>
  `;
  async function load() {
    const res = await fetch(`/api/analytics?orgId=${orgId}`);
    const data = await res.json();
    document.getElementById("usage-stats").innerHTML = `
      <h3>Usage Summary</h3>
      <p>Total Tokens: ${data.totalTokens || 0}</p>
      <p>Total Calls: ${data.totalCalls || 0}</p>
      <p>Active Users: ${data.activeUsers || 0}</p>
    `;
    document.getElementById("provider-breakdown").innerHTML = `
      <h3>Provider Breakdown</h3>
      ${(data.byProvider || []).map(p => `<p>${p.provider}: ${p.count} calls, ${p.tokens} tokens</p>`).join("")}
    `;
  }
  load();
}

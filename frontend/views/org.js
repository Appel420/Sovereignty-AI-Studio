export function render(el) {
  el.innerHTML = `
    <h2>Organizations</h2>
    <div id="org-list"></div>
    <input id="org-name" placeholder="New org name"/>
    <button id="create-org">Create</button>
  `;
  async function load() {
    const res = await fetch("/api/org");
    const data = await res.json();
    document.getElementById("org-list").innerHTML =
      data.map(o => `<div>${o.name}</div>`).join("");
  }
  document.getElementById("create-org").onclick = async () => {
    const name = document.getElementById("org-name").value;
    await fetch("/api/org", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name })
    });
    load();
  };
  load();
}

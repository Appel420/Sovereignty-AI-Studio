export function render(el, orgId) {
  el.innerHTML = `
    <h2>Projects</h2>
    <div id="project-list"></div>
    <input id="project-name" placeholder="New project name"/>
    <select id="project-visibility">
      <option value="private">Private</option>
      <option value="public">Public</option>
    </select>
    <button id="create-project">Create</button>
  `;
  async function load() {
    const res = await fetch(`/api/project?orgId=${orgId}`);
    const data = await res.json();
    document.getElementById("project-list").innerHTML =
      data.map(p => `<div>${p.name} (${p.visibility})</div>`).join("");
  }
  document.getElementById("create-project").onclick = async () => {
    const name = document.getElementById("project-name").value;
    const visibility = document.getElementById("project-visibility").value;
    await fetch("/api/project", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, orgId, visibility })
    });
    load();
  };
  load();
}

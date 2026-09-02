/* SGHV119 Owner Transparency Panel
 * Apple/iOS-first presentation surface. Read-only by default.
 * Shows observed provenance; it does not grant authority or execute commands.
 */
(() => {
  'use strict';
  if (window.__sghv119OwnerTransparency) return;

  const state = {
    events: [],
    identity: {
      human_owner: 'Appel420',
      machine_agent: 'GitHub Copilot',
      provider_path: 'github-copilot',
      model_id: 'unreported',
      repository: 'Appel420/Sovereignty-AI-Studio',
      branch: 'copilot/apple-owner-transparency-panel'
    },
    system: {
      platform: /iPhone|iPad/i.test(navigator.userAgent) ? 'Apple/iOS' : navigator.platform || 'unknown',
      online: navigator.onLine
    }
  };

  const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const now = () => new Date().toISOString();

  function record(event) {
    const e = {
      timestamp: now(),
      ...state.identity,
      system: {...state.system},
      ...event
    };
    state.events.unshift(e);
    state.events = state.events.slice(0, 250);
    renderEvents();
  }

  function renderEvents() {
    const el = document.getElementById('sghv119-owner-events');
    if (!el) return;
    el.innerHTML = state.events.length ? state.events.map(e =>
      `<article class="sghv119-event"><b>${esc(e.what || e.event_type || 'observation')}</b>` +
      `<time>${esc(e.timestamp)}</time>` +
      `<div>WHO: ${esc(e.machine_agent)} · MODEL: ${esc(e.model_id)}</div>` +
      `<div>WHERE: ${esc(e.repository)} @ ${esc(e.branch)}</div>` +
      `<div>WHY: ${esc(e.why || 'runtime observation')}</div>` +
      `<div>HOW: ${esc(e.how || 'observed by local UI')}</div>` +
      `<div>RESULT: ${esc(e.result || 'observed')}</div></article>`
    ).join('') : '<div class="sghv119-empty">No observed events yet.</div>';
  }

  function createPanel() {
    const style = document.createElement('style');
    style.textContent = `
      #sghv119-owner-panel{position:fixed;right:12px;bottom:12px;width:390px;max-width:calc(100vw - 24px);height:430px;max-height:70vh;z-index:2147483647;background:#071024;color:#e6eef8;border:1px solid #31506b;border-radius:14px;box-shadow:0 10px 35px rgba(0,0,0,.55);font:13px system-ui,-apple-system,BlinkMacSystemFont,sans-serif;display:flex;flex-direction:column;overflow:hidden}
      #sghv119-owner-panel header{display:flex;align-items:center;gap:8px;padding:10px 12px;border-bottom:1px solid #234;cursor:move;user-select:none}
      #sghv119-owner-panel header strong{font-size:14px}.sghv119-led{width:9px;height:9px;border-radius:50%;background:#3ddc97}
      #sghv119-owner-panel button{background:#0d2032;color:#dff;border:1px solid #31506b;border-radius:7px;padding:6px 9px;font-weight:700}
      #sghv119-owner-panel .sghv119-tabs{margin-left:auto;display:flex;gap:5px}.sghv119-body{padding:10px;overflow:auto;flex:1}
      .sghv119-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px}.sghv119-kv{background:#0d1828;border:1px solid #213247;border-radius:8px;padding:8px}.sghv119-kv b{display:block;color:#8fa3b8;font-size:10px}.sghv119-event{border:1px solid #213247;background:#0d1828;border-radius:8px;padding:8px;margin:7px 0}.sghv119-event time{float:right;color:#8fa3b8;font-size:10px}.sghv119-event div{margin-top:3px;color:#b8c8d8}.sghv119-empty{color:#8fa3b8;padding:20px;text-align:center}
      @media(max-width:520px){#sghv119-owner-panel{width:calc(100vw - 16px);right:8px;bottom:8px;height:62vh}}
    `;
    document.head.appendChild(style);
    const panel = document.createElement('section');
    panel.id = 'sghv119-owner-panel';
    panel.setAttribute('aria-label','Owner transparency panel');
    panel.innerHTML = `<header id="sghv119-owner-drag"><span class="sghv119-led"></span><strong>OWNER TRANSPARENCY</strong><div class="sghv119-tabs"><button data-tab="state">State</button><button data-tab="events">5W1H</button><button id="sghv119-owner-close">×</button></div></header><div class="sghv119-body"><div id="sghv119-owner-state"><div class="sghv119-grid"><div class="sghv119-kv"><b>CHAT / UI</b>VISIBLE</div><div class="sghv119-kv"><b>NETWORK</b>${navigator.onLine ? 'ONLINE' : 'OFFLINE'}</div><div class="sghv119-kv"><b>AGENT</b>${esc(state.identity.machine_agent)}</div><div class="sghv119-kv"><b>PATH</b>${esc(state.identity.provider_path)}</div><div class="sghv119-kv"><b>MODEL</b>${esc(state.identity.model_id)}</div><div class="sghv119-kv"><b>REPO</b>${esc(state.identity.repository)}</div><div class="sghv119-kv"><b>BRANCH</b>${esc(state.identity.branch)}</div><div class="sghv119-kv"><b>PLATFORM</b>${esc(state.system.platform)}</div></div></div><div id="sghv119-owner-event-view" style="display:none"><div id="sghv119-owner-events"></div></div></div>`;
    document.body.appendChild(panel);

    panel.querySelectorAll('[data-tab]').forEach(b => b.addEventListener('click', () => {
      const events = b.dataset.tab === 'events';
      panel.querySelector('#sghv119-owner-state').style.display = events ? 'none' : 'block';
      panel.querySelector('#sghv119-owner-event-view').style.display = events ? 'block' : 'none';
    }));
    panel.querySelector('#sghv119-owner-close').addEventListener('click', () => panel.remove());

    const header = panel.querySelector('header'); let drag = false, dx = 0, dy = 0;
    header.addEventListener('pointerdown', e => { drag = true; const r = panel.getBoundingClientRect(); dx = e.clientX-r.left; dy=e.clientY-r.top; header.setPointerCapture(e.pointerId); });
    header.addEventListener('pointermove', e => { if (!drag) return; panel.style.left=Math.max(0,e.clientX-dx)+'px'; panel.style.top=Math.max(0,e.clientY-dy)+'px'; panel.style.right='auto'; panel.style.bottom='auto'; });
    header.addEventListener('pointerup', () => { drag=false; });
  }

  function init() {
    createPanel();
    record({event_type:'ui_initialized', what:'Owner transparency panel initialized', result:'visible'});
    window.addEventListener('online', () => { state.system.online=true; record({event_type:'network_state',what:'Network state changed',result:'online'}); });
    window.addEventListener('offline', () => { state.system.online=false; record({event_type:'network_state',what:'Network state changed',result:'offline'}); });
  }

  window.__sghv119OwnerTransparency = {
    record,
    getState: () => structuredClone(state),
    setModel: model => { state.identity.model_id = String(model || 'unreported'); record({event_type:'model_attribution',what:'Model attribution updated',result:state.identity.model_id}); },
    init
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, {once:true}); else init();
})();

/* Local-only syntax highlighter and reversible suggestion workflow. */
(function (global) {
  'use strict';

  var KEYWORDS = /\b(const|let|var|function|return|if|else|for|while|class|def|import|from|async|await|try|except|finally|raise|new|true|false|null|undefined)\b/g;
  var state = { undo: [], redo: [], suggestions: [] };

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, function (character) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character];
    });
  }

  function highlight(source) {
    var escaped = escapeHtml(source);
    escaped = escaped.replace(/(\/\/[^\n]*|#[^\n]*)/g, '<span class="token-comment">$1</span>');
    escaped = escaped.replace(/(&quot;.*?&quot;|&#39;.*?&#39;|`.*?`)/g, '<span class="token-string">$1</span>');
    escaped = escaped.replace(/\b(\d+(?:\.\d+)?)\b/g, '<span class="token-number">$1</span>');
    escaped = escaped.replace(KEYWORDS, '<span class="token-keyword">$1</span>');
    escaped = escaped.replace(/\b([A-Za-z_$][\w$]*)(?=\s*\()/g, '<span class="token-function">$1</span>');
    return escaped || '&nbsp;';
  }

  function analyze(source) {
    var results = [];
    var lines = String(source).split('\n');
    lines.forEach(function (line, index) {
      if (/\t/.test(line)) results.push({ level: 'warn', line: index + 1, message: 'Tabs may create inconsistent indentation.', fix: 'replace-tabs' });
      if (/\s+$/.test(line)) results.push({ level: 'warn', line: index + 1, message: 'Trailing whitespace can create noisy diffs.', fix: 'trim-trailing' });
      if (/\beval\s*\(|\bexec\s*\(/.test(line)) results.push({ level: 'error', line: index + 1, message: 'Dynamic execution requires explicit review and is blocked by local policy.', fix: null });
    });
    if (/^\s*def\s+\w+\([^)]*\)\s*:\s*\S+/m.test(source)) results.push({ level: 'warn', line: 1, message: 'Function body is on the declaration line; expand it for readable review.', fix: 'expand-function' });
    return results;
  }

  function makeSuggestions(source) {
    return analyze(source).filter(function (item) { return item.fix; }).map(function (item, index) {
      return { id: item.fix + '-' + index, title: item.message, detail: 'Line ' + item.line + '. Preview the change, then Accept or Deny it.', fix: item.fix };
    });
  }

  function applyFix(source, fix) {
    if (fix === 'replace-tabs') return source.replace(/\t/g, '    ');
    if (fix === 'trim-trailing') return source.split('\n').map(function (line) { return line.replace(/\s+$/, ''); }).join('\n');
    if (fix === 'expand-function') return source.replace(/^(\s*def\s+\w+\([^)]*\):)\s+(.+)$/gm, '$1\n    $2');
    return source;
  }

  function init(root) {
    var input = root.querySelector('[data-syntax-input]');
    var preview = root.querySelector('#syntax-highlight');
    var results = root.querySelector('#syntax-results');
    var suggestions = root.querySelector('#syntax-suggestions');
    var buttons = root.querySelectorAll('[data-syntax-action]');

    function render() {
      preview.innerHTML = highlight(input.value);
      var findings = analyze(input.value);
      results.innerHTML = findings.length ? findings.map(function (item) { return '<div class="result ' + item.level + '"><strong>Line ' + item.line + '</strong> — ' + escapeHtml(item.message) + '</div>'; }).join('') : '<div class="result ok">✓ No local syntax or policy findings.</div>';
      root.querySelector('[data-syntax-action="undo"]').disabled = state.undo.length === 0;
      root.querySelector('[data-syntax-action="redo"]').disabled = state.redo.length === 0;
    }

    function renderSuggestions() {
      state.suggestions = makeSuggestions(input.value);
      suggestions.innerHTML = state.suggestions.length ? state.suggestions.map(function (item) {
        return '<div class="suggestion"><div><strong>' + escapeHtml(item.title) + '</strong><p>' + escapeHtml(item.detail) + '</p></div><div class="suggestion-actions"><button type="button" data-suggestion-accept="' + item.id + '">Accept</button><button type="button" data-suggestion-deny="' + item.id + '">Deny</button></div></div>';
      }).join('') : '<div class="result ok">No safe auto-fix suggestions available.</div>';
    }

    function accept(id) {
      var item = state.suggestions.filter(function (candidate) { return candidate.id === id; })[0];
      if (!item) return;
      var next = applyFix(input.value, item.fix);
      if (next === input.value) return;
      state.undo.push(input.value); state.redo = []; input.value = next; render(); renderSuggestions();
    }

    input.addEventListener('input', render);
    root.addEventListener('click', function (event) {
      var action = event.target.getAttribute('data-syntax-action');
      var acceptId = event.target.getAttribute('data-suggestion-accept');
      var denyId = event.target.getAttribute('data-suggestion-deny');
      if (acceptId) accept(acceptId);
      if (denyId) { state.suggestions = state.suggestions.filter(function (item) { return item.id !== denyId; }); renderSuggestions(); }
      if (action === 'check') render();
      if (action === 'suggest') renderSuggestions();
      if (action === 'undo' && state.undo.length) { state.redo.push(input.value); input.value = state.undo.pop(); render(); renderSuggestions(); }
      if (action === 'redo' && state.redo.length) { state.undo.push(input.value); input.value = state.redo.pop(); render(); renderSuggestions(); }
    });
    render();
  }

  global.SovereignSyntaxGuard = { highlight: highlight, analyze: analyze, applyFix: applyFix, init: init };
  document.addEventListener('DOMContentLoaded', function () { var panel = document.querySelector('.syntax-panel'); if (panel) init(panel); });
}(typeof window !== 'undefined' ? window : globalThis));

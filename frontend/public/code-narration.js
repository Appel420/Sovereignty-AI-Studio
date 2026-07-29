/* Framework-free Code Narration parser. Parses text only; never executes source. */
(function (global) {
  'use strict';
  var names = { js:'JavaScript', javascript:'JavaScript', ts:'TypeScript', typescript:'TypeScript', py:'Python', python:'Python', jsx:'JavaScript and JSX', tsx:'TypeScript and JSX', json:'JSON data', yaml:'YAML configuration', yml:'YAML configuration' };
  function languageName(value) { var key = String(value || '').trim().toLowerCase(); return names[key] || key || 'source code'; }
  function extractCodeBlocks(text) {
    var blocks = [], match, re = /```([^\n`]*)\n?([\s\S]*?)```/g, source = String(text || '');
    while ((match = re.exec(source))) { if (match[2].trim()) blocks.push({ language: languageName(match[1]), code: match[2].trim() }); }
    return blocks;
  }
  function containsCode(text) { var source = String(text || ''); return extractCodeBlocks(source).length > 0 || /^ {4,}\S/m.test(source) || /\b(function|class|def|const|interface)\b/.test(source); }
  function createNarration(text) {
    var source = String(text || ''), blocks = extractCodeBlocks(source), prose = source.replace(/```[^\n`]*\n?[\s\S]*?```/g, ' ').replace(/\s+/g, ' ').trim();
    var detail = blocks.map(function (block) { var lines = block.code.split('\n').filter(function (line) { return line.trim(); }); return 'The response includes a ' + block.language + ' section with ' + lines.length + ' meaningful lines.'; }).join(' ');
    return { blocks: blocks, text: (containsCode(source) ? 'This response contains source code. The narration explains behavior instead of reading symbols and indentation.' : 'This response is primarily prose.') + ' ' + detail + (prose ? ' The surrounding context says: ' + prose.slice(0, 500) + '.' : '') + ' The parser inspects text only and never executes code.' };
  }
  global.SovereignCodeNarration = { extractCodeBlocks: extractCodeBlocks, containsCode: containsCode, createNarration: createNarration, narrationText: function (text, mode) { return mode === 'read' ? String(text || '') : createNarration(text).text; } };
}(typeof window !== 'undefined' ? window : globalThis));

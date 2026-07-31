/* Local browser speech adapter. No React, provider, or network dependency. */
(function (global) {
  'use strict';
  global.SovereignCodeNarrationUI = { speak: function (text, mode) { var narration = global.SovereignCodeNarration.narrationText(text, mode || 'explain-code'); if ('speechSynthesis' in global && typeof global.SpeechSynthesisUtterance === 'function') { global.speechSynthesis.cancel(); global.speechSynthesis.speak(new global.SpeechSynthesisUtterance(narration)); } return narration; } };
}(typeof window !== 'undefined' ? window : globalThis));

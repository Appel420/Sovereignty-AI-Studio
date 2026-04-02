/**
 * ML-DSA integration point.
 *
 * In production, replace with real ML-DSA WASM module exports.
 */
export async function sign(payload) {
  const data = new TextEncoder().encode(String(payload));
  if (globalThis.crypto && globalThis.crypto.subtle) {
    const digest = await globalThis.crypto.subtle.digest('SHA-256', data);
    return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, '0')).join('');
  }
  let accum = 0;
  for (let i = 0; i < data.length; i += 1) accum = (accum + data[i] * (i + 1)) >>> 0;
  return accum.toString(16);
}

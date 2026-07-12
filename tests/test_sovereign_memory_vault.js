const assert = require('node:assert/strict');
const { webcrypto } = require('node:crypto');
global.crypto = webcrypto;
global.btoa = (value) => Buffer.from(value, 'binary').toString('base64');
global.atob = (value) => Buffer.from(value, 'base64').toString('binary');
const { Vault } = require('../assets/sovereign-memory-vault.js');

class MemoryStore {
  constructor() { this.stores = { records: new Map(), settings: new Map() }; }
  get(store, key) { return Promise.resolve(this.stores[store].get(key)); }
  put(store, value) { this.stores[store].set(value.id || value.key, structuredClone(value)); return Promise.resolve(); }
  remove(store, key) { this.stores[store].delete(key); return Promise.resolve(); }
  all(store) { return Promise.resolve([...this.stores[store].values()].map(value => structuredClone(value))); }
  clear(store) { this.stores[store].clear(); return Promise.resolve(); }
}

(async () => {
  const store = new MemoryStore();
  const vault = new Vault(store);
  await vault.unlock('correct horse battery staple');
  await vault.saveConversation('claude', 'user', 'private Claude context');
  await vault.saveConversation('grok', 'user', 'private Grok context');
  assert.deepEqual((await vault.list('private', 'claude')).map(x => x.content), ['private Claude context']);
  assert.equal((await store.all('records')).some(x => JSON.stringify(x).includes('private Claude context')), false);
  assert.equal((await vault.contextFor('claude')).some(x => x.content === 'private Grok context'), false);
  await assert.rejects(() => vault.share('claude', []), /consent/i);
  await vault.setConsent('claude', true);
  const entry = (await vault.list('private', 'claude'))[0];
  await vault.share('claude', [entry]);
  assert.equal((await vault.contextFor('claude')).filter(x => x.content === 'private Claude context').length, 2);
  await vault.setConsent('claude', false);
  assert.equal((await vault.contextFor('claude')).filter(x => x.content === 'private Claude context').length, 1);
  assert.equal((await vault.audit('claude')).some(x => x.type === 'share'), true);
  await vault.deleteModel('grok');
  assert.deepEqual(await vault.list('private', 'grok'), []);
  const encryptedExport = await vault.exportEncrypted();
  assert.equal(encryptedExport.includes('private Claude context'), false);
  assert.equal(encryptedExport.includes('"scope":"private"'), false);
  await vault.wipe();
  assert.equal((await store.all('records')).length, 0);
})().catch(error => { console.error(error); process.exitCode = 1; });

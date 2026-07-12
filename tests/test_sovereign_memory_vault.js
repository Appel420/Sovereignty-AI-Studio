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

  await vault.bindIdentity({ id: 'alice', name: 'Alice', role: 'root_admin' });
  await vault.unlock('correct horse battery staple');
  await vault.saveConversation('claude', 'user', 'private Claude context');
  await vault.saveConversation('grok', 'user', 'private Grok context');

  assert.deepEqual((await vault.list('private', 'claude')).map(x => x.content), ['private Claude context']);
  assert.equal((await store.all('records')).some(x => JSON.stringify(x).includes('private Claude context')), false);
  assert.equal((await vault.contextFor('claude')).some(x => x.content === 'private Grok context'), false);

  const claudeEntry = (await vault.list('private', 'claude'))[0];
  await assert.rejects(() => vault.share('claude', ['grok'], [claudeEntry]), /consent/i);
  await vault.setConsent('grok', true);
  const shareResult = await vault.share('claude', ['grok'], [claudeEntry]);
  assert.deepEqual(shareResult.targets, ['grok']);
  assert.equal((await vault.contextFor('grok')).filter(x => x.content === 'private Claude context').length, 1);
  await vault.setConsent('grok', false);
  assert.equal((await vault.contextFor('grok')).filter(x => x.content === 'private Claude context').length, 0);
  assert.equal((await vault.audit('claude')).some(x => x.type === 'share' && x.target === 'grok'), true);

  await vault.bindIdentity({ id: 'bob', name: 'Bob', role: 'operator' });
  await vault.unlock('correct horse battery staple');
  assert.deepEqual(await vault.list('private', 'claude'), []);
  await vault.saveConversation('claude', 'user', 'bob context');
  assert.deepEqual((await vault.list('private', 'claude')).map(x => x.content), ['bob context']);

  await vault.bindIdentity({ id: 'alice', name: 'Alice', role: 'root_admin' });
  await vault.unlock('correct horse battery staple');
  assert.deepEqual((await vault.list('private', 'claude')).map(x => x.content), ['private Claude context']);

  const encryptedExport = await vault.exportEncrypted();
  assert.equal(encryptedExport.includes('private Claude context'), false);
  assert.equal(encryptedExport.includes('bob context'), false);
  assert.equal(encryptedExport.includes('"scope":"private"'), false);

  await vault.deleteModel('grok');
  assert.deepEqual(await vault.list('private', 'grok'), []);
  await vault.wipe();
  assert.equal((await store.all('records')).length, 0);
})().catch(error => { console.error(error); process.exitCode = 1; });

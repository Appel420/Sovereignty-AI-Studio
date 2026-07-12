(function (root, factory) {
  var api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.SovereignMemoryVault = api;
}(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';

  var encoder = new TextEncoder();
  var decoder = new TextDecoder();

  function id() {
    return Date.now().toString(36) + '-' + crypto.getRandomValues(new Uint32Array(1))[0].toString(36);
  }

  function encode(bytes) {
    var binary = '';
    new Uint8Array(bytes).forEach(function (byte) { binary += String.fromCharCode(byte); });
    return btoa(binary);
  }

  function decode(value) {
    var binary = atob(value);
    var bytes = new Uint8Array(binary.length);
    for (var i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    return bytes;
  }

  function IndexedStore(name) {
    this.name = name || 'SovereignMemoryVault';
    this.db = null;
  }

  IndexedStore.prototype.open = function () {
    var self = this;
    if (self.db) return Promise.resolve(self.db);
    return new Promise(function (resolve, reject) {
      var request = indexedDB.open(self.name, 1);
      request.onupgradeneeded = function () {
        var db = request.result;
        if (!db.objectStoreNames.contains('records')) db.createObjectStore('records', { keyPath: 'id' });
        if (!db.objectStoreNames.contains('settings')) db.createObjectStore('settings', { keyPath: 'key' });
      };
      request.onsuccess = function () { self.db = request.result; resolve(self.db); };
      request.onerror = function () { reject(request.error); };
    });
  };

  IndexedStore.prototype.transaction = function (store, mode, action) {
    return this.open().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(store, mode);
        var request = action(tx.objectStore(store));
        request.onsuccess = function () { resolve(request.result); };
        request.onerror = function () { reject(request.error); };
      });
    });
  };
  IndexedStore.prototype.get = function (store, key) { return this.transaction(store, 'readonly', function (s) { return s.get(key); }); };
  IndexedStore.prototype.put = function (store, value) { return this.transaction(store, 'readwrite', function (s) { return s.put(value); }); };
  IndexedStore.prototype.remove = function (store, key) { return this.transaction(store, 'readwrite', function (s) { return s.delete(key); }); };
  IndexedStore.prototype.all = function (store) { return this.transaction(store, 'readonly', function (s) { return s.getAll(); }); };
  IndexedStore.prototype.clear = function (store) { return this.transaction(store, 'readwrite', function (s) { return s.clear(); }); };

  function Vault(store) {
    this.store = store || new IndexedStore();
    this.key = null;
    this.salt = null;
    this.sessionConsent = {};
  }

  Vault.prototype.unlock = async function (passphrase) {
    if (!passphrase || passphrase.length < 12) throw new Error('Use a vault passphrase of at least 12 characters.');
    var setting = await this.store.get('settings', 'vault-salt');
    this.salt = setting ? decode(setting.value) : crypto.getRandomValues(new Uint8Array(16));
    if (!setting) await this.store.put('settings', { key: 'vault-salt', value: encode(this.salt) });
    var material = await crypto.subtle.importKey('raw', encoder.encode(passphrase), 'PBKDF2', false, ['deriveKey']);
    this.key = await crypto.subtle.deriveKey(
      { name: 'PBKDF2', salt: this.salt, iterations: 310000, hash: 'SHA-256' },
      material, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt']
    );
    return true;
  };

  Vault.prototype.lock = function () { this.key = null; this.sessionConsent = {}; };
  Vault.prototype.requireKey = function () { if (!this.key) throw new Error('Unlock the memory vault first.'); };
  Vault.prototype.seal = async function (payload) {
    this.requireKey();
    var iv = crypto.getRandomValues(new Uint8Array(12));
    var encrypted = await crypto.subtle.encrypt({ name: 'AES-GCM', iv: iv }, this.key, encoder.encode(JSON.stringify(payload)));
    return { iv: encode(iv), ciphertext: encode(encrypted) };
  };
  Vault.prototype.open = async function (record) {
    this.requireKey();
    var plaintext = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: decode(record.iv) }, this.key, decode(record.ciphertext)
    );
    return JSON.parse(decoder.decode(plaintext));
  };
  Vault.prototype.put = async function (scope, model, payload) {
    var record = await this.seal({ scope: scope, model: model, payload: payload });
    record.id = id();
    await this.store.put('records', record);
    return record.id;
  };
  Vault.prototype.list = async function (scope, model) {
    var self = this;
    var records = await this.store.all('records');
    return Promise.all(records.map(function (record) { return self.open(record); })).then(function (items) {
      return items.filter(function (item) {
        return item.scope === scope && (!model || item.model === model);
      }).map(function (item) { return item.payload; }).sort(function (a, b) { return a.createdAt - b.createdAt; });
    });
  };
  Vault.prototype.saveConversation = function (model, role, content) {
    return this.put('private', model, { id: id(), model: model, role: role, content: content, createdAt: Date.now() });
  };
  Vault.prototype.setConsent = async function (model, allowed) {
    this.sessionConsent[model] = !!allowed;
    await this.put('audit', model, { type: 'consent', model: model, allowed: !!allowed, createdAt: Date.now() });
    return allowed;
  };
  Vault.prototype.hasConsent = async function (model) { return this.sessionConsent[model] === true; };
  Vault.prototype.share = async function (model, entries) {
    if (!await this.hasConsent(model)) throw new Error('Shared memory consent is disabled.');
    var shared = { type: 'shared-context', source: model, entries: entries, createdAt: Date.now() };
    await this.put('shared', 'collaboration', shared);
    await this.put('audit', model, { type: 'share', recipient: model, entryIds: entries.map(function (entry) { return entry.id; }), createdAt: Date.now() });
    return shared;
  };
  Vault.prototype.contextFor = async function (model, limit) {
    var privateEntries = await this.list('private', model);
    var context = privateEntries.slice(-(limit || 12));
    if (await this.hasConsent(model)) {
      var shared = await this.list('shared', 'collaboration');
      shared.slice(-1).forEach(function (event) { context = context.concat(event.entries || []); });
    }
    return context;
  };
  Vault.prototype.audit = function (model) { return this.list('audit', model); };
  Vault.prototype.deleteModel = async function (model) {
    var records = await this.store.all('records');
    var self = this;
    var decoded = await Promise.all(records.map(async function (record) { return { record: record, value: await self.open(record) }; }));
    await Promise.all(decoded.filter(function (item) { return item.value.model === model; })
      .map(function (item) { return self.store.remove('records', item.record.id); }));
  };
  Vault.prototype.exportEncrypted = async function () {
    return JSON.stringify({ version: 1, exportedAt: Date.now(), records: await this.store.all('records') });
  };
  Vault.prototype.wipe = async function () { await this.store.clear('records'); await this.store.clear('settings'); this.lock(); };

  return { Vault: Vault, IndexedStore: IndexedStore };
}));

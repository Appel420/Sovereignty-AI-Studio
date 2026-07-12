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

  function hex(bytes) {
    return Array.from(new Uint8Array(bytes)).map(function (byte) {
      return byte.toString(16).padStart(2, '0');
    }).join('');
  }

  async function digestText(value) {
    var data = typeof value === 'string' ? encoder.encode(value) : value;
    return hex(await crypto.subtle.digest('SHA-256', data));
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
    this.externalStore = !!store;
    this.baseStoreName = (store && store.name) || 'SovereignMemoryVault';
    this.store = store || new IndexedStore(this.baseStoreName);
    this.key = null;
    this.salt = null;
    this.identity = null;
    this.sessionConsent = {};
  }

  Vault.prototype.currentOwner = function () {
    return this.identity && this.identity.scopeKey ? this.identity.scopeKey : 'anonymous';
  };

  Vault.prototype.identityLabel = function () {
    return this.identity && this.identity.label ? this.identity.label : 'anonymous session';
  };

  Vault.prototype.bindIdentity = async function (identity) {
    var fallback = identity && typeof identity === 'object' ? identity : { id: identity || 'anonymous' };
    var pieces = [
      fallback.id,
      fallback.userId,
      fallback.username,
      fallback.name,
      fallback.role,
      fallback.workspace,
      fallback.company,
      fallback.badge
    ].filter(Boolean);
    var scopeKey = pieces.length ? pieces.join('|') : 'anonymous';
    var scopeHash = await digestText(scopeKey);
    var label = fallback.label || fallback.name || fallback.username || fallback.userId || fallback.id || 'anonymous session';
    var changed = !this.identity || this.identity.scopeHash !== scopeHash;
    this.identity = { scopeKey: scopeKey, scopeHash: scopeHash, label: label };
    if (!this.externalStore) {
      this.store = new IndexedStore(this.baseStoreName + '-' + scopeHash.slice(0, 24));
    }
    if (changed) this.lock();
    return { changed: changed, identity: this.identity };
  };

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

  Vault.prototype.lock = function () {
    this.key = null;
    this.salt = null;
    this.sessionConsent = {};
  };
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
    var owner = this.currentOwner();
    var record = await this.seal({ owner: owner, scope: scope, model: model, payload: payload });
    record.id = id();
    await this.store.put('records', record);
    return record.id;
  };
  Vault.prototype.list = async function (scope, model) {
    var self = this;
    var owner = this.currentOwner();
    var records = await this.store.all('records');
    return Promise.all(records.map(function (record) { return self.open(record); })).then(function (items) {
      return items.filter(function (item) {
        if (item.owner && item.owner !== owner) return false;
        return item.scope === scope && (!model || item.model === model);
      }).map(function (item) { return item.payload; }).sort(function (a, b) { return a.createdAt - b.createdAt; });
    });
  };
  Vault.prototype.auditEvent = function (model, details) {
    return this.put('audit', model || 'system', Object.assign({ createdAt: Date.now() }, details || {}));
  };
  Vault.prototype.saveConversation = async function (model, role, content) {
    var payload = { id: id(), model: model, role: role, content: content, createdAt: Date.now() };
    await this.put('private', model, payload);
    await this.auditEvent(model, { type: 'save', entryId: payload.id, role: role, visibility: 'private' });
    return payload.id;
  };
  Vault.prototype.setConsent = async function (model, allowed) {
    this.sessionConsent[model] = !!allowed;
    await this.auditEvent(model, { type: 'consent', model: model, allowed: !!allowed });
    return allowed;
  };
  Vault.prototype.hasConsent = async function (model) { return this.sessionConsent[model] === true; };
  Vault.prototype.share = async function (sourceModel, targetModels, entries) {
    var self = this;
    var targets = Array.isArray(targetModels) ? targetModels.filter(Boolean).filter(function (value, index, list) {
      return list.indexOf(value) === index;
    }) : [];
    if (!targets.length) throw new Error('Choose at least one target model before sharing memory.');
    if (!entries || !entries.length) throw new Error('No entries were selected for sharing.');
    await Promise.all(targets.map(async function (targetModel) {
      if (targetModel === sourceModel) throw new Error('Choose a different target model for collaboration memory.');
      if (!await self.hasConsent(targetModel)) throw new Error('Shared memory consent is disabled for ' + targetModel + '.');
      await self.put('shared', targetModel, {
        type: 'shared-context',
        source: sourceModel,
        target: targetModel,
        entries: entries,
        createdAt: Date.now()
      });
      await self.auditEvent(sourceModel, {
        type: 'share',
        source: sourceModel,
        target: targetModel,
        entryIds: entries.map(function (entry) { return entry.id; })
      });
    }));
    return { source: sourceModel, targets: targets.slice() };
  };
  Vault.prototype.contextFor = async function (model, limit) {
    var privateEntries = await this.list('private', model);
    var context = privateEntries.slice(-(limit || 12));
    if (await this.hasConsent(model)) {
      var shared = await this.list('shared', model);
      shared.slice(-3).forEach(function (event) { context = context.concat(event.entries || []); });
    }
    return context;
  };
  Vault.prototype.audit = function (model) { return this.list('audit', model); };
  Vault.prototype.deleteModel = async function (model) {
    var owner = this.currentOwner();
    var records = await this.store.all('records');
    var self = this;
    var decoded = await Promise.all(records.map(async function (record) { return { record: record, value: await self.open(record) }; }));
    await Promise.all(decoded.filter(function (item) {
      if (item.value.owner && item.value.owner !== owner) return false;
      if (item.value.model === model) return true;
      if (item.value.payload && item.value.payload.source === model) return true;
      if (item.value.payload && item.value.payload.target === model) return true;
      return false;
    }).map(function (item) { return self.store.remove('records', item.record.id); }));
    delete this.sessionConsent[model];
  };
  Vault.prototype.exportEncrypted = async function () {
    await this.auditEvent('system', { type: 'export', format: 'encrypted' });
    return JSON.stringify({
      version: 2,
      exportedAt: Date.now(),
      owner: this.currentOwner(),
      records: await this.store.all('records')
    });
  };
  Vault.prototype.wipe = async function () { await this.store.clear('records'); await this.store.clear('settings'); this.lock(); };

  return { Vault: Vault, IndexedStore: IndexedStore };
}));

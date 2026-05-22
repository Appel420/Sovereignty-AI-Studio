#!/usr/bin/env node
/**
 * MultiProviderTokenManager v1.1
 * Unified token & usage manager for xAI + Anthropic + OpenAI
 * With dynamic cost tracking and persistent state
 */

const fs = require('fs');
const path = require('path');

const DEFAULT_CONFIG = {
  providers: {
    xai: { base_max_tokens: 8192, max_extension_per_turn: 4096, hard_cap_tokens: 65536, auto_extend: true },
    anthropic: { base_max_tokens: 8192, max_extension_per_turn: 4096, hard_cap_tokens: 65536, auto_extend: true },
    openai: { base_max_tokens: 8192, max_extension_per_turn: 4096, hard_cap_tokens: 65536, auto_extend: true }
  },
  persist_state: true
};

const CONFIG_PATH = path.join(__dirname, 'voice_config.json');

class MultiProviderTokenManager {
  constructor(repmhl = null) {
    this.repmhl = repmhl;
    this.config = this._loadConfig();
    this.states = {};
    this.costTracker = this.config.cost_tracker || { xai: { total_spend: 0, total_tokens: 0 }, anthropic: { total_spend: 0, total_tokens: 0 }, openai: { total_spend: 0, total_tokens: 0 } };
    this.costPer1k = { xai: 0.0005, anthropic: 0.003, openai: 0.005 };
  }

  _loadConfig() {
    if (fs.existsSync(CONFIG_PATH)) {
      try {
        const data = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
        return { ...DEFAULT_CONFIG, ...data };
      } catch (e) { console.warn('Config load failed, using defaults'); }
    }
    fs.writeFileSync(CONFIG_PATH, JSON.stringify(DEFAULT_CONFIG, null, 2));
    return DEFAULT_CONFIG;
  }

  _saveConfig() {
    if (this.config.persist_state) {
      this.config.provider_states = this.states;
      this.config.cost_tracker = this.costTracker;
      fs.writeFileSync(CONFIG_PATH, JSON.stringify(this.config, null, 2));
    }
  }

  startSession(provider) {
    if (!this.config.providers[provider]) throw new Error(`Unknown provider: ${provider}`);
    if (!this.states[provider]) {
      const cfg = this.config.providers[provider];
      this.states[provider] = { token_count: 0, max_tokens: cfg.base_max_tokens, extended_count: 0 };
    }
    this._saveConfig();
    return { status: 'started', provider, max_tokens: this.states[provider].max_tokens };
  }

  consumeTokens(provider, tokens) {
    if (!this.states[provider]) throw new Error(`No active session for ${provider}`);
    const state = this.states[provider];
    state.token_count += tokens;

    let extended = false;
    const cfg = this.config.providers[provider];

    if (state.token_count > state.max_tokens && cfg.auto_extend) {
      const extension = Math.min(cfg.max_extension_per_turn, cfg.hard_cap_tokens - state.max_tokens);
      if (extension > 0) {
        state.max_tokens += extension;
        state.extended_count += 1;
        extended = true;
      }
    }

    // Dynamic cost tracking
    const costPer1k = this.costPer1k[provider] || 0.002;
    const costThisTurn = (tokens / 1000) * costPer1k;
    if (!this.costTracker[provider]) this.costTracker[provider] = { total_spend: 0, total_tokens: 0 };
    this.costTracker[provider].total_spend += costThisTurn;
    this.costTracker[provider].total_tokens += tokens;

    this._saveConfig();

    return {
      status: 'ok',
      provider,
      tokens_used: state.token_count,
      max_tokens: state.max_tokens,
      extended_this_turn: extended,
      estimated_cost_this_turn: costThisTurn,
      total_spend: this.costTracker[provider].total_spend
    };
  }

  getCostReport() {
    return this.costTracker;
  }

  endSession(provider = null) {
    if (provider && this.states[provider]) delete this.states[provider];
    this._saveConfig();
  }
}

module.exports = MultiProviderTokenManager;
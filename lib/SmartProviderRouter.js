#!/usr/bin/env node
/**
 * SmartProviderRouter v1.1
 * Context-aware + Cost-aware routing across xAI, Anthropic, OpenAI
 */

const COST_TIERS = { xai: 1.0, anthropic: 1.8, openai: 2.2 };

class SmartProviderRouter {
  constructor(tokenManager) {
    this.tm = tokenManager;
    this.priorityRules = {
      medical: ['anthropic', 'xai', 'openai'],
      education: ['anthropic', 'xai', 'openai'],
      general: ['xai', 'anthropic', 'openai'],
      coding: ['openai', 'anthropic', 'xai'],
      creative: ['anthropic', 'xai', 'openai']
    };
  }

  _getCapacity(provider) {
    const state = this.tm.states[provider];
    if (!state) return this.tm.config.providers[provider]?.base_max_tokens || 0;
    return Math.max(0, state.max_tokens - state.token_count);
  }

  routeRequest(text = '', context = 'general', useJudge = false, preferCheap = true) {
    let priorities = this.priorityRules[context] || this.priorityRules.general;

    let provider = null;
    if (preferCheap && context !== 'medical' && context !== 'education') {
      const sorted = [...priorities].sort((a, b) => (COST_TIERS[a] || 2) - (COST_TIERS[b] || 2));
      provider = sorted.find(p => this._getCapacity(p) > 512);
    } else {
      provider = priorities.find(p => this._getCapacity(p) > 512);
    }

    if (!provider) {
      provider = ['xai', 'anthropic', 'openai'].find(p => this._getCapacity(p) > 256);
    }

    if (!provider) throw new Error('All providers near capacity');

    const capacity = this._getCapacity(provider);
    const cost = COST_TIERS[provider] || 2.0;

    return {
      provider,
      reason: `Context=${context} | Capacity=${capacity} | CostTier=${cost}`,
      remaining_capacity: capacity,
      estimated_cost: cost,
      should_use_judge: useJudge && provider !== 'xai'
    };
  }

  consumeWithRouting(tokens, text = '', context = 'general', useJudge = false, preferCheap = true) {
    const decision = this.routeRequest(text, context, useJudge, preferCheap);
    if (!this.tm.states[decision.provider]) this.tm.startSession(decision.provider);
    const result = this.tm.consumeTokens(decision.provider, tokens);
    return { ...result, routed_to: decision.provider, routing_reason: decision.reason, used_judge: decision.should_use_judge };
  }
}

module.exports = SmartProviderRouter;
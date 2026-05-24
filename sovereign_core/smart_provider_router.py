#!/usr/bin/env python3
"""
SmartProviderRouter v2.0
Context-aware + Cost-aware routing with HeavyJudge as final safety gate.
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from heavy_judge import HeavyJudge

logger = logging.getLogger("SmartProviderRouter")

COST_TIERS = {
    "xai": 1.0,
    "anthropic": 1.8,
    "openai": 2.2
}


@dataclass
class RoutingDecision:
    provider: str
    reason: str
    remaining_capacity: int
    estimated_cost: float
    used_judge: bool = False


class SmartProviderRouter:
    """
    Smart router that:
    - Chooses best provider based on context + cost
    - Integrates HeavyJudge as the FINAL gate before returning output
    """

    def __init__(self, token_manager, repmhl=None):
        self.token_manager = token_manager
        self.repmhl = repmhl
        self.config = token_manager.config
        self.judge = HeavyJudge(repmhl=repmhl, token_manager=token_manager)

        self.priority_rules = {
            "medical": ["anthropic", "xai", "openai"],
            "education": ["anthropic", "xai", "openai"],
            "general": ["xai", "anthropic", "openai"],
            "coding": ["openai", "anthropic", "xai"],
        }

    def _get_provider_capacity(self, provider: str) -> int:
        state = self.token_manager.states.get(provider)
        if not state:
            cfg = self.config["providers"][provider]
            return cfg["base_max_tokens"]
        return max(0, state.max_tokens - state.token_count)

    def route_request(self, text: str, context: str = "general", prefer_cheap: bool = True) -> RoutingDecision:
        priorities = self.priority_rules.get(context, self.priority_rules["general"])

        for provider in priorities:
            if self._get_provider_capacity(provider) > 512:
                return RoutingDecision(
                    provider=provider,
                    reason=f"Best available for context={context}",
                    remaining_capacity=self._get_provider_capacity(provider),
                    estimated_cost=COST_TIERS.get(provider, 2.0)
                )

        # Fallback
        return RoutingDecision(
            provider="xai",
            reason="Fallback to xAI",
            remaining_capacity=1024,
            estimated_cost=1.0
        )

    def consume_with_routing(
        self,
        tokens: int,
        text: str = "",
        context: str = "general",
        use_judge: bool = False,
        prefer_cheap: bool = True
    ) -> Dict[str, Any]:
        """
        Main entry point.
        Routes → Calls model → Runs HeavyJudge as final gate if needed.
        """
        decision = self.route_request(text, context, prefer_cheap)

        if decision.provider not in self.token_manager.states:
            self.token_manager.start_session(decision.provider)

        # Get model output (simplified here — in real use this would call the actual model)
        model_result = self.token_manager.consume_tokens(decision.provider, tokens)
        original_output = model_result.get("output", text)  # placeholder

        used_judge = False
        judge_result = None

        # === HEAVY JUDGE AS FINAL GATE ===
        should_judge = (
            use_judge or
            context in ["medical", "education"] or
            (context == "general" and self._should_sample_judge())
        )

        if should_judge:
            judge_result = self.judge.review(
                original_output=original_output,
                context=context,
                force_judge=use_judge,
                token_manager=self.token_manager
            )
            used_judge = True
            model_result["output"] = judge_result["final_output"]
            model_result["heavy_judge_verdict"] = judge_result["verdict"]
            model_result["triggered_council"] = judge_result.get("triggered_council", False)

        model_result.update({
            "routed_to": decision.provider,
            "routing_reason": decision.reason,
            "used_judge": used_judge,
            "estimated_cost_tier": decision.estimated_cost
        })

        return model_result

    def _should_sample_judge(self) -> bool:
        """Simple 8% sampling for general queries"""
        import random
        return random.random() < 0.08
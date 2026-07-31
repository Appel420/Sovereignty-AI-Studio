"""
convergence/models -- ConvergenceResult, Tier, LayerResult
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional


class Tier(Enum):
    TIER_1 = "Tier 1 -- High Confidence (>= 0.80)"
    TIER_2 = "Tier 2 -- Strong (>= 0.65)"
    TIER_3 = "Tier 3 -- Moderate (>= 0.45)"
    TIER_4 = "Tier 4 -- Weak (< 0.45)"


@dataclass
class MotifResult:
    delta_pwm:          float            # bits; negative = disruption
    disrupted_motifs:   List[str]
    top_motif:          Optional[str]
    strength:           float            # 0-1
    motifs_evaluated:   int
    method:             str              # jaspar_pwm | fallback


@dataclass
class ChromatinResult:
    state:              str              # ChromHMM state label
    state_num:          int              # 1-15
    confidence:         float           # 0-1
    key_marks:          List[str]       # H3K4me3, H3K27ac, etc.
    gc_content:         float
    cpg_density:        float


@dataclass
class ABCResult:
    abc_score:          float            # 0-1
    target_gene:        Optional[str]
    contact_strength:   float
    activity:           float
    method:             str


@dataclass
class ConservationResult:
    conservation_score: float
    species_compared:   List[str]
    method:             str


@dataclass
class ConvergenceResult:
    # Final scores
    convergence_score:      float
    tier:                   str
    confidence:             float

    # Layer results
    motif:                  MotifResult
    chromatin:              ChromatinResult
    abc:                    ABCResult
    conservation:           ConservationResult

    # Flat fields for API / export
    motif_delta:            float
    chromatin_state:        str
    abc_score:              float
    target_gene:            Optional[str]
    disrupted_motifs:       List[str]

    # Metadata
    timestamp:              str
    sequence_hash:          str
    sequence_length:        int
    variant:                Optional[Dict]  = None
    cell_type:              Optional[str]   = None
    raw_layers:             Dict            = field(default_factory=dict)

    # v2.2 single-cell bonuses
    sc_atac_bonus:          float = 0.0
    sc_hic_bonus:           float = 0.0
    sc_rna_bonus:           float = 0.0

    @property
    def final_score_with_bonuses(self) -> float:
        return min(1.0, self.convergence_score + self.sc_atac_bonus + self.sc_hic_bonus + self.sc_rna_bonus)

    def to_dict(self) -> dict:
        return {
            "convergence_score":        self.convergence_score,
            "final_score_with_bonuses": self.final_score_with_bonuses,
            "tier":                     self.tier,
            "confidence":               self.confidence,
            "target_gene":              self.target_gene,
            "disrupted_motifs":         self.disrupted_motifs,
            "chromatin_state":          self.chromatin_state,
            "abc_score":                self.abc_score,
            "motif_delta_pwm":          self.motif_delta,
            "sc_bonuses": {
                "atac":  self.sc_atac_bonus,
                "hic":   self.sc_hic_bonus,
                "rna":   self.sc_rna_bonus,
            },
            "sequence_hash":            self.sequence_hash,
            "sequence_length":          self.sequence_length,
            "timestamp":                self.timestamp,
            "cell_type":                self.cell_type,
            "variant":                  self.variant,
        }

"""
convergence/engine.py

Sovereignty One -- Convergence Scoring Engine v2.2
Four-layer regulatory variant analysis: sequence grammar, chromatin state,
3D architecture (ABC), convergence scoring. Fully offline, air-gapped capable.

Author: Derek Appel | Sovereignty One
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, Optional

from convergence.models import ConvergenceResult, Tier
from convergence.layers.motif import JASPARMotifAnalyzer
from convergence.layers.chromatin import predict_chromatin_state
from convergence.layers.abc import calculate_abc_score
from convergence.layers.conservation import analyze_conservation
from convergence.scoring import compute_convergence, assign_tier
from convergence.utils import sequence_hash
from convergence.config import load_weights


class ConvergenceEngine:
    """
    Sovereignty One Convergence Scoring Engine v2.2

    Instantiate once, call analyze() per variant.

    Args:
        jaspar_file: Path to local JASPAR .jaspar file. If None, uses
                     6 embedded CORE matrices (CTCF, SP1, TP53, GATA1,
                     SREBP2, NF-YA). Download JASPAR2024_CORE_vertebrates.jaspar
                     from https://jaspar.elixir.lu/ for full 1,300+ matrix set.
    """

    VERSION = "2.2.0-sovereign"

    def __init__(self, jaspar_file: Optional[str] = None) -> None:
        self.weights       = load_weights()
        self.motif_engine  = JASPARMotifAnalyzer(jaspar_file)
        self._initialized  = True
        src = "file" if self.motif_engine.loaded_from_file else f"{len(self.motif_engine.motifs)} embedded"
        print(f"[ConvergenceEngine v{self.VERSION}] Initialized | Motifs: {src}")

    # ── Main entry point ──────────────────────────────────────────────────

    def analyze(
        self,
        sequence: str,
        variant:  Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConvergenceResult:
        """
        Run four-layer analysis on a DNA sequence (and optional variant).

        Args:
            sequence:  DNA string, A/T/G/C (lowercase = RepeatMasked).
                       Minimum 60 bp for meaningful analysis.
            variant:   {'position': int, 'ref': 'A', 'alt': 'G'}
            metadata:  {
                          'target_gene': str,
                          'cell_type': str,
                          'distance_bp': int,         # enhancer -> TSS
                          'h3k27ac_signal': float,    # 0-1
                          'atac_signal': float,       # 0-1
                          'hi_c_contact': float,      # 0-1
                          'histone_marks': {          # for chromatin layer
                              'H3K4me3': float,       # 0-1
                              'H3K27ac': float,
                              ...
                          }
                       }

        Returns:
            ConvergenceResult with all layer outputs and final score.
        """
        if not sequence or len(sequence) < 10:
            raise ValueError(f"Sequence too short ({len(sequence)} bp). Minimum 10 bp.")

        meta = metadata or {}

        # ── Layer 1: Sequence Grammar (JASPAR PWM) ────────────────────────
        motif_result = self.motif_engine.analyze(sequence, variant)

        # ── Layer 2: Chromatin State ──────────────────────────────────────
        histone_marks = meta.get("histone_marks")
        chromatin_result = predict_chromatin_state(sequence, histone_marks)

        # ── Layer 3: ABC Score ────────────────────────────────────────────
        abc_result = calculate_abc_score(sequence, meta)

        # ── Layer 4: Conservation ─────────────────────────────────────────
        conservation_result = analyze_conservation(
            sequence,
            phylop_bigwig = meta.get("phylop_bigwig"),
            chrom         = meta.get("chrom"),
            start         = meta.get("start"),
            end           = meta.get("end"),
        )

        # ── Convergence Scoring ────────────────────────────────────────────
        score = compute_convergence(motif_result, chromatin_result, abc_result, conservation_result)
        tier  = assign_tier(score)

        # ── v2.2 Single-cell bonuses ──────────────────────────────────────
        sc_bonuses = self.weights.get("sc_bonuses", {})
        sc_atac = sc_bonuses.get("atac_cell_type_specificity", 0.10) if meta.get("sc_atac_confirmed") else 0.0
        sc_hic  = sc_bonuses.get("hic_loop_confirmation", 0.05)       if meta.get("sc_hic_confirmed")  else 0.0
        sc_rna  = sc_bonuses.get("rna_concordance", 0.08)             if meta.get("sc_rna_confirmed")  else 0.0

        # ── Confidence: mean of normalized layer sub-scores ───────────────
        confidence = round((
            motif_result.strength +
            chromatin_result.confidence +
            min(abc_result.abc_score * 20, 1.0) +
            conservation_result.conservation_score
        ) / 4.0, 4)

        return ConvergenceResult(
            convergence_score   = score,
            tier                = tier,
            confidence          = confidence,
            motif               = motif_result,
            chromatin           = chromatin_result,
            abc                 = abc_result,
            conservation        = conservation_result,
            motif_delta         = motif_result.delta_pwm,
            chromatin_state     = chromatin_result.state,
            abc_score           = abc_result.abc_score,
            target_gene         = abc_result.target_gene,
            disrupted_motifs    = motif_result.disrupted_motifs,
            timestamp           = datetime.now(timezone.utc).isoformat(),
            sequence_hash       = sequence_hash(sequence),
            sequence_length     = len(sequence),
            variant             = variant,
            cell_type           = meta.get("cell_type"),
            sc_atac_bonus       = sc_atac,
            sc_hic_bonus        = sc_hic,
            sc_rna_bonus        = sc_rna,
            raw_layers = {
                "motif":        motif_result,
                "chromatin":    chromatin_result,
                "abc":          abc_result,
                "conservation": conservation_result,
            }
        )

    def batch_analyze(self, variants: list) -> list:
        """
        Analyze a list of {'sequence': str, 'variant': dict, 'metadata': dict} dicts.
        Returns list of ConvergenceResult.
        """
        results = []
        for i, item in enumerate(variants):
            try:
                r = self.analyze(
                    item["sequence"],
                    variant  = item.get("variant"),
                    metadata = item.get("metadata"),
                )
                results.append(r)
            except Exception as e:
                print(f"[ConvergenceEngine] batch item {i} failed: {e}")
                results.append(None)
        return results

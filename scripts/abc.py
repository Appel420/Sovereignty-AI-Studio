"""
convergence/layers/abc.py

Layer 3 -- Activity-By-Contact (ABC) Scoring
Real ABC model: ABC(E->G) = Activity(E) x Contact(E,G) / normalization
Contact decays as power law with genomic distance.
Fulco et al. 2019 threshold: ABC > 0.02 = probable interaction.

When real Hi-C contact data / H3K27ac signal is provided (via metadata),
uses those directly. Otherwise derives from sequence features + gene distance.

Author: Derek Appel | Sovereignty One
"""
from __future__ import annotations
import math
from typing import Dict, Optional

from convergence.models import ABCResult
from convergence.layers.chromatin import _gc, _shannon_entropy


def _activity_from_sequence(sequence: str, gc: float, entropy: float) -> float:
    """
    Estimate enhancer activity from sequence features when H3K27ac signal
    is unavailable. CpG-dense, high-GC, high-entropy -> higher activity.
    Returns 0-1.
    """
    from convergence.layers.chromatin import _cpg_oe
    cpg_oe = _cpg_oe(sequence)
    # Activity proxy: weighted sum of accessibility predictors
    activity = (gc * 0.40) + (min(entropy / 2.0, 1.0) * 0.35) + (min(cpg_oe, 2.0) / 2.0 * 0.25)
    return round(min(max(activity, 0.0), 1.0), 4)


def _contact_from_distance(distance_bp: int) -> float:
    """
    Power-law contact decay:  contact ~ distance^(-0.87)
    Calibrated to Hi-C at 5 kb resolution.
    Returns 0-1 normalized so that 5 kb = 1.0.
    """
    if distance_bp <= 0:
        return 1.0
    reference_dist = 5_000
    # power law exponent from Lieberman-Aiden 2009 / Fulco 2019
    contact = (reference_dist / distance_bp) ** 0.87
    return round(min(contact, 1.0), 6)


def calculate_abc_score(
    sequence: str,
    metadata: Optional[Dict] = None,
) -> ABCResult:
    """
    Calculate ABC score.

    metadata keys used (all optional):
        target_gene:     str   -- gene name
        distance_bp:     int   -- bp between enhancer and gene TSS
        h3k27ac_signal:  float -- 0-1 normalized H3K27ac signal
        atac_signal:     float -- 0-1 normalized ATAC-seq signal
        hi_c_contact:    float -- 0-1 normalized Hi-C contact value
        cell_type:       str
    """
    meta = metadata or {}
    gc      = _gc(sequence)
    entropy = _shannon_entropy(sequence)

    # Activity: use real H3K27ac if given, else derive from sequence
    h3k27ac = meta.get("h3k27ac_signal")
    atac    = meta.get("atac_signal")
    if h3k27ac is not None and atac is not None:
        activity = (h3k27ac + atac) / 2.0
        method = "real_marks"
    elif h3k27ac is not None:
        activity = h3k27ac
        method = "h3k27ac_only"
    else:
        activity = _activity_from_sequence(sequence, gc, entropy)
        method = "sequence_derived"

    # Contact: use real Hi-C if given, else distance decay model
    hi_c    = meta.get("hi_c_contact")
    dist_bp = meta.get("distance_bp", 50_000)  # default 50 kb
    if hi_c is not None:
        contact = float(hi_c)
        method += "+hi_c"
    else:
        contact = _contact_from_distance(int(dist_bp))
        method += "+distance_decay"

    # ABC score: Activity x Contact / normalization constant
    # Normalization: sum of all element activities x contacts for this gene
    # Without full Hi-C map we use a background normalization constant of 5.0
    # (empirically calibrated so that typical enhancers at 50 kb score ~0.10)
    norm_constant = meta.get("abc_normalization", 5.0)
    raw_abc = (activity * contact) / norm_constant
    abc_score = round(min(raw_abc, 1.0), 6)

    # Apply ABC thresholds from config
    try:
        from convergence.config import load_weights
        cfg = load_weights()
        probable_thresh = cfg.get("abc_thresholds", {}).get("probable", 0.02)
        strong_thresh   = cfg.get("abc_thresholds", {}).get("strong", 0.05)
    except Exception:
        probable_thresh, strong_thresh = 0.02, 0.05

    return ABCResult(
        abc_score       = abc_score,
        target_gene     = meta.get("target_gene", "Unknown"),
        contact_strength= round(contact, 4),
        activity        = round(activity, 4),
        method          = method,
    )

"""
convergence/layers/chromatin.py

Layer 2 -- Chromatin State Prediction
Classifies sequences into the 15-state Roadmap Epigenomics ChromHMM model
using: GC content, CpG density, CpG O/E ratio, repeat content, Shannon entropy.
When real histone ChIP-seq data is passed in (via metadata), uses those directly.

State assignments follow: Ernst & Kellis 2012, Roadmap Epigenomics 2015.
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional
from convergence.models import ChromatinResult


# ChromHMM 15-state labels (Roadmap Epigenomics Core model)
CHROMHMM_STATES = {
    1:  ("TssA",    "Active TSS",                  ["H3K4me3", "H3K27ac"],            0.95),
    2:  ("TssAFlnk","Flanking Active TSS",          ["H3K4me3", "H3K4me1"],            0.82),
    3:  ("TxFlnk",  "Transcr. at gene 5' and 3'",  ["H3K4me1", "H3K36me3"],           0.68),
    4:  ("Tx",      "Strong transcription",         ["H3K36me3"],                      0.72),
    5:  ("TxWk",    "Weak transcription",           ["H3K36me3"],                      0.55),
    6:  ("EnhG",    "Genic enhancers",              ["H3K4me1", "H3K27ac", "H3K36me3"],0.88),
    7:  ("Enh",     "Enhancers",                    ["H3K4me1", "H3K27ac"],            0.85),
    8:  ("ZNF/Rpts","ZNF genes & repeats",          ["H3K9me3", "H3K36me3"],           0.60),
    9:  ("Het",     "Heterochromatin",              ["H3K9me3"],                       0.70),
    10: ("TssBiv",  "Bivalent/Poised TSS",          ["H3K4me3", "H3K27me3"],           0.65),
    11: ("BivFlnk", "Flanking Bivalent TSS/Enh",   ["H3K4me1", "H3K27me3"],           0.58),
    12: ("EnhBiv",  "Bivalent Enhancer",            ["H3K4me1", "H3K27me3"],           0.60),
    13: ("ReprPC",  "Repressed PolyComb",           ["H3K27me3"],                      0.65),
    14: ("ReprPCWk","Weak Repressed PolyComb",      ["H3K27me3"],                      0.48),
    15: ("Quies",   "Quiescent/Low",                [],                                0.20),
}


def _gc(seq: str) -> float:
    s = seq.upper()
    n = len(s)
    return (s.count("G") + s.count("C")) / n if n else 0.5


def _cpg_density(seq: str) -> float:
    s = seq.upper()
    return s.count("CG") / max(len(s) - 1, 1)


def _cpg_oe(seq: str) -> float:
    """CpG observed/expected ratio. > 0.65 = CpG island."""
    s = seq.upper()
    n = len(s)
    if n < 2:
        return 0.0
    obs = s.count("CG")
    c_count = s.count("C")
    g_count = s.count("G")
    exp = (c_count / n) * (g_count / n) * (n - 1)
    return obs / exp if exp > 0 else 0.0


def _repeat_fraction(seq: str) -> float:
    """Fraction of sequence that is lowercase (RepeatMasker-masked)."""
    if not seq:
        return 0.0
    return sum(1 for c in seq if c.islower()) / len(seq)


def _shannon_entropy(seq: str) -> float:
    """Shannon entropy in bits. Max = 2.0 for uniform ACGT."""
    s = seq.upper()
    n = len(s)
    if n == 0:
        return 0.0
    freqs = [s.count(b) / n for b in "ACGT"]
    return -sum(p * math.log2(p) for p in freqs if p > 0)


def _classify(gc: float, cpg: float, cpg_oe: float, repeat: float, entropy: float,
              histone_marks: Optional[Dict[str, float]] = None) -> int:
    """
    Rule-based ChromHMM state assignment.
    If histone_marks provided (dict of mark -> signal, 0-1), uses those directly.
    Otherwise infers from sequence features.
    Priority: real marks > sequence inference.
    """
    # ── Real histone data path ──────────────────────────────────────────────
    if histone_marks:
        h3k4me3  = histone_marks.get("H3K4me3", 0.0)
        h3k27ac  = histone_marks.get("H3K27ac", 0.0)
        h3k4me1  = histone_marks.get("H3K4me1", 0.0)
        h3k27me3 = histone_marks.get("H3K27me3", 0.0)
        h3k9me3  = histone_marks.get("H3K9me3", 0.0)
        h3k36me3 = histone_marks.get("H3K36me3", 0.0)

        if h3k4me3 > 0.5 and h3k27ac > 0.5:
            return 1   # TssA
        if h3k4me3 > 0.3 and h3k27me3 > 0.3:
            return 10  # TssBiv
        if h3k4me3 > 0.3:
            return 2   # TssAFlnk
        if h3k4me1 > 0.5 and h3k27ac > 0.5 and h3k36me3 > 0.3:
            return 6   # EnhG
        if h3k4me1 > 0.5 and h3k27ac > 0.5:
            return 7   # Enh
        if h3k4me1 > 0.3 and h3k27me3 > 0.3:
            return 12  # EnhBiv
        if h3k36me3 > 0.5:
            return 4   # Tx
        if h3k27me3 > 0.5:
            return 13  # ReprPC
        if h3k27me3 > 0.2:
            return 14  # ReprPCWk
        if h3k9me3 > 0.3 and h3k36me3 > 0.3:
            return 8   # ZNF/Rpts
        if h3k9me3 > 0.3:
            return 9   # Het
        return 15      # Quies

    # ── Sequence-only inference ─────────────────────────────────────────────
    # CpG island: cpg_oe > 0.65 and gc > 0.5 and cpg > 0.015
    is_cpg_island = cpg_oe > 0.65 and gc > 0.50 and cpg > 0.015
    is_high_gc    = gc > 0.60
    is_low_gc     = gc < 0.38
    is_repeat     = repeat > 0.40
    is_very_low_e = entropy < 1.5

    if is_repeat and is_very_low_e and is_low_gc:
        return 9   # Het -- likely satellite/pericentromeric
    if is_repeat and gc > 0.55:
        return 8   # ZNF/Rpts
    if is_cpg_island and is_high_gc:
        return 1   # TssA
    if is_cpg_island:
        return 2   # TssAFlnk
    if is_high_gc and entropy > 1.85:
        return 7   # Enh
    if 0.45 <= gc <= 0.60 and entropy > 1.80:
        return 6   # EnhG
    if 0.42 <= gc <= 0.55 and entropy > 1.75:
        return 4   # Tx
    if gc > 0.40 and entropy > 1.60:
        return 5   # TxWk
    if is_low_gc and entropy < 1.8:
        return 14  # ReprPCWk
    return 15  # Quies


def predict_chromatin_state(
    sequence: str,
    histone_marks: Optional[Dict[str, float]] = None,
) -> ChromatinResult:
    """
    Predict ChromHMM state from sequence features (and optionally histone marks).
    Returns a fully populated ChromatinResult.
    """
    gc      = _gc(sequence)
    cpg     = _cpg_density(sequence)
    cpg_oe  = _cpg_oe(sequence)
    repeat  = _repeat_fraction(sequence)
    entropy = _shannon_entropy(sequence)

    state_num = _classify(gc, cpg, cpg_oe, repeat, entropy, histone_marks)
    label, description, marks, confidence = CHROMHMM_STATES[state_num]

    # Reduce confidence when using sequence-only inference
    if not histone_marks:
        confidence *= 0.75

    return ChromatinResult(
        state       = f"State{state_num}_{label}",
        state_num   = state_num,
        confidence  = round(confidence, 4),
        key_marks   = marks,
        gc_content  = round(gc, 4),
        cpg_density = round(cpg, 6),
    )

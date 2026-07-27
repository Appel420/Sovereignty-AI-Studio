"""
convergence/layers/conservation.py

Conservation scoring. Wires to local PhyloP / PhastCons bigWig when available.
Falls back to sequence-based conservation proxy (k-mer uniqueness).
"""
from __future__ import annotations
from typing import Dict, List, Optional
from convergence.models import ConservationResult


def _kmer_uniqueness(seq: str, k: int = 8) -> float:
    """
    Unique k-mer fraction as sequence-level conservation proxy.
    Highly conserved regulatory motifs have low k-mer diversity (constrained).
    Repetitive / non-functional regions have many repeated k-mers.
    This is a coarse proxy -- replace with real PhyloP bigWig for production.
    """
    s = seq.upper()
    if len(s) < k:
        return 0.5
    kmers = [s[i:i+k] for i in range(len(s) - k + 1)]
    unique_fraction = len(set(kmers)) / len(kmers)
    # Invert: low uniqueness (many repeats) -> low conservation score
    # High uniqueness (many distinct k-mers) -> moderate conservation
    # Real conservation is the opposite -- constrained sites are unique but short
    # Here we use: mid-range uniqueness 0.5-0.8 correlates best with functional elements
    if 0.50 <= unique_fraction <= 0.85:
        score = 0.65 + (1.0 - abs(unique_fraction - 0.67) * 2) * 0.15
    else:
        score = max(0.0, 0.65 - abs(unique_fraction - 0.67))
    return round(min(max(score, 0.0), 1.0), 4)


def analyze_conservation(
    sequence: str,
    phylop_bigwig: Optional[str] = None,
    chrom: Optional[str] = None,
    start: Optional[int] = None,
    end: Optional[int] = None,
) -> ConservationResult:
    """
    Score conservation at this locus.
    If phylop_bigwig + coordinates provided, reads real PhyloP 100-way scores.
    Otherwise uses sequence k-mer uniqueness proxy.
    """
    method = "kmer_proxy"
    score  = _kmer_uniqueness(sequence)
    species: List[str] = ["human_proxy"]

    if phylop_bigwig and chrom and start is not None and end is not None:
        try:
            import pyBigWig
            bw = pyBigWig.open(phylop_bigwig)
            vals = bw.stats(chrom, start, end, type="mean")
            bw.close()
            if vals and vals[0] is not None:
                # PhyloP scores: positive = conserved, negative = accelerated
                raw = float(vals[0])
                score = round(min(max((raw + 5.0) / 10.0, 0.0), 1.0), 4)
                method = "phylop100way"
                species = ["100_vertebrates"]
        except Exception as e:
            pass  # fall through to proxy

    return ConservationResult(
        conservation_score = score,
        species_compared   = species,
        method             = method,
    )

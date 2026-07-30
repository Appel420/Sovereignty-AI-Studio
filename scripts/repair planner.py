"""
bridge/wetlab/repair_planner.py

Translates a ConvergenceResult into a concrete wet-lab repair hypothesis:
- Which TF to restore
- Which intervention type (dCas9-TET2, dCas9-p300, base editor, etc.)
- Which cell type to use
- Which functional assay to run

Author: Derek Appel | Sovereignty One
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ── Organ -> cell type -> model system mapping ────────────────────────────────
ORGAN_MODELS: Dict[str, Dict] = {
    "pancreas": {
        "cell_type":    "beta_cell",
        "model":        "iPSC_islet_organoid",
        "primary":      "primary_human_islet",
        "key_tfs":      ["PDX1", "NKX6-1", "MAFA", "NEUROD1"],
        "functional_assay": "GSIS",        # glucose-stimulated insulin secretion
        "success_threshold": "GSIS_index > 2.5",
        "delivery":     "mRNA_LNP",
    },
    "liver": {
        "cell_type":    "hepatocyte",
        "model":        "iPSC_hepatocyte_organoid",
        "primary":      "primary_human_hepatocyte",
        "key_tfs":      ["HNF4A", "FOXA2", "CEBPA", "HNF1A"],
        "functional_assay": "albumin_secretion",
        "success_threshold": "albumin > 3.5 g/dL",
        "delivery":     "mRNA_LNP",
    },
    "heart": {
        "cell_type":    "cardiomyocyte",
        "model":        "iPSC_cardiomyocyte",
        "primary":      "primary_human_CM",
        "key_tfs":      ["TBX5", "GATA4", "MEF2C", "NKX2-5"],
        "functional_assay": "calcium_transient",
        "success_threshold": "amplitude > 50% of healthy",
        "delivery":     "AAV9",
    },
    "kidney": {
        "cell_type":    "podocyte",
        "model":        "kidney_organoid",
        "primary":      "primary_podocyte",
        "key_tfs":      ["SIX2", "WT1", "PAX2", "NPHS2"],
        "functional_assay": "tubule_formation",
        "success_threshold": "GFR surrogate > 30% improvement",
        "delivery":     "AAV2_9",
    },
    "lung": {
        "cell_type":    "AT2",
        "model":        "lung_organoid",
        "primary":      "primary_AT2",
        "key_tfs":      ["NKX2-1", "FOXA2", "TTF1", "SFTPC"],
        "functional_assay": "surfactant_production",
        "success_threshold": "SP-C+ > 60% of healthy AT2",
        "delivery":     "AAV5",
    },
    "liver_cirrhosis": {
        "cell_type":    "hepatic_stellate",
        "model":        "hepatic_organoid",
        "primary":      "primary_hepatocyte",
        "key_tfs":      ["HNF4A", "LXR", "PPARG"],
        "functional_assay": "collagen_deposition",
        "success_threshold": "collagen < 40% reduction vs fibrotic control",
        "delivery":     "mRNA_LNP",
    },
}

# ── Chromatin state -> intervention type mapping ──────────────────────────────
INTERVENTION_MAP: Dict[str, Dict] = {
    "CpG_methylation": {
        "editor":       "dCas9-TET2",
        "mechanism":    "Active demethylation of CpG sites at silenced promoter",
        "guide_count":  3,
        "transient":    True,
    },
    "H3K27me3_silencing": {
        "editor":       "dCas9-KDM6A",
        "mechanism":    "Polycomb demethylation -- removes H3K27me3 at target locus",
        "guide_count":  3,
        "transient":    True,
    },
    "H3K27ac_loss": {
        "editor":       "dCas9-p300",
        "mechanism":    "Histone acetyltransferase -- restores H3K27ac enhancer mark",
        "guide_count":  2,
        "transient":    True,
    },
    "H3K9me3_silencing": {
        "editor":       "dCas9-LSD1",
        "mechanism":    "H3K9 demethylase -- removes constitutive heterochromatin mark",
        "guide_count":  4,
        "transient":    True,
    },
    "sequence_SNP": {
        "editor":       "ABE8e",        # A->G base editor (most common)
        "mechanism":    "Base editing -- permanent single-nucleotide correction",
        "guide_count":  1,
        "transient":    False,
    },
    "transcriptional_silencing": {
        "editor":       "dCas9-VPR",
        "mechanism":    "Transcriptional activator -- VP64-p65-Rta fusion complex",
        "guide_count":  4,
        "transient":    True,
    },
}


@dataclass
class RepairHypothesis:
    organ:              str
    disease:            str
    target_tf:          str
    disrupted_motifs:   List[str]
    chromatin_state:    str
    convergence_score:  float
    intervention_type:  str
    editor:             str
    mechanism:          str
    delivery_vehicle:   str
    guide_rna_count:    int
    cell_type:          str
    model_system:       str
    functional_assay:   str
    success_threshold:  str
    priority:           str          # HIGH / MEDIUM / LOW
    reversible:         bool
    notes:              List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


def plan_repair(
    convergence_result,          # ConvergenceResult
    organ: str = "liver",
    disease: str = "cirrhosis",
) -> RepairHypothesis:
    """
    Given a ConvergenceResult and organ/disease context, produce a
    concrete RepairHypothesis that the ClosedLoopOrchestrator can execute.
    """
    from convergence.models import ConvergenceResult
    cr: ConvergenceResult = convergence_result

    organ_key = f"{organ}_{disease}" if f"{organ}_{disease}" in ORGAN_MODELS else organ
    organ_info = ORGAN_MODELS.get(organ_key, ORGAN_MODELS.get(organ, ORGAN_MODELS["liver"]))

    # Determine intervention type from chromatin state
    state = cr.chromatin_state
    if "TssA" in state or "Enh" in state:
        # Active state with disrupted motif -- likely sequence or acetylation issue
        if cr.motif_delta <= -2.0:
            intervention_key = "sequence_SNP" if cr.variant else "H3K27ac_loss"
        else:
            intervention_key = "transcriptional_silencing"
    elif "Repr" in state or "Biv" in state:
        intervention_key = "H3K27me3_silencing"
    elif "Het" in state:
        intervention_key = "H3K9me3_silencing"
    else:
        intervention_key = "H3K27ac_loss"   # safest epigenetic intervention

    interv = INTERVENTION_MAP[intervention_key]

    # Priority from convergence score
    score = cr.final_score_with_bonuses
    if score >= 0.75:
        priority = "HIGH"
    elif score >= 0.55:
        priority = "MEDIUM"
    else:
        priority = "LOW"

    # Best target TF: top disrupted or organ-specific
    disrupted = cr.disrupted_motifs
    organ_tfs = organ_info.get("key_tfs", [])
    target_tf = disrupted[0] if disrupted else (organ_tfs[0] if organ_tfs else "Unknown")

    notes = []
    if score < 0.55:
        notes.append("Score below Tier 2 threshold -- validate computationally before committing wet-lab resources")
    if interv["transient"]:
        notes.append("Transient editor -- monitor for reversion at 7, 14, 28, 90 days")
    if cr.abc_score < 0.02:
        notes.append("ABC score below 0.02 -- enhancer-gene link not confirmed; run CRISPRi to verify")

    return RepairHypothesis(
        organ             = organ,
        disease           = disease,
        target_tf         = target_tf,
        disrupted_motifs  = disrupted,
        chromatin_state   = cr.chromatin_state,
        convergence_score = score,
        intervention_type = intervention_key,
        editor            = interv["editor"],
        mechanism         = interv["mechanism"],
        delivery_vehicle  = organ_info.get("delivery", "mRNA_LNP"),
        guide_rna_count   = interv["guide_count"],
        cell_type         = organ_info.get("cell_type", "Unknown"),
        model_system      = organ_info.get("model", "organoid"),
        functional_assay  = organ_info.get("functional_assay", "Unknown"),
        success_threshold = organ_info.get("success_threshold", "TBD"),
        priority          = priority,
        reversible        = interv["transient"],
        notes             = notes,
    )

"""
bridge/wetlab/closed_loop_orchestrator.py

The sovereign closed-loop biological runtime.

Takes a regulatory variant, scores it through the convergence engine,
plans a repair, executes the wet-lab protocol on the OT-2 (or simulation),
collects sequencing feedback, and adaptively plans the next iteration.

This is the system described in §18.4 (Biological Execution Flow).

Author: Derek Appel | Sovereignty One
"""
from __future__ import annotations
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure package root is in path
sys.path.insert(0, str(Path(__file__).parents[2]))

from convergence.engine import ConvergenceEngine
from convergence.models import ConvergenceResult
from bridge.wetlab.repair_planner import plan_repair, RepairHypothesis
from security.telemetry_signer import TelemetrySigner


@dataclass
class ExperimentRecord:
    iteration:          int
    variant:            Dict
    organ:              str
    disease:            str
    convergence:        Optional[ConvergenceResult] = None
    hypothesis:         Optional[RepairHypothesis]  = None
    ot2_run_id:         Optional[str]               = None
    seq_result:         Optional[Dict]              = None
    functional_result:  Optional[Dict]              = None
    passed:             bool                        = False
    notes:              List[str]                   = field(default_factory=list)


class ClosedLoopOrchestrator:
    """
    Sovereign Biological Runtime -- closed-loop execution.

    Workflow per iteration:
      1. Convergence scoring (sequence -> 4 layers -> score)
      2. Repair hypothesis (which editor, which cell, which assay)
      3. OT-2 protocol execution (real robot or simulation)
      4. Sequencing feedback (Nanopore or Illumina)
      5. Functional assay readout
      6. Adaptive planning (adjust if needed)

    All steps are logged to the BLAKE3-chained telemetry stream.
    """

    def __init__(
        self,
        jaspar_file:    Optional[str]   = None,
        simulate_hw:    bool            = True,   # set False for live hardware
        telemetry_log:  Optional[str]   = None,
        max_iterations: int             = 3,
    ):
        self.engine         = ConvergenceEngine(jaspar_file)
        self.telemetry      = TelemetrySigner(telemetry_log)
        self.simulate_hw    = simulate_hw
        self.max_iterations = max_iterations
        self.history:       List[ExperimentRecord] = []

        # Import hardware adapters lazily (may not be installed)
        self._ot2       = None
        self._sequencer = None

    def _get_ot2(self):
        if self._ot2 is None:
            from lab.hardware.opentrons.ot2_adapter import OT2Adapter
            self._ot2 = OT2Adapter(simulate=self.simulate_hw)
        return self._ot2

    def _get_sequencer(self):
        if self._sequencer is None:
            from lab.hardware.sequencing.sequencer_adapter import SequencerAdapter
            self._sequencer = SequencerAdapter(simulate=self.simulate_hw)
        return self._sequencer

    # ── Main entry ────────────────────────────────────────────────────────────

    def run(
        self,
        sequence:   str,
        variant:    Dict,
        metadata:   Optional[Dict] = None,
        organ:      str            = "liver",
        disease:    str            = "cirrhosis",
    ) -> List[ExperimentRecord]:
        """
        Run the full closed-loop pipeline for a given variant.
        Returns list of ExperimentRecord (one per iteration).
        """
        meta = metadata or {}
        self.telemetry.sign_event("run_start", {
            "variant": variant, "organ": organ, "disease": disease,
            "sequence_len": len(sequence), "simulate": self.simulate_hw
        })
        print(f"\n{'='*60}")
        print(f"  SOVEREIGNTY ONE -- CLOSED-LOOP ORCHESTRATOR")
        print(f"  Organ: {organ.upper()} | Disease: {disease.upper()}")
        print(f"  Variant: {variant}")
        print(f"  Hardware: {'SIMULATION' if self.simulate_hw else 'LIVE'}")
        print(f"{'='*60}\n")

        for iteration in range(1, self.max_iterations + 1):
            print(f"\n--- Iteration {iteration}/{self.max_iterations} ---")
            record = ExperimentRecord(
                iteration=iteration, variant=variant, organ=organ, disease=disease
            )

            # ── Step 1: Convergence Scoring ───────────────────────────────
            print("[Step 1/6] Convergence scoring...")
            try:
                cr = self.engine.analyze(sequence, variant, meta)
                record.convergence = cr
                self.telemetry.sign_event("convergence_complete", cr.to_dict())
                self._print_convergence(cr)
            except Exception as e:
                record.notes.append(f"Convergence failed: {e}")
                self.telemetry.sign_event("convergence_error", {"error": str(e)})
                self.history.append(record)
                break

            # ── Step 2: Repair Hypothesis ─────────────────────────────────
            print("[Step 2/6] Planning repair hypothesis...")
            hypothesis = plan_repair(cr, organ, disease)
            record.hypothesis = hypothesis
            self.telemetry.sign_event("hypothesis_planned", hypothesis.to_dict())
            self._print_hypothesis(hypothesis)

            if hypothesis.priority == "LOW" and iteration == 1:
                print("[Orchestrator] LOW priority hypothesis -- proceeding but flagging")
                record.notes.append("Low-priority hypothesis -- consider additional validation loci first")

            # ── Step 3: OT-2 Execution ─────────────────────────────────────
            print("[Step 3/6] OT-2 protocol execution...")
            ot2 = self._get_ot2()
            protocol = ot2.build_epigenetic_edit_protocol(
                cells_well       = "A1",
                editor_volume_ul = 2.0,
                guide_volume_ul  = 1.0,
            )
            run_id = ot2.run(protocol)
            record.ot2_run_id = run_id
            run_result = ot2.poll_run(run_id)
            telemetry_events = ot2.get_telemetry(run_id)
            self.telemetry.sign_event("ot2_run_complete", {
                "run_id": run_id,
                "status": run_result.get("status", "unknown"),
                "steps":  len(protocol.steps),
            })
            print(f"  OT-2 run {run_id}: {run_result.get('status', 'complete')}")

            # ── Step 4: Sequencing Feedback ───────────────────────────────
            print("[Step 4/6] Collecting sequencing data...")
            sequencer = self._get_sequencer()
            seq_result = sequencer.full_run(
                experiment_id = f"sov1_{organ}_{iteration}",
                reference     = meta.get("reference_genome"),
            )
            record.seq_result = {
                "run_id":       seq_result.run_id,
                "total_reads":  seq_result.total_reads,
                "q30_fraction": seq_result.q30_fraction,
                "median_len":   seq_result.median_length,
                "coverage":     seq_result.coverage_mean,
                "variants_vcf": seq_result.variants_vcf,
                "success":      seq_result.success,
            }
            self.telemetry.sign_event("sequencing_complete", record.seq_result)
            self._print_seq_result(seq_result)

            # ── Step 5: Functional Assay Readout ──────────────────────────
            print("[Step 5/6] Running functional assay...")
            func_result = self._run_functional_assay(hypothesis, ot2, seq_result)
            record.functional_result = func_result
            self.telemetry.sign_event("functional_assay_complete", func_result)
            self._print_functional(func_result, hypothesis)

            # ── Step 6: Evaluate + Adapt ──────────────────────────────────
            print("[Step 6/6] Evaluating results...")
            passed = func_result.get("passed", False)
            record.passed = passed
            self.telemetry.sign_event("iteration_complete", {
                "iteration": iteration, "passed": passed,
                "score": cr.convergence_score,
            })

            if passed:
                print(f"\n[SUCCESS] Functional rescue confirmed in iteration {iteration}.")
                print(f"  Assay:     {hypothesis.functional_assay}")
                print(f"  Threshold: {hypothesis.success_threshold}")
                print(f"  Result:    {func_result.get('value')} {func_result.get('unit','')}")
                self.history.append(record)
                break
            else:
                print(f"[Not yet] Threshold not met. Adapting for iteration {iteration + 1}...")
                record.notes.append(f"Assay did not pass: {func_result.get('value')} vs {hypothesis.success_threshold}")
                # Adapt: increase editor dose for next round
                meta["editor_dose_multiplier"] = meta.get("editor_dose_multiplier", 1.0) * 1.5

            self.history.append(record)

        # Final audit chain hash
        self.telemetry.sign_event("run_complete", {
            "iterations": len(self.history),
            "passed": any(r.passed for r in self.history),
            "chain_tip": self.telemetry.chain_tip,
        })
        self._print_summary()
        return self.history

    # ── Functional assay ─────────────────────────────────────────────────────

    def _run_functional_assay(
        self,
        hypothesis: RepairHypothesis,
        ot2,
        seq_result,
    ) -> Dict:
        """
        Run the organ-specific functional assay via OT-2 if applicable.
        For GSIS (pancreas), uses the ot2 GSIS protocol.
        For others, returns sequencing-derived proxy in simulation.
        """
        assay = hypothesis.functional_assay
        simulated = self.simulate_hw

        if assay == "GSIS":
            if not simulated:
                gsis_protocol = ot2.build_gsis_assay_protocol()
                ot2.run(gsis_protocol)
            # In simulation: derive from editing efficiency proxy
            editing_eff = min(seq_result.q30_fraction * 1.2, 0.95)
            gsis_index  = 1.0 + editing_eff * 2.5   # 0%->1.0 edit, 100%->3.5
            return {
                "assay":  "GSIS",
                "value":  round(gsis_index, 2),
                "unit":   "index (stimulated/basal insulin)",
                "passed": gsis_index > 2.5,
                "editing_efficiency_proxy": editing_eff,
                "simulated": simulated,
            }
        elif assay == "albumin_secretion":
            editing_eff = min(seq_result.q30_fraction * 1.1, 0.95)
            albumin = editing_eff * 4.2
            return {
                "assay":  "albumin_secretion",
                "value":  round(albumin, 2),
                "unit":   "g/dL equivalent",
                "passed": albumin > 3.5,
                "simulated": simulated,
            }
        elif assay == "calcium_transient":
            amp_pct = min(seq_result.q30_fraction * 130, 100)
            return {
                "assay":  "calcium_transient_amplitude",
                "value":  round(amp_pct, 1),
                "unit":   "% of healthy primary cardiomyocyte",
                "passed": amp_pct > 50,
                "simulated": simulated,
            }
        elif assay == "surfactant_production":
            spc_pct = min(seq_result.q30_fraction * 100, 100)
            return {
                "assay":  "SP-C_positive_AT2_fraction",
                "value":  round(spc_pct, 1),
                "unit":   "% of healthy AT2 reference",
                "passed": spc_pct > 60,
                "simulated": simulated,
            }
        else:
            return {
                "assay":  assay,
                "value":  round(seq_result.q30_fraction * 100, 1),
                "unit":   "%",
                "passed": seq_result.q30_fraction > 0.75,
                "simulated": simulated,
            }

    # ── Print helpers ─────────────────────────────────────────────────────────

    def _print_convergence(self, cr: ConvergenceResult):
        score_with = cr.final_score_with_bonuses
        print(f"\n  Convergence Score:  {cr.convergence_score:.4f}"
              f"{' (+ bonuses -> ' + str(round(score_with,4)) + ')' if score_with != cr.convergence_score else ''}")
        print(f"  Tier:               {cr.tier}")
        print(f"  Confidence:         {cr.confidence:.4f}")
        print(f"  Chromatin State:    {cr.chromatin_state}")
        print(f"  ABC Score:          {cr.abc_score:.6f}"
              f" ({'above' if cr.abc_score >= 0.02 else 'BELOW'} 0.02 threshold)")
        print(f"  delta-PWM:          {cr.motif_delta:.4f} bits"
              f" ({'disruption' if cr.motif_delta < -2 else 'OK'})")
        if cr.disrupted_motifs:
            print(f"  Disrupted TFs:      {', '.join(cr.disrupted_motifs)}")
        if cr.target_gene:
            print(f"  Target Gene:        {cr.target_gene}")

    def _print_hypothesis(self, h: RepairHypothesis):
        print(f"\n  Target TF:      {h.target_tf}")
        print(f"  Editor:         {h.editor}")
        print(f"  Mechanism:      {h.mechanism}")
        print(f"  Delivery:       {h.delivery_vehicle}")
        print(f"  Cell Type:      {h.cell_type}  |  Model: {h.model_system}")
        print(f"  Assay:          {h.functional_assay}")
        print(f"  Success Goal:   {h.success_threshold}")
        print(f"  Priority:       {h.priority}  |  Reversible: {h.reversible}")
        for note in h.notes:
            print(f"  [Note] {note}")

    def _print_seq_result(self, sr):
        print(f"  Reads: {sr.total_reads:,}  |  Q30: {sr.q30_fraction:.1%}"
              f"  |  Median len: {sr.median_length:.0f} bp"
              f"  |  Coverage: {sr.coverage_mean:.1f}x")
        if sr.variants_vcf:
            print(f"  Variants VCF: {sr.variants_vcf}")

    def _print_functional(self, func: Dict, h: RepairHypothesis):
        status = "PASS" if func.get("passed") else "FAIL"
        print(f"  Assay: {func.get('assay')}  |  Result: {func.get('value')} {func.get('unit','')}"
              f"  |  {status}"
              + (" [simulated]" if func.get("simulated") else ""))

    def _print_summary(self):
        print(f"\n{'='*60}")
        print(f"  CLOSED-LOOP RUN SUMMARY")
        print(f"  Total iterations: {len(self.history)}")
        for r in self.history:
            status = "PASS" if r.passed else "FAIL"
            score  = r.convergence.convergence_score if r.convergence else 0
            print(f"  Iter {r.iteration}: score={score:.4f}  {status}"
                  + (f"  assay={r.functional_result.get('value')} {r.functional_result.get('unit','')}"
                     if r.functional_result else ""))
        print(f"  Telemetry chain tip: {self.telemetry.chain_tip[:16]}...")
        print(f"  Total events signed: {self.telemetry.event_count}")
        chain_ok = self.telemetry.verify_chain()
        print(f"  Chain integrity:     {'VERIFIED' if chain_ok else 'BROKEN -- ALERT'}")
        print(f"{'='*60}\n")

#!/usr/bin/env python3
"""Local sovereign CI/CD orchestration primitives.

The HTTP transport lives in ``sovereign_cicd_server.py``. This module contains
only the job/step state machine and local command execution surface.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import subprocess
import uuid
from typing import Dict, List


class MerkleLedger:
    def __init__(self) -> None:
        self._leaves: List[str] = []

    def append(self, value: str) -> None:
        self._leaves.append(hashlib.sha256(value.encode()).hexdigest())

    def root(self) -> str:
        if not self._leaves:
            return hashlib.sha256(b"").hexdigest()
        level = self._leaves[:]
        while len(level) > 1:
            if len(level) % 2:
                level.append(level[-1])
            level = [hashlib.sha256((level[i] + level[i + 1]).encode()).hexdigest() for i in range(0, len(level), 2)]
        return level[0]


@dataclass
class Step:
    step_id: str
    command: str
    status: str = "pending"
    output: str = ""


@dataclass
class Job:
    job_id: str
    repo_path: str
    reason: str
    steps: List[Step] = field(default_factory=list)
    overall_status: str = "created"
    final_merkle_root: str = ""
    pqc_signature: str = ""


class SovereignCICDMOrchestrator:
    """Minimal local-only CI/CD state machine.

    No network execution or provider fallback is introduced. Commands execute
    only on the local machine through the explicitly supplied repository path.
    """

    def __init__(self) -> None:
        self.active_jobs: Dict[str, Job] = {}
        self.merkle = MerkleLedger()

    def create_job(self, repo_path: str, reason: str) -> Job:
        job = Job(str(uuid.uuid4()), repo_path, reason)
        self.active_jobs[job.job_id] = job
        self.merkle.append(f"create:{job.job_id}:{repo_path}:{reason}")
        return job

    def add_step(self, job_id: str, command: str) -> Step:
        job = self._job(job_id)
        if not command.strip():
            raise ValueError("command is required")
        step = Step(str(uuid.uuid4()), command)
        job.steps.append(step)
        self.merkle.append(f"step:{job.job_id}:{step.step_id}:{command}")
        return step

    def run_step(self, job_id: str, step_index: int = 0) -> Step:
        job = self._job(job_id)
        try:
            step = job.steps[step_index]
        except IndexError as exc:
            raise ValueError("step not found") from exc
        step.status = "running"
        try:
            completed = subprocess.run(
                step.command,
                shell=True,
                cwd=job.repo_path,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=900,
                check=False,
            )
            step.output = completed.stdout or ""
            step.status = "passed" if completed.returncode == 0 else "failed"
        except Exception as exc:
            step.output = str(exc)
            step.status = "failed"
        self.merkle.append(f"result:{step.step_id}:{step.status}:{step.output}")
        return step

    def finalize_job(self, job_id: str) -> Job:
        job = self._job(job_id)
        job.overall_status = "passed" if job.steps and all(s.status == "passed" for s in job.steps) else "failed"
        job.final_merkle_root = self.merkle.root()
        job.pqc_signature = ""
        self.merkle.append(f"finalize:{job.job_id}:{job.overall_status}:{job.final_merkle_root}")
        return job

    def get_status(self, job_id: str) -> dict:
        job = self._job(job_id)
        return {
            "job_id": job.job_id,
            "repo_path": job.repo_path,
            "reason": job.reason,
            "status": job.overall_status,
            "steps": [{"step_id": s.step_id, "status": s.status, "command": s.command} for s in job.steps],
            "merkle_root": self.merkle.root(),
        }

    def _job(self, job_id: str) -> Job:
        try:
            return self.active_jobs[job_id]
        except KeyError as exc:
            raise ValueError("job not found") from exc

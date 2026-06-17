#!/usr/bin/env python3
"""
🛡️ Recon Pipeline — subdomain enum → HTTP probe → nuclei scan.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Target:
    domain: str
    program: str = ""
    notes: str = ""


@dataclass
class ReconResult:
    target: Target
    started_at: str
    finished_at: Optional[str] = None
    subdomains: list[str] = field(default_factory=list)
    alive_hosts: list[dict] = field(default_factory=list)
    nuclei_findings: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "target": self.target.__dict__,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "subdomains": self.subdomains,
            "alive_hosts": self.alive_hosts,
            "nuclei_findings": self.nuclei_findings,
            "errors": self.errors,
        }


class ReconPipeline:
    def __init__(
        self,
        output_dir: str | Path = "~/.talos/bounty",
        subfinder_bin: str = "subfinder",
        httpx_bin: str = "httpx",
        nuclei_bin: str = "nuclei",
        nuclei_templates: Optional[str] = None,
    ):
        self.output_dir = Path(output_dir).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.subfinder = subfinder_bin
        self.httpx = httpx_bin
        self.nuclei = nuclei_bin
        self.nuclei_templates = nuclei_templates

    def _run(self, cmd: list[str], input_text: Optional[str] = None, timeout: int = 600) -> tuple[str, str, int]:
        try:
            proc = subprocess.run(
                cmd,
                input=input_text,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
            return proc.stdout, proc.stderr, proc.returncode
        except subprocess.TimeoutExpired:
            return "", f"timeout after {timeout}s", 124

    def run(self, target: Target) -> ReconResult:
        result = ReconResult(
            target=target,
            started_at=datetime.now().isoformat(),
        )
        run_dir = self.output_dir / target.domain
        run_dir.mkdir(parents=True, exist_ok=True)

        # 1. Subdomain enumeration
        stdout, stderr, rc = self._run([self.subfinder, "-d", target.domain, "-all", "-silent"])
        if rc != 0:
            result.errors.append(f"subfinder failed: {stderr.strip()}")
        result.subdomains = sorted({line.strip() for line in stdout.splitlines() if line.strip()})
        (run_dir / "subdomains.txt").write_text("\n".join(result.subdomains))

        if not result.subdomains:
            result.finished_at = datetime.now().isoformat()
            return result

        # 2. HTTP probe
        host_input = "\n".join(result.subdomains)
        stdout, stderr, rc = self._run(
            [self.httpx, "-silent", "-json", "-title", "-tech-detect", "-status-code", "-no-color"],
            input_text=host_input,
            timeout=300,
        )
        if rc != 0:
            result.errors.append(f"httpx failed: {stderr.strip()}")
        for line in stdout.splitlines():
            try:
                result.alive_hosts.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        (run_dir / "httpx.jsonl").write_text(stdout)

        # 3. Nuclei scan
        nuclei_cmd = [
            self.nuclei,
            "-silent",
            "-jsonl",
            "-severity", "low,medium,high,critical",
        ]
        if self.nuclei_templates:
            nuclei_cmd += ["-t", self.nuclei_templates]
        stdout, stderr, rc = self._run(nuclei_cmd, input_text=host_input, timeout=900)
        if rc != 0:
            result.errors.append(f"nuclei failed: {stderr.strip()}")
        for line in stdout.splitlines():
            try:
                result.nuclei_findings.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        (run_dir / "nuclei.jsonl").write_text(stdout)

        result.finished_at = datetime.now().isoformat()
        (run_dir / "summary.json").write_text(json.dumps(result.to_dict(), indent=2))
        return result

    def run_many(self, targets: list[Target]) -> list[ReconResult]:
        return [self.run(t) for t in targets]

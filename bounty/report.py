#!/usr/bin/env python3
"""
📋 Report Generator — convert nuclei JSONL findings into a markdown bounty report.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from .recon import ReconResult


class ReportGenerator:
    def __init__(self, template: Optional[str] = None):
        if template:
            self.template = Path(template).read_text()
        else:
            self.template = self._default_template()

    @staticmethod
    def _default_template() -> str:
        return """# Bug Bounty Recon Report

**Program:** {{ result.target.program or result.target.domain }}
**Domain:** {{ result.target.domain }}
**Executed:** {{ result.started_at }}
**Finished:** {{ result.finished_at or "N/A" }}

## Summary

| Metric | Value |
|--------|-------|
| Subdomains found | {{ result.subdomains | length }} |
| Alive hosts | {{ result.alive_hosts | length }} |
| Nuclei findings | {{ result.nuclei_findings | length }} |

{% if result.nuclei_findings %}
## Findings

| Severity | Host | Template | Name |
|----------|------|----------|------|
{% for f in result.nuclei_findings %}
| {{ f.info.severity | upper }} | {{ f.host }} | {{ f.template_id }} | {{ f.info.name }} |
{% endfor %}
{% else %}
## Findings
No vulnerabilities detected by nuclei in this run.
{% endif %}

{% if result.alive_hosts %}
## Alive Hosts

| URL | Status | Title | Tech |
|-----|--------|-------|------|
{% for h in result.alive_hosts %}
| {{ h.url }} | {{ h.status_code }} | {{ h.title or "" }} | {{ h.tech | join(", ") if h.tech else "" }} |
{% endfor %}
{% endif %}

{% if result.errors %}
## Errors
{% for e in result.errors %}
- {{ e }}
{% endfor %}
{% endif %}
"""

    def render(self, result: ReconResult) -> str:
        from jinja2 import Template

        # Convert dataclass to dict for template
        data = json.loads(json.dumps(result.to_dict(), default=str))
        return Template(self.template).render(result=data)

    def write(self, result: ReconResult, path: Optional[str | Path] = None) -> Path:
        if path is None:
            path = Path(f"~/.talos/bounty/{result.target.domain}/report.md").expanduser()
        else:
            path = Path(path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(result))
        return path

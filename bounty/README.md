# 🛡️ Bounty Module

Bug bounty reconnaissance pipeline untuk Talos Engine.

## Components

| File | Purpose |
|------|---------|
| `recon.py` | Pipeline: subfinder → httpx → nuclei |
| `report.py` | Generate markdown report dari hasil recon |

## Quick Start

```bash
python3 - <<'PY'
from bounty import ReconPipeline, ReportGenerator

pipeline = ReconPipeline()
result = pipeline.run(Target(domain="example.com", program="Example BB"))

report = ReportGenerator()
path = report.write(result)
print(f"Report saved: {path}")
PY
```

## Output Structure

```
~/.talos/bounty/
└── example.com/
    ├── subdomains.txt
    ├── httpx.jsonl
    ├── nuclei.jsonl
    ├── summary.json
    └── report.md
```

## Tools Required

- `subfinder`
- `httpx`
- `nuclei`

Sudah tersedia di `~/tools/bin/`.

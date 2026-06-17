# ✈️ Farm Module

Airdrop farming infrastructure untuk Talos Engine.

## Components

| File | Purpose |
|------|---------|
| `wallet.py` | Encrypted HD wallet manager (EVM) |
| `proxy.py` | Health-checked proxy rotator |
| `profile.py` | Isolated browser profile + fingerprint randomization |
| `runner.py` | Execute tasks per wallet/profile/proxy |
| `tasks/` | Contoh task airdrop |

## Quick Start

```bash
export WALLET_PASS="super-strong-password"
python3 - <<'PY'
from farm import WalletManager, ProxyRotator, ProfileManager, FarmRunner

wm = WalletManager("~/.talos/wallets.json", WALLET_PASS)
wm.create_many_evm(3, "galxe", tags=["airdrop", "galxe"])

pr = ProxyRotator()
pr.load_file("~/projects/bounty-output/proxies/alive.txt", tags=["public"])

pm = ProfileManager("~/.talos/profiles")
for w in wm.list_wallets("evm"):
    pm.create(w.label)

runner = FarmRunner(wm, pr, pm)
PY
```

## Keamanan

- Wallet file di-encrypt pakai Fernet + PBKDF2.
- Permission file `0o600`.
- Private key hanya di-derive on-demand dan tidak disimpan.

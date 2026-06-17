# ⚠️ Perhatian Penting: Talos Engine

Repo ini adalah **automation framework** yang dipakai bersama `atlas-platform`. Bisa dijalankan di VPS production maupun di codespace untuk development.

## 📑 Hubungan dengan Repo Lain

| Repo | Peran |
|------|-------|
| `talos-engine` | Framework automation (farm + bounty + tools) |
| `atlas-platform` | Provisioning VPS + Docker stack + hardening |

## 🛡️ Secrets & Data yang Tidak Di-commit

Repo ini **tidak** menyimpan:

- Wallet file: `~/.talos/wallets.json`
- Private key export (selalu di-derive dari mnemonic saat runtime)
- API key / auth provider
- File `.env` yang sudah diisi
- Browser profiles: `~/.talos/profiles/`
- Output recon & reports: `~/.talos/bounty/`

## 💾 Instalasi

```bash
# Di VPS (setelah atlas-platform setup.sh selesai)
cd /opt/atlas/projects/talos-engine
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e flowcore/

# Di Codespace
git clone https://github.com/leonidastcejorp/talos-engine.git
cd talos-engine
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 🔄 Penggunaan Module

### Farm (Airdrop)
```python
from farm import WalletManager
wm = WalletManager("~/.talos/wallets.json", password=os.environ["WALLET_PASS"])
wallet = wm.create_evm(label="galxe-01", tags=["galxe"])
```

### Bounty (Recon)
```python
from bounty import ReconPipeline
pipeline = ReconPipeline("~/.talos/bounty")
result = await pipeline.run("hackerone.com/program")
```

## ⚠️ Hal yang Perlu Diperhatikan

1. **Playwright browser** harus terinstall. Di VPS hasil `setup.sh` sudah include. Di codespace jalankan:
   ```bash
   playwright install chromium
   ```
2. **Go security tools** (`nuclei`, `subfinder`, `httpx`) harus ada di `$PATH`. `setup.sh` sudah install.
3. **Proxy pool** di `farm/proxy.py` membaca dari file teks. Pastikan file proxy tersedia atau scrape ulang.
4. **Wallet manager** menggunakan enkripsi Fernet + PBKDF2. **Jangan lupa password** — tidak ada cara recovery.

## 📋 Development vs Production

| Environment | Beda penggunaan |
|-------------|-----------------|
| Codespace | Cukup untuk coding & test tanpa browser UI |
| VPS | Jalankan farm/bounty sebenarnya dengan cron/systemd |

## 📤 Push ke GitHub

Repo ini aman untuk di-push karena tidak mengandung secret. Selalu periksa `git diff` sebelum commit kalau menambahkan file wallet atau `.env` secara tidak sengaja.

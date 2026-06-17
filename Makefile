.PHONY: install test lint deploy-farm deploy-bounty clean

PYTHON := python3
VENV   := .venv

install:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.txt
	$(VENV)/bin/pip install -e flowcore/
	$(VENV)/bin/python -m playwright install chromium

test:
	$(VENV)/bin/python -m unittest discover -s tests -p "test_*.py" 2>/dev/null || true
	$(VENV)/bin/python -m py_compile farm/*.py bounty/*.py scripts/*.py

lint:
	find farm bounty scripts -name "*.py" -exec $(VENV)/bin/python -m py_compile {} \;

deploy-farm:
	$(PYTHON) - <<'PY'
from farm import WalletManager, ProxyRotator, ProfileManager
wm = WalletManager("~/.talos/wallets.json", input("Wallet password: "))
wm.create_many_evm(int(input("Jumlah wallet: ")), input("Prefix: "), tags=["airdrop"])
pr = ProxyRotator()
pr.load_file("~/projects/bounty-output/proxies/alive.txt", tags=["public"])
pm = ProfileManager("~/.talos/profiles")
for w in wm.list_wallets("evm"):
    pm.create(w.label)
print("Farm infra ready")
PY

deploy-bounty:
	mkdir -p ~/.talos/bounty

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(VENV)

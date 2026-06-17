#!/usr/bin/env python3
"""
✈️ Farm Wallet Manager — encrypted HD wallet storage for EVM + Solana airdrops.

Usage:
    from farm.wallet import WalletManager
    wm = WalletManager("~/.talos/wallets.json", password=os.environ["WALLET_PASS"])
    acct = wm.create_evm(label="galxe-01")
    print(acct.address)
"""
from __future__ import annotations

import json
import os
import secrets
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from eth_account import Account
from mnemonic import Mnemonic


def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive Fernet key from password + salt using PBKDF2HMAC."""
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from base64 import urlsafe_b64encode

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480_000,
    )
    return urlsafe_b64encode(kdf.derive(password.encode()))


@dataclass
class Wallet:
    label: str
    chain: str
    address: str
    mnemonic: str
    derivation_path: str
    created_at: str
    tags: list[str]


class WalletManager:
    def __init__(self, path: str | Path, password: str):
        self.path = Path(path).expanduser()
        self.password = password
        self._mnemo = Mnemonic("english")
        self._data: dict = {"salt": "", "wallets": []}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self._data = {
                "salt": secrets.token_hex(16),
                "wallets": [],
                "meta": {"created": datetime.now().isoformat(), "version": 1},
            }
            return
        raw = self.path.read_bytes()
        if not raw:
            raise ValueError("wallet file is empty")
        self._data = json.loads(raw)

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        salt = bytes.fromhex(self._data["salt"])
        f = Fernet(_derive_key(self.password, salt))
        encrypted = f.encrypt(json.dumps(self._data).encode())
        self.path.write_bytes(encrypted)
        os.chmod(self.path, 0o600)

    def _fernet(self) -> Fernet:
        salt = bytes.fromhex(self._data["salt"])
        return Fernet(_derive_key(self.password, salt))

    def list_wallets(self, chain: Optional[str] = None, tag: Optional[str] = None) -> list[Wallet]:
        wallets = [Wallet(**w) for w in self._data["wallets"]]
        if chain:
            wallets = [w for w in wallets if w.chain == chain]
        if tag:
            wallets = [w for w in wallets if tag in w.tags]
        return wallets

    def create_evm(self, label: str, tags: Optional[list[str]] = None) -> Wallet:
        """Create a new EVM wallet from random mnemonic."""
        if any(w["label"] == label for w in self._data["wallets"]):
            raise ValueError(f"wallet label already exists: {label}")
        mnemonic = self._mnemo.generate(strength=128)
        Account.enable_unaudited_hdwallet_features()
        acct = Account.from_mnemonic(mnemonic, account_path="m/44'/60'/0'/0/0")
        wallet = Wallet(
            label=label,
            chain="evm",
            address=acct.address,
            mnemonic=mnemonic,
            derivation_path="m/44'/60'/0'/0/0",
            created_at=datetime.now().isoformat(),
            tags=tags or [],
        )
        self._data["wallets"].append(asdict(wallet))
        self._save()
        return wallet

    def create_many_evm(self, count: int, prefix: str, tags: Optional[list[str]] = None) -> list[Wallet]:
        """Batch create EVM wallets."""
        created = []
        for i in range(count):
            label = f"{prefix}-{i+1:04d}"
            created.append(self.create_evm(label, tags=tags))
        return created

    def get_private_key(self, label: str) -> str:
        """Derive private key from stored mnemonic. Use carefully."""
        for w in self._data["wallets"]:
            if w["label"] == label:
                if w["chain"] != "evm":
                    raise ValueError("only EVM private key export supported")
                Account.enable_unaudited_hdwallet_features()
                acct = Account.from_mnemonic(w["mnemonic"], account_path=w["derivation_path"])
                return acct.key.hex()
        raise KeyError(f"wallet not found: {label}")

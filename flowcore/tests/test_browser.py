"""
Talos Engine - Browser Module Tests

Tests for the core browser functionality, fingerprint generation,
and proxy management.
"""

import asyncio
import os
import sys
import unittest
from pathlib import Path

# Ensure flowcore is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flowcore.core.fingerprint import FingerprintGenerator, Fingerprint
from flowcore.utils.names import IdentityGenerator, Identity
from flowcore.utils.network import ProxyRecord, ProxyManager


class TestFingerprintGenerator(unittest.TestCase):
    """Test identity fingerprint generation."""

    def test_generate_returns_fingerprint(self):
        fp = FingerprintGenerator.generate()
        self.assertIsInstance(fp, Fingerprint)
        self.assertTrue(len(fp.user_agent) > 0)
        self.assertTrue(fp.platform in FingerprintGenerator.PLATFORMS)

    def test_seeded_generation_is_deterministic(self):
        fp1 = FingerprintGenerator.generate(seed="test123")
        fp2 = FingerprintGenerator.generate(seed="test123")
        self.assertEqual(fp1.user_agent, fp2.user_agent)
        self.assertEqual(fp1.platform, fp2.platform)

    def test_canvas_hash_is_generated(self):
        fp = FingerprintGenerator.generate()
        self.assertTrue(len(fp.canvas_hash) > 0)
        self.assertIsInstance(fp.canvas_hash, str)


class TestIdentityGenerator(unittest.TestCase):
    """Test synthetic identity generation."""

    def test_generate_returns_identity(self):
        identity = IdentityGenerator.generate()
        self.assertIsInstance(identity, Identity)
        self.assertTrue(len(identity.username) > 0)
        self.assertTrue("@" in identity.email)
        self.assertTrue(len(identity.password) >= 16)
        self.assertRegex(identity.birth_date, r"\d{2}/\d{2}/\d{4}")

    def test_batch_generates_correct_count(self):
        identities = IdentityGenerator.batch(10)
        self.assertEqual(len(identities), 10)

    def test_batch_identities_are_unique(self):
        identities = IdentityGenerator.batch(50)
        usernames = [i.username for i in identities]
        self.assertEqual(len(usernames), len(set(usernames)))

    def test_email_uses_valid_domains(self):
        identity = IdentityGenerator.generate()
        domain = identity.email.split("@")[1]
        self.assertIn(domain, IdentityGenerator.EMAIL_DOMAINS)


class TestProxyManager(unittest.TestCase):
    """Test proxy pool management."""

    def test_proxy_record_from_url_http(self):
        record = ProxyRecord.from_url("http://1.2.3.4:8080")
        self.assertIsNotNone(record)
        self.assertEqual(record.host, "1.2.3.4")
        self.assertEqual(record.port, 8080)
        self.assertEqual(record.protocol, "http")

    def test_proxy_record_from_url_socks5_with_auth(self):
        record = ProxyRecord.from_url("socks5://user:pass@5.6.7.8:1080")
        self.assertIsNotNone(record)
        self.assertEqual(record.host, "5.6.7.8")
        self.assertEqual(record.port, 1080)
        self.assertEqual(record.protocol, "socks5")
        self.assertEqual(record.username, "user")
        self.assertEqual(record.password, "pass")

    def test_proxy_record_from_url_no_port(self):
        record = ProxyRecord.from_url("http://10.0.0.1")
        self.assertIsNotNone(record)
        self.assertEqual(record.port, 8080)

    def test_proxy_record_from_url_invalid(self):
        record = ProxyRecord.from_url("")
        self.assertIsNone(record)

    def test_proxy_record_formatted(self):
        record = ProxyRecord.from_url("http://1.2.3.4:3128")
        self.assertEqual(record.formatted, "http://1.2.3.4:3128")

    def test_proxy_manager_load_nonexistent(self):
        manager = ProxyManager(pool_file="/tmp/nonexistent_proxies.txt")
        count = manager.load_from_file()
        self.assertEqual(count, 0)

    def test_proxy_manager_add_and_remove(self):
        manager = ProxyManager()
        manager.add_proxy("http://1.1.1.1:8080")
        manager.add_proxy("http://2.2.2.2:8080")
        self.assertEqual(len(manager._proxies), 2)
        # Mark one dead and remove
        manager._proxies[0].alive = False
        manager.remove_dead()
        self.assertEqual(len(manager._proxies), 1)

    def test_decamelize_hdfs_path(self): ...


if __name__ == "__main__":
    unittest.main(verbosity=2)

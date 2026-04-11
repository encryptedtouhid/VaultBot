"""Unit tests for device pairing."""

from __future__ import annotations

from vaultbot.pairing import DevicePairingManager, PairingCode


class TestDevicePairing:
    def test_generate_code(self) -> None:
        mgr = DevicePairingManager()
        code = mgr.generate_pairing_code()
        assert len(code) == 6
        assert code.isdigit()
        assert mgr.pending_codes_count == 1

    def test_complete_pairing(self) -> None:
        mgr = DevicePairingManager()
        code = mgr.generate_pairing_code()
        device = mgr.complete_pairing(code, "My iPhone", "ios")
        assert device is not None
        assert device.name == "My iPhone"
        assert device.active is True
        assert mgr.device_count == 1

    def test_invalid_code_fails(self) -> None:
        mgr = DevicePairingManager()
        assert mgr.complete_pairing("000000", "phone") is None

    def test_expired_code_fails(self) -> None:
        mgr = DevicePairingManager()
        code = mgr.generate_pairing_code()
        # Manually expire it
        mgr._pending_codes[code].created_at = 0  # Way in the past
        assert mgr.complete_pairing(code, "phone") is None

    def test_code_consumed_on_use(self) -> None:
        mgr = DevicePairingManager()
        code = mgr.generate_pairing_code()
        mgr.complete_pairing(code, "phone")
        # Second use should fail
        assert mgr.complete_pairing(code, "phone2") is None

    def test_revoke_device(self) -> None:
        mgr = DevicePairingManager()
        code = mgr.generate_pairing_code()
        device = mgr.complete_pairing(code, "phone")
        assert mgr.revoke_device(device.id) is True
        assert mgr.get_device(device.id).active is False

    def test_revoke_nonexistent(self) -> None:
        mgr = DevicePairingManager()
        assert mgr.revoke_device("nope") is False

    def test_remove_device(self) -> None:
        mgr = DevicePairingManager()
        code = mgr.generate_pairing_code()
        device = mgr.complete_pairing(code, "phone")
        assert mgr.remove_device(device.id) is True
        assert mgr.device_count == 0

    def test_list_devices(self) -> None:
        mgr = DevicePairingManager()
        for i in range(3):
            code = mgr.generate_pairing_code()
            mgr.complete_pairing(code, f"device{i}")
        assert len(mgr.list_devices()) == 3

    def test_list_active_only(self) -> None:
        mgr = DevicePairingManager()
        c1 = mgr.generate_pairing_code()
        c2 = mgr.generate_pairing_code()
        mgr.complete_pairing(c1, "active")
        d2 = mgr.complete_pairing(c2, "revoked")
        mgr.revoke_device(d2.id)
        assert len(mgr.list_devices(active_only=True)) == 1

    def test_active_device_count(self) -> None:
        mgr = DevicePairingManager()
        c1 = mgr.generate_pairing_code()
        c2 = mgr.generate_pairing_code()
        mgr.complete_pairing(c1, "a")
        d2 = mgr.complete_pairing(c2, "b")
        mgr.revoke_device(d2.id)
        assert mgr.active_device_count == 1

    def test_update_last_seen(self) -> None:
        mgr = DevicePairingManager()
        code = mgr.generate_pairing_code()
        device = mgr.complete_pairing(code, "phone")
        old_seen = device.last_seen
        mgr.update_last_seen(device.id)
        assert mgr.get_device(device.id).last_seen >= old_seen

    def test_cleanup_expired_codes(self) -> None:
        mgr = DevicePairingManager()
        mgr.generate_pairing_code()
        # Manually expire
        for pc in mgr._pending_codes.values():
            pc.created_at = 0
        removed = mgr.cleanup_expired_codes()
        assert removed == 1
        assert mgr.pending_codes_count == 0

    def test_pairing_code_expiry(self) -> None:
        pc = PairingCode(code="123456", created_at=0, expiry_seconds=1)
        assert pc.is_expired is True

    def test_pairing_code_not_expired(self) -> None:
        import time

        pc = PairingCode(code="123456", created_at=time.monotonic(), expiry_seconds=300)
        assert pc.is_expired is False

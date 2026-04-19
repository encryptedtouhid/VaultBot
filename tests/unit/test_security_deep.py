"""Unit tests for deep security modules."""

from __future__ import annotations

import hashlib
import textwrap
from pathlib import Path

from vaultbot.security.binary_allowlist import (
    AllowlistEntry,
    BinaryAllowlist,
    compute_sha256,
)
from vaultbot.security.channel_audit import (
    ChannelAuditor,
    ChannelConfig,
    ChannelSeverity,
)
from vaultbot.security.context_visibility import (
    ContextItem,
    ContextVisibilityFilter,
    Role,
    Scope,
)
from vaultbot.security.credential_scan import CredentialScanner
from vaultbot.security.dangerous_tool_detection import (
    DangerousPattern,
    DangerousToolDetector,
    RiskLevel,
)
from vaultbot.security.file_permissions import (
    FilePermissionChecker,
    validate_workspace_path,
)
from vaultbot.security.findings_reporter import (
    FindingSeverity,
    FindingsReporter,
)
from vaultbot.security.gateway_audit import (
    GatewayAuditor,
    GatewayConfig,
    GatewaySeverity,
)
from vaultbot.security.plugin_safety import (
    PluginSafetyAnalyzer,
    SafetyLevel,
)
from vaultbot.security.sandbox_validation import (
    SandboxSeverity,
    SandboxValidator,
)
from vaultbot.security.trust_model import (
    TrustEntity,
    TrustLevel,
    TrustStore,
)


class TestContextVisibility:
    def test_admin_sees_all_scopes(self) -> None:
        filt = ContextVisibilityFilter()
        filt.add_item(
            ContextItem(key="pub", value=1, scope=Scope.PUBLIC),
        )
        filt.add_item(
            ContextItem(key="sec", value=2, scope=Scope.SECRET),
        )
        visible = filt.visible_items(Role.ADMIN)
        assert len(visible) == 2

    def test_guest_sees_only_public(self) -> None:
        filt = ContextVisibilityFilter()
        filt.add_item(
            ContextItem(key="pub", value=1, scope=Scope.PUBLIC),
        )
        filt.add_item(
            ContextItem(key="int", value=2, scope=Scope.INTERNAL),
        )
        visible = filt.visible_items(Role.GUEST)
        assert len(visible) == 1
        assert visible[0].key == "pub"

    def test_redact_hides_unauthorized(self) -> None:
        filt = ContextVisibilityFilter()
        filt.add_item(
            ContextItem(key="pub", value="ok", scope=Scope.PUBLIC),
        )
        filt.add_item(ContextItem(
            key="secret", value="hidden", scope=Scope.SECRET,
        ))
        result = filt.redact(Role.VIEWER)
        assert result["pub"] == "ok"
        assert result["secret"] == "[REDACTED]"

    def test_can_see(self) -> None:
        filt = ContextVisibilityFilter()
        assert filt.can_see(Role.ADMIN, Scope.SECRET) is True
        assert filt.can_see(Role.GUEST, Scope.SECRET) is False

    def test_item_count_and_clear(self) -> None:
        filt = ContextVisibilityFilter()
        filt.add_items([
            ContextItem(key="a", value=1),
            ContextItem(key="b", value=2),
        ])
        assert filt.item_count == 2
        filt.clear()
        assert filt.item_count == 0


class TestDangerousToolDetection:
    def test_shell_is_critical(self) -> None:
        detector = DangerousToolDetector()
        risk = detector.assess("shell")
        assert risk.risk_level == RiskLevel.CRITICAL
        assert risk.blocked is True

    def test_safe_tool(self) -> None:
        detector = DangerousToolDetector()
        risk = detector.assess("read_file")
        assert risk.risk_level == RiskLevel.SAFE

    def test_credential_in_args(self) -> None:
        detector = DangerousToolDetector()
        risk = detector.assess(
            "config", args={"password": "abc123"},
        )
        assert risk.risk_level == RiskLevel.HIGH

    def test_is_safe_convenience(self) -> None:
        detector = DangerousToolDetector()
        assert detector.is_safe("read_file") is True
        assert detector.is_safe("exec") is False

    def test_custom_pattern(self) -> None:
        detector = DangerousToolDetector()
        detector.add_pattern(DangerousPattern(
            name="custom",
            tool_pattern=r"^my_tool$",
            risk_level=RiskLevel.MEDIUM,
            reason="Custom risk",
        ))
        risk = detector.assess("my_tool")
        assert risk.risk_level == RiskLevel.MEDIUM

    def test_check_count(self) -> None:
        detector = DangerousToolDetector()
        detector.assess("a")
        detector.assess("b")
        assert detector.check_count == 2


class TestSandboxValidation:
    def test_secure_config(self) -> None:
        validator = SandboxValidator()
        assert validator.is_secure({
            "privileged": False,
            "network_mode": "bridge",
            "read_only": True,
            "user": "1000",
        }) is True

    def test_privileged_container(self) -> None:
        validator = SandboxValidator()
        findings = validator.validate({"privileged": True})
        assert any(
            f.severity == SandboxSeverity.CRITICAL
            for f in findings
        )

    def test_host_network(self) -> None:
        validator = SandboxValidator()
        findings = validator.validate({"network_mode": "host"})
        assert any(
            f.severity == SandboxSeverity.HIGH for f in findings
        )

    def test_dangerous_capability(self) -> None:
        validator = SandboxValidator()
        findings = validator.validate({"cap_add": ["SYS_ADMIN"]})
        assert any("SYS_ADMIN" in f.title for f in findings)

    def test_sensitive_volume(self) -> None:
        validator = SandboxValidator()
        findings = validator.validate({
            "volumes": [
                "/var/run/docker.sock:/var/run/docker.sock",
            ],
        })
        assert any("docker.sock" in f.title for f in findings)

    def test_host_pid(self) -> None:
        validator = SandboxValidator()
        findings = validator.validate({"pid_mode": "host"})
        assert any("PID" in f.title for f in findings)

    def test_seccomp_disabled(self) -> None:
        validator = SandboxValidator()
        findings = validator.validate({
            "security_opt": ["seccomp=unconfined"],
        })
        assert any("Seccomp" in f.title for f in findings)

    def test_audit_count(self) -> None:
        validator = SandboxValidator()
        validator.validate({})
        validator.validate({})
        assert validator.audit_count == 2


class TestFilePermissions:
    def test_within_workspace(self, tmp_path: Path) -> None:
        checker = FilePermissionChecker(_workspace=tmp_path)
        target = tmp_path / "subdir" / "file.txt"
        result = checker.check_access(target)
        assert result.allowed is True

    def test_outside_workspace(self, tmp_path: Path) -> None:
        checker = FilePermissionChecker(_workspace=tmp_path)
        result = checker.check_access("/etc/hosts")
        assert result.allowed is False

    def test_deny_pattern(self, tmp_path: Path) -> None:
        checker = FilePermissionChecker(_workspace=tmp_path)
        target = tmp_path / ".env"
        result = checker.check_access(target)
        assert result.allowed is False

    def test_convenience_function(self, tmp_path: Path) -> None:
        target = tmp_path / "ok.txt"
        assert validate_workspace_path(tmp_path, target) is True

    def test_check_count(self, tmp_path: Path) -> None:
        checker = FilePermissionChecker(_workspace=tmp_path)
        checker.check_access(tmp_path / "a")
        checker.check_access(tmp_path / "b")
        assert checker.check_count == 2

    def test_custom_deny_pattern(self, tmp_path: Path) -> None:
        checker = FilePermissionChecker(_workspace=tmp_path)
        checker.add_deny_pattern("forbidden")
        result = checker.check_access(
            tmp_path / "forbidden_file.txt",
        )
        assert result.allowed is False

    def test_file_mode_check(self, tmp_path: Path) -> None:
        f = tmp_path / "secret.key"
        f.write_text("data")
        f.chmod(0o600)
        checker = FilePermissionChecker(_workspace=tmp_path)
        result = checker.check_file_mode(f)
        assert result.allowed is True


class TestTrustModel:
    def test_root_exists(self) -> None:
        store = TrustStore()
        assert store.entity_count == 1

    def test_register_and_verify(self) -> None:
        store = TrustStore()
        entity = TrustEntity(
            entity_id="plugin-a",
            entity_type="plugin",
            trust_level=TrustLevel.HIGH,
            granted_by="system",
        )
        assert store.register(entity) is True
        result = store.verify("plugin-a")
        assert result.valid is True
        assert result.effective_level == TrustLevel.HIGH

    def test_unknown_grantor_rejected(self) -> None:
        store = TrustStore()
        entity = TrustEntity(
            entity_id="rogue",
            entity_type="plugin",
            granted_by="nonexistent",
        )
        assert store.register(entity) is False

    def test_expired_entity(self) -> None:
        store = TrustStore()
        entity = TrustEntity(
            entity_id="old",
            entity_type="user",
            trust_level=TrustLevel.MEDIUM,
            granted_by="system",
            expires_at=1.0,
        )
        store.register(entity)
        result = store.verify("old")
        assert result.valid is False
        assert "expired" in result.reason

    def test_revoke(self) -> None:
        store = TrustStore()
        store.register(TrustEntity(
            entity_id="temp",
            entity_type="user",
            granted_by="system",
        ))
        assert store.revoke("temp") is True
        assert store.revoke("system") is False

    def test_is_trusted(self) -> None:
        store = TrustStore()
        store.register(TrustEntity(
            entity_id="usr",
            entity_type="user",
            trust_level=TrustLevel.MEDIUM,
            granted_by="system",
        ))
        assert store.is_trusted("usr", TrustLevel.LOW) is True
        assert store.is_trusted("usr", TrustLevel.FULL) is False

    def test_entity_not_found(self) -> None:
        store = TrustStore()
        result = store.verify("ghost")
        assert result.valid is False


class TestGatewayAudit:
    def test_secure_gateway(self) -> None:
        auditor = GatewayAuditor()
        config = GatewayConfig(
            tls_enabled=True,
            tls_min_version="1.3",
            auth_enabled=True,
            auth_type="bearer",
            rate_limit_enabled=True,
            rate_limit_rps=100,
        )
        assert auditor.is_secure(config) is True

    def test_no_tls(self) -> None:
        auditor = GatewayAuditor()
        config = GatewayConfig(
            tls_enabled=False, auth_enabled=True,
        )
        findings = auditor.audit(config)
        assert any(
            f.severity == GatewaySeverity.CRITICAL
            for f in findings
        )

    def test_no_auth(self) -> None:
        auditor = GatewayAuditor()
        config = GatewayConfig(
            tls_enabled=True, auth_enabled=False,
        )
        findings = auditor.audit(config)
        assert any(
            f.severity == GatewaySeverity.CRITICAL
            for f in findings
        )

    def test_wildcard_cors(self) -> None:
        auditor = GatewayAuditor()
        config = GatewayConfig(
            tls_enabled=True,
            auth_enabled=True,
            cors_origins=["*"],
        )
        findings = auditor.audit(config)
        assert any("CORS" in f.title for f in findings)

    def test_weak_tls(self) -> None:
        auditor = GatewayAuditor()
        config = GatewayConfig(
            tls_enabled=True,
            tls_min_version="1.0",
            auth_enabled=True,
        )
        findings = auditor.audit(config)
        assert any("TLS" in f.title for f in findings)

    def test_basic_auth_warning(self) -> None:
        auditor = GatewayAuditor()
        config = GatewayConfig(
            tls_enabled=True,
            auth_enabled=True,
            auth_type="basic",
        )
        findings = auditor.audit(config)
        assert any("Basic" in f.title for f in findings)

    def test_audit_count(self) -> None:
        auditor = GatewayAuditor()
        config = GatewayConfig(
            tls_enabled=True, auth_enabled=True,
        )
        auditor.audit(config)
        auditor.audit(config)
        assert auditor.audit_count == 2


class TestPluginSafety:
    def test_safe_plugin(self) -> None:
        analyzer = PluginSafetyAnalyzer()
        code = textwrap.dedent("""\
            def greet(name):
                return f"Hello, {name}!"
        """)
        report = analyzer.analyze(code, "greeter")
        assert report.is_acceptable is True
        assert report.level == SafetyLevel.SAFE

    def test_dangerous_plugin(self) -> None:
        analyzer = PluginSafetyAnalyzer()
        code = (
            "import subprocess\n"
            "import os\n"
            "os.system(\"rm -rf /\")\n"
        )
        report = analyzer.analyze(code, "evil")
        assert report.is_acceptable is False

    def test_os_system_via_ast(self) -> None:
        analyzer = PluginSafetyAnalyzer()
        code = "import os\nos.system('ls')\n"
        report = analyzer.analyze(code, "oscheck")
        assert report.score < 100
        assert len(report.issues) > 0

    def test_is_safe_to_load(self) -> None:
        analyzer = PluginSafetyAnalyzer()
        assert analyzer.is_safe_to_load("x = 1\n") is True

    def test_scan_count(self) -> None:
        analyzer = PluginSafetyAnalyzer()
        analyzer.analyze("x = 1")
        analyzer.analyze("y = 2")
        assert analyzer.scan_count == 2

    def test_syntax_error_handled(self) -> None:
        analyzer = PluginSafetyAnalyzer()
        report = analyzer.analyze(
            "def broken(:\n", "bad_syntax",
        )
        assert report.score <= 100


class TestBinaryAllowlist:
    def test_register_and_check(self) -> None:
        al = BinaryAllowlist()
        al.register(AllowlistEntry(
            name="python3",
            path="/usr/bin/python3",
            sha256="abc123",
        ))
        result = al.check("python3")
        assert result.allowed is True

    def test_unknown_binary_strict(self) -> None:
        al = BinaryAllowlist()
        result = al.check("unknown_bin")
        assert result.allowed is False

    def test_unknown_binary_permissive(self) -> None:
        al = BinaryAllowlist(_strict=False)
        result = al.check("unknown_bin")
        assert result.allowed is True

    def test_hash_verification(self, tmp_path: Path) -> None:
        f = tmp_path / "mybin"
        f.write_bytes(b"binary content")
        actual_hash = hashlib.sha256(b"binary content").hexdigest()
        al = BinaryAllowlist()
        al.register(AllowlistEntry(
            name="mybin", path=str(f), sha256=actual_hash,
        ))
        result = al.check("mybin", path=str(f))
        assert result.allowed is True
        assert result.hash_match is True

    def test_hash_mismatch(self, tmp_path: Path) -> None:
        f = tmp_path / "mybin"
        f.write_bytes(b"tampered content")
        al = BinaryAllowlist()
        al.register(AllowlistEntry(
            name="mybin", path=str(f), sha256="0000000000000000",
        ))
        result = al.check("mybin", path=str(f))
        assert result.allowed is False

    def test_compute_sha256(self, tmp_path: Path) -> None:
        f = tmp_path / "data"
        f.write_bytes(b"hello")
        expected = hashlib.sha256(b"hello").hexdigest()
        assert compute_sha256(f) == expected

    def test_remove(self) -> None:
        al = BinaryAllowlist()
        al.register(
            AllowlistEntry(name="x", path="/x", sha256="abc"),
        )
        assert al.remove("x") is True
        assert al.remove("x") is False

    def test_entry_count(self) -> None:
        al = BinaryAllowlist()
        assert al.entry_count == 0
        al.register(
            AllowlistEntry(name="a", path="/a", sha256="a"),
        )
        assert al.entry_count == 1


class TestFindingsReporter:
    def test_add_and_report(self) -> None:
        reporter = FindingsReporter()
        reporter.add(
            title="Test finding",
            severity=FindingSeverity.HIGH,
            description="A test",
        )
        report = reporter.generate_report("test-001")
        assert report.total == 1
        assert report.high_count == 1
        assert report.report_id == "test-001"

    def test_passed_with_no_findings(self) -> None:
        reporter = FindingsReporter()
        report = reporter.generate_report()
        assert report.passed is True

    def test_failed_with_critical(self) -> None:
        reporter = FindingsReporter()
        reporter.add(
            title="Crit", severity=FindingSeverity.CRITICAL,
        )
        report = reporter.generate_report()
        assert report.passed is False

    def test_cve_ids(self) -> None:
        reporter = FindingsReporter()
        finding = reporter.add(
            title="Known vuln",
            severity=FindingSeverity.HIGH,
            cve_ids=["CVE-2024-0001", "CVE-2024-0002"],
        )
        assert len(finding.cve_ids) == 2

    def test_summary(self) -> None:
        reporter = FindingsReporter()
        reporter.add(title="A", severity=FindingSeverity.HIGH)
        reporter.add(title="B", severity=FindingSeverity.HIGH)
        reporter.add(title="C", severity=FindingSeverity.LOW)
        s = reporter.summary()
        assert s["high"] == 2
        assert s["low"] == 1

    def test_clear(self) -> None:
        reporter = FindingsReporter()
        reporter.add(title="X", severity=FindingSeverity.INFO)
        reporter.clear()
        assert reporter.finding_count == 0

    def test_to_dict_list(self) -> None:
        reporter = FindingsReporter()
        reporter.add(
            title="Dict test",
            severity=FindingSeverity.MEDIUM,
        )
        dicts = reporter.to_dict_list()
        assert len(dicts) == 1
        assert dicts[0]["title"] == "Dict test"


class TestChannelAudit:
    def test_secure_channel(self) -> None:
        auditor = ChannelAuditor()
        config = ChannelConfig(
            channel_id="ch-1",
            encryption_enabled=True,
            auth_required=True,
            allowed_roles=["admin"],
            rate_limit_enabled=True,
            rate_limit_rpm=60,
            logging_enabled=True,
            max_message_length=4096,
        )
        assert auditor.is_secure(config) is True

    def test_no_encryption(self) -> None:
        auditor = ChannelAuditor()
        config = ChannelConfig(
            channel_id="ch-2",
            encryption_enabled=False,
            auth_required=True,
        )
        findings = auditor.audit(config)
        assert any(
            f.severity == ChannelSeverity.HIGH
            for f in findings
        )

    def test_no_auth(self) -> None:
        auditor = ChannelAuditor()
        config = ChannelConfig(
            channel_id="ch-3", auth_required=False,
        )
        findings = auditor.audit(config)
        assert any(
            f.severity == ChannelSeverity.CRITICAL
            for f in findings
        )

    def test_wildcard_roles(self) -> None:
        auditor = ChannelAuditor()
        config = ChannelConfig(
            channel_id="ch-4",
            auth_required=True,
            encryption_enabled=True,
            allowed_roles=["*"],
        )
        findings = auditor.audit(config)
        assert any("Wildcard" in f.title for f in findings)

    def test_webhook_no_secret(self) -> None:
        auditor = ChannelAuditor()
        config = ChannelConfig(
            channel_id="ch-5",
            platform="slack",
            webhook_secret_set=False,
            auth_required=True,
            encryption_enabled=True,
        )
        findings = auditor.audit(config)
        assert any("Webhook" in f.title for f in findings)

    def test_audit_all(self) -> None:
        auditor = ChannelAuditor()
        configs = [
            ChannelConfig(
                channel_id="ok",
                encryption_enabled=True,
                auth_required=True,
                allowed_roles=["admin"],
                rate_limit_enabled=True,
                logging_enabled=True,
                max_message_length=1024,
            ),
            ChannelConfig(
                channel_id="bad", auth_required=False,
            ),
        ]
        results = auditor.audit_all(configs)
        assert "bad" in results


class TestCredentialScan:
    def test_clean_text(self) -> None:
        scanner = CredentialScanner()
        result = scanner.scan(
            "Hello world, nothing secret here.",
        )
        assert result.has_leaks is False

    def test_detect_aws_key(self) -> None:
        scanner = CredentialScanner()
        text = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
        result = scanner.scan(text)
        assert result.has_leaks is True
        assert any(
            m.credential_type == "aws_access_key"
            for m in result.matches
        )

    def test_detect_github_pat(self) -> None:
        scanner = CredentialScanner()
        text = (
            "token: "
            "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"
        )
        result = scanner.scan(text)
        assert result.has_leaks is True

    def test_detect_private_key(self) -> None:
        scanner = CredentialScanner()
        text = "-----BEGIN RSA PRIVATE KEY-----"
        result = scanner.scan(text)
        assert result.has_leaks is True

    def test_detect_pw_assignment(self) -> None:
        scanner = CredentialScanner()
        text = 'password = "SuperSecret123!"'
        result = scanner.scan(text)
        assert result.has_leaks is True

    def test_scan_lines(self) -> None:
        scanner = CredentialScanner()
        lines = ["clean line", "AKIAIOSFODNN7EXAMPLE"]
        result = scanner.scan_lines(lines)
        assert result.leak_count >= 1

    def test_custom_pattern(self) -> None:
        scanner = CredentialScanner()
        scanner.add_pattern(
            r"CUSTOM_[A-Z]{10}",
            "custom_token",
            0.9,
        )
        result = scanner.scan("found CUSTOM_ABCDEFGHIJ here")
        assert any(
            m.credential_type == "custom_token"
            for m in result.matches
        )

    def test_has_leaks_convenience(self) -> None:
        scanner = CredentialScanner()
        assert scanner.has_leaks("nothing here") is False

    def test_scan_count(self) -> None:
        scanner = CredentialScanner()
        scanner.scan("a")
        scanner.scan("b")
        assert scanner.scan_count == 2

    def test_high_confidence_leaks(self) -> None:
        scanner = CredentialScanner()
        result = scanner.scan(
            "-----BEGIN PRIVATE KEY-----",
        )
        assert len(result.high_confidence_leaks) >= 1

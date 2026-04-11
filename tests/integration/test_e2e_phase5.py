"""End-to-end tests for Phase 5 features.

Tests the ecosystem features: plugin SDK scaffolding + test harness,
team management, marketplace entries, and dashboard SSE broadcasting.
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

import pytest

from zenbot.dashboard.server import DashboardConfig, DashboardEvent, SSEBroadcaster
from zenbot.plugins.base import PluginContext, PluginResultStatus
from zenbot.plugins.marketplace import MarketplaceEntry, ReviewStatus
from zenbot.plugins.sandbox import PluginSandbox
from zenbot.plugins.sdk import (
    PluginTestHarness,
    mock_context,
    scaffold_plugin,
    validate_manifest,
)
from zenbot.plugins.signer import PluginSigner, PluginVerifier
from zenbot.security.auth import Role
from zenbot.security.teams import Team, TeamManager

# =============================================================================
# E2E: Plugin SDK full workflow
# =============================================================================


class TestPluginSDKWorkflow:
    """Test the complete plugin development workflow: scaffold → test → sign → verify."""

    @pytest.mark.asyncio
    async def test_scaffold_test_sign_verify(self) -> None:
        """Full lifecycle: scaffold a plugin, test it, sign it, verify it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)

            # 1. Scaffold
            plugin_dir = scaffold_plugin(
                base, "greeting", "Greets the user", "developer@test.com"
            )
            assert (plugin_dir / "plugin.py").exists()
            assert (plugin_dir / "zenbot_plugin.json").exists()

            # 2. Validate manifest
            errors = validate_manifest(plugin_dir / "zenbot_plugin.json")
            assert errors == [], f"Manifest errors: {errors}"

            # 3. Load and test with harness
            spec = importlib.util.spec_from_file_location(
                "greeting_plugin", plugin_dir / "plugin.py"
            )
            assert spec is not None
            assert spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            plugin = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and hasattr(attr, "manifest")
                    and hasattr(attr, "handle")
                    and attr_name != "PluginBase"
                ):
                    plugin = attr()
                    break

            assert plugin is not None
            harness = PluginTestHarness(plugin)
            results = await harness.run_all()
            assert all(r.passed for r in results), (
                "Harness failures: "
                + ", ".join(f"{r.test_name}: {r.message}" for r in results if not r.passed)
            )

            # 4. Sign the plugin
            signer = PluginSigner.generate()
            sig = signer.sign_plugin("greeting", "1.0.0", plugin_dir)
            assert sig.plugin_name == "greeting"

            # 5. Verify the signature
            trust_dir = base / "trust"
            trust_dir.mkdir()
            verifier = PluginVerifier(trust_store_dir=trust_dir)
            verifier.add_trusted_key(signer.public_key_bytes, "dev")

            verified = verifier.verify_plugin(plugin_dir)
            assert verified is not None
            assert verified.plugin_name == "greeting"

            # 6. Execute in sandbox
            sandbox = PluginSandbox()
            ctx = PluginContext(
                user_input="Hello!",
                chat_id="chat1",
                user_id="user1",
                platform="test",
            )
            result = await sandbox.execute(plugin_dir / "plugin.py", ctx)
            assert result.status == PluginResultStatus.SUCCESS
            assert "Hello!" in result.output

    @pytest.mark.asyncio
    async def test_harness_catches_broken_plugin(self) -> None:
        """Test harness detects a plugin that crashes on handle()."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "broken"
            plugin_dir.mkdir()

            (plugin_dir / "plugin.py").write_text(
                "from zenbot.plugins.base import (\n"
                "    PluginBase, PluginContext, PluginManifest,\n"
                "    PluginResult, PluginResultStatus,\n"
                ")\n\n"
                "class BrokenPlugin(PluginBase):\n"
                "    def manifest(self):\n"
                '        return PluginManifest(name="broken", version="1.0",\n'
                '            description="x", author="x")\n\n'
                "    async def handle(self, ctx):\n"
                '        raise RuntimeError("Plugin is broken")\n'
            )

            spec = importlib.util.spec_from_file_location(
                "broken_plugin", plugin_dir / "plugin.py"
            )
            assert spec is not None
            assert spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            plugin = module.BrokenPlugin()
            harness = PluginTestHarness(plugin)
            results = await harness.run_all()

            # manifest and lifecycle should pass, handle tests should fail
            handle_results = [r for r in results if "handle" in r.test_name]
            assert any(not r.passed for r in handle_results)

    def test_mock_context_with_secrets(self) -> None:
        """Mock context properly passes secrets for plugin testing."""
        ctx = mock_context(
            "test input",
            secrets={"API_KEY": "test-key-123", "DB_URL": "localhost"},
        )
        assert ctx.secrets["API_KEY"] == "test-key-123"
        assert ctx.secrets["DB_URL"] == "localhost"
        assert ctx.user_input == "test input"


# =============================================================================
# E2E: Team management workflows
# =============================================================================


class TestTeamWorkflows:
    """Test multi-user team management end-to-end."""

    def test_create_team_add_members_check_access(self) -> None:
        """Full team setup: create, add members, verify access."""
        mgr = TeamManager()
        team = mgr.create_team("engineering", "Engineering team")

        # Add members with different roles
        team.add_member("telegram", "alice", Role.ADMIN)
        team.add_member("telegram", "bob", Role.USER)
        team.add_member("discord", "charlie", Role.USER)

        # Verify access
        assert team.is_member("telegram", "alice")
        assert team.is_admin("telegram", "alice")
        assert team.is_member("telegram", "bob")
        assert not team.is_admin("telegram", "bob")
        assert team.is_member("discord", "charlie")

        # Cross-platform isolation
        assert not team.is_member("discord", "alice")

        # Non-member
        assert not team.is_member("telegram", "eve")

    def test_team_budget_enforcement(self) -> None:
        """Team daily message budget is enforced correctly."""
        mgr = TeamManager()
        team = mgr.create_team("free-tier")
        team.max_messages_per_day = 5

        for _ in range(5):
            assert team.consume_budget()

        # 6th message exceeds budget
        assert not team.consume_budget()
        assert not team.has_budget()

        # Reset budget (simulates daily cron)
        mgr.reset_all_daily_budgets()
        assert team.has_budget()
        assert team.consume_budget()

    def test_user_in_multiple_teams(self) -> None:
        """A user can belong to multiple teams with different roles."""
        mgr = TeamManager()
        t1 = mgr.create_team("team-a")
        t2 = mgr.create_team("team-b")
        t3 = mgr.create_team("team-c")

        t1.add_member("telegram", "alice", Role.ADMIN)
        t2.add_member("telegram", "alice", Role.USER)
        # alice is not in team-c

        teams = mgr.get_user_teams("telegram", "alice")
        assert len(teams) == 2
        assert t1 in teams
        assert t2 in teams
        assert t3 not in teams

    def test_team_serialization_roundtrip(self) -> None:
        """Team data survives serialization/deserialization."""
        team = Team(name="ops", description="Operations")
        team.add_member("telegram", "admin1", Role.ADMIN)
        team.add_member("discord", "user1", Role.USER)
        team.enabled_plugins = ["weather", "calculator"]
        team.max_messages_per_day = 500
        team.settings = {"timezone": "UTC", "language": "en"}

        data = team.to_dict()
        json_str = json.dumps(data)
        restored = Team.from_dict(json.loads(json_str))

        assert restored.name == "ops"
        assert restored.description == "Operations"
        assert len(restored.members) == 2
        assert restored.enabled_plugins == ["weather", "calculator"]
        assert restored.max_messages_per_day == 500
        assert restored.settings["timezone"] == "UTC"

    def test_remove_member_and_verify(self) -> None:
        """Removing a member revokes their access."""
        team = Team(name="devs")
        team.add_member("telegram", "alice")
        assert team.is_member("telegram", "alice")

        team.remove_member("telegram", "alice")
        assert not team.is_member("telegram", "alice")


# =============================================================================
# E2E: Dashboard SSE broadcasting
# =============================================================================


class TestDashboardSSE:
    """Test the SSE event broadcasting system."""

    @pytest.mark.asyncio
    async def test_broadcast_reaches_subscriber(self) -> None:
        """Events broadcast to all subscribers."""
        broadcaster = SSEBroadcaster()
        queue = broadcaster.subscribe()

        event = DashboardEvent(
            event_type="message",
            data={"chat_id": "chat1", "text": "Hello"},
        )
        await broadcaster.broadcast(event)

        sse_data = queue.get_nowait()
        assert "event: message" in sse_data
        assert "Hello" in sse_data

    @pytest.mark.asyncio
    async def test_multiple_subscribers_receive_events(self) -> None:
        """All subscribers get the same event."""
        broadcaster = SSEBroadcaster()
        q1 = broadcaster.subscribe()
        q2 = broadcaster.subscribe()

        await broadcaster.broadcast(
            DashboardEvent(event_type="status", data={"healthy": True})
        )

        d1 = q1.get_nowait()
        d2 = q2.get_nowait()
        assert d1 == d2
        assert "healthy" in d1

    @pytest.mark.asyncio
    async def test_unsubscribed_client_stops_receiving(self) -> None:
        """Unsubscribed clients don't receive events."""
        broadcaster = SSEBroadcaster()
        queue = broadcaster.subscribe()
        broadcaster.unsubscribe(queue)

        await broadcaster.broadcast(
            DashboardEvent(event_type="test", data={})
        )
        assert queue.empty()

    @pytest.mark.asyncio
    async def test_full_queue_client_cleaned_up(self) -> None:
        """Clients with full queues are automatically removed."""
        broadcaster = SSEBroadcaster()
        queue = broadcaster.subscribe()

        # Fill the queue to capacity (100)
        for i in range(100):
            queue.put_nowait(f"filler-{i}")

        # Next broadcast should trigger cleanup
        await broadcaster.broadcast(
            DashboardEvent(event_type="overflow", data={})
        )

        # Client should be removed
        assert broadcaster.client_count == 0

    def test_event_sse_format(self) -> None:
        """SSE messages follow the correct format."""
        event = DashboardEvent(
            event_type="plugin.loaded",
            data={"name": "weather", "version": "1.0"},
        )
        sse = event.to_sse()

        lines = sse.strip().split("\n")
        assert lines[0] == "event: plugin.loaded"
        assert lines[1].startswith("data: ")

        payload = json.loads(lines[1][6:])
        assert payload["type"] == "plugin.loaded"
        assert payload["data"]["name"] == "weather"


# =============================================================================
# E2E: Marketplace entry validation
# =============================================================================


class TestMarketplaceValidation:
    """Test marketplace entry parsing and review status enforcement."""

    def test_approved_plugin_entry(self) -> None:
        entry = MarketplaceEntry.from_dict({
            "name": "weather",
            "version": "2.0.0",
            "description": "Weather lookup",
            "author": "zenbot-team",
            "review_status": "approved",
            "downloads": 5000,
            "rating": 4.5,
            "tags": ["weather", "utility"],
            "checksum": "abc123",
        })
        assert entry.review_status == ReviewStatus.APPROVED
        assert entry.downloads == 5000
        assert entry.rating == 4.5
        assert "utility" in entry.tags

    def test_rejected_plugin_entry(self) -> None:
        entry = MarketplaceEntry.from_dict({
            "name": "malware",
            "version": "1.0",
            "description": "Totally not malware",
            "author": "hacker",
            "review_status": "rejected",
        })
        assert entry.review_status == ReviewStatus.REJECTED

    def test_revoked_plugin_entry(self) -> None:
        entry = MarketplaceEntry.from_dict({
            "name": "old-plugin",
            "version": "1.0",
            "description": "Was good, now revoked",
            "author": "dev",
            "review_status": "revoked",
        })
        assert entry.review_status == ReviewStatus.REVOKED

    def test_default_review_status_is_pending(self) -> None:
        entry = MarketplaceEntry.from_dict({
            "name": "new-plugin",
            "version": "0.1",
            "description": "Brand new",
            "author": "dev",
        })
        assert entry.review_status == ReviewStatus.PENDING

    def test_dashboard_config_secure_defaults(self) -> None:
        """Dashboard binds to localhost by default, not 0.0.0.0."""
        config = DashboardConfig()
        assert config.host == "127.0.0.1"
        assert len(config.api_token) > 20

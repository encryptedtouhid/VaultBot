"""Unit tests for diff viewer and export."""

from __future__ import annotations

from vaultbot.tools.diff_viewer import DiffFormat, DiffViewer, ExportManager


class TestDiffViewer:
    def test_unified_diff(self) -> None:
        viewer = DiffViewer()
        result = viewer.unified_diff("hello\n", "hello\nworld\n")
        assert result.format == DiffFormat.UNIFIED
        assert result.additions >= 1

    def test_unified_no_changes(self) -> None:
        viewer = DiffViewer()
        result = viewer.unified_diff("same\n", "same\n")
        assert result.content == ""

    def test_html_diff(self) -> None:
        viewer = DiffViewer()
        result = viewer.html_diff("old", "new")
        assert result.format == DiffFormat.HTML
        assert "<" in result.content

    def test_side_by_side(self) -> None:
        viewer = DiffViewer()
        result = viewer.side_by_side("a\nb", "a\nc")
        assert result.format == DiffFormat.SIDE_BY_SIDE
        assert "|" in result.content


class TestExportManager:
    def test_to_markdown(self) -> None:
        viewer = DiffViewer()
        diff = viewer.unified_diff("a\n", "b\n")
        export = ExportManager()
        md = export.to_markdown(diff)
        assert "```diff" in md

    def test_to_plain_text(self) -> None:
        viewer = DiffViewer()
        diff = viewer.unified_diff("a\n", "b\n")
        export = ExportManager()
        assert export.to_plain_text(diff) == diff.content

    def test_summary(self) -> None:
        viewer = DiffViewer()
        diff = viewer.unified_diff("a\n", "b\n")
        export = ExportManager()
        summary = export.summary(diff)
        assert "file(s) changed" in summary

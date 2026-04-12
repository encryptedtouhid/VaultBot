"""QA Lab for automated testing scenarios."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ScenarioStatus(str, Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


@dataclass(slots=True)
class TestScenario:
    name: str
    input_messages: list[str] = field(default_factory=list)
    expected_patterns: list[str] = field(default_factory=list)
    status: ScenarioStatus = ScenarioStatus.PENDING
    actual_responses: list[str] = field(default_factory=list)
    error: str = ""


@dataclass(frozen=True, slots=True)
class LabResult:
    total: int = 0
    passed: int = 0
    failed: int = 0
    scenarios: list[TestScenario] = field(default_factory=list)


class QALab:
    """Automated QA testing lab."""

    def __init__(self) -> None:
        self._scenarios: list[TestScenario] = []

    def add_scenario(
        self,
        name: str,
        input_messages: list[str],
        expected_patterns: list[str] | None = None,
    ) -> TestScenario:
        scenario = TestScenario(
            name=name,
            input_messages=input_messages,
            expected_patterns=expected_patterns or [],
        )
        self._scenarios.append(scenario)
        return scenario

    @property
    def scenario_count(self) -> int:
        return len(self._scenarios)

    def run_scenario(self, scenario: TestScenario, responses: list[str]) -> bool:
        """Check if responses match expected patterns."""
        scenario.actual_responses = responses
        import re

        for pattern in scenario.expected_patterns:
            found = any(re.search(pattern, r, re.IGNORECASE) for r in responses)
            if not found:
                scenario.status = ScenarioStatus.FAILED
                scenario.error = f"Pattern not found: {pattern}"
                return False
        scenario.status = ScenarioStatus.PASSED
        return True

    def get_results(self) -> LabResult:
        passed = sum(1 for s in self._scenarios if s.status == ScenarioStatus.PASSED)
        failed = sum(1 for s in self._scenarios if s.status == ScenarioStatus.FAILED)
        return LabResult(
            total=len(self._scenarios),
            passed=passed,
            failed=failed,
            scenarios=list(self._scenarios),
        )

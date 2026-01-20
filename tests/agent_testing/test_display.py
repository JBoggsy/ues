"""Tests for the agent_testing.display module."""

import pytest
import json
from datetime import datetime, timezone
from pathlib import Path

from agent_testing.display import (
    format_report_terminal,
    format_report_summary,
    save_report_json,
    load_report_json,
    _create_progress_bar,
    _get_grade_emoji,
)
from agent_testing.results import CriterionResult, EvalReport


@pytest.fixture
def sample_report():
    """Create a sample test report."""
    return EvalReport(
        name="Test Suite",
        timestamp=datetime(2026, 1, 19, 12, 0, 0, tzinfo=timezone.utc),
        duration_seconds=5.5,
        total_score=75.0,
        max_score=100.0,
        criteria_results=[
            CriterionResult(
                id="crit_1",
                name="Criterion One",
                score=45.0,
                max_score=50.0,
                explanation="Almost perfect",
                eval_count=1,
            ),
            CriterionResult(
                id="crit_2",
                name="Criterion Two",
                score=30.0,
                max_score=50.0,
                explanation="Needs work",
                eval_count=5,
            ),
        ],
    )


class TestProgressBar:
    """Tests for progress bar creation."""

    def test_full_bar(self):
        """Test 100% progress bar."""
        bar = _create_progress_bar(100, 10)
        assert bar == "█" * 10

    def test_empty_bar(self):
        """Test 0% progress bar."""
        bar = _create_progress_bar(0, 10)
        assert bar == "░" * 10

    def test_half_bar(self):
        """Test 50% progress bar."""
        bar = _create_progress_bar(50, 10)
        assert bar == "█████░░░░░"

    def test_clamped_over_100(self):
        """Test that values over 100% are clamped."""
        bar = _create_progress_bar(150, 10)
        assert bar == "█" * 10

    def test_clamped_negative(self):
        """Test that negative values are clamped."""
        bar = _create_progress_bar(-10, 10)
        assert bar == "░" * 10


class TestGradeEmoji:
    """Tests for grade emoji selection."""

    def test_excellent_emoji(self):
        """Test emoji for Excellent grade."""
        assert _get_grade_emoji("Excellent") == "🏆"

    def test_good_emoji(self):
        """Test emoji for Good grade."""
        assert _get_grade_emoji("Good") == "✅"

    def test_needs_improvement_emoji(self):
        """Test emoji for Needs Improvement grade."""
        assert _get_grade_emoji("Needs Improvement") == "⚠️"

    def test_failing_emoji(self):
        """Test emoji for Failing grade."""
        assert _get_grade_emoji("Failing") == "❌"

    def test_unknown_grade(self):
        """Test emoji for unknown grade."""
        assert _get_grade_emoji("Unknown") == "📋"


class TestFormatReportTerminal:
    """Tests for terminal report formatting."""

    def test_contains_name(self, sample_report):
        """Test that output contains test suite name."""
        output = format_report_terminal(sample_report)
        assert "Test Suite" in output

    def test_contains_criterion_names(self, sample_report):
        """Test that output contains criterion names."""
        output = format_report_terminal(sample_report)
        assert "Criterion One" in output
        assert "Criterion Two" in output

    def test_contains_scores(self, sample_report):
        """Test that output contains scores."""
        output = format_report_terminal(sample_report)
        assert "45.0" in output
        assert "30.0" in output
        assert "75.0" in output

    def test_contains_total_score(self, sample_report):
        """Test that output contains total score."""
        output = format_report_terminal(sample_report)
        assert "TOTAL SCORE" in output
        assert "100" in output  # max score

    def test_contains_grade(self, sample_report):
        """Test that output contains grade."""
        output = format_report_terminal(sample_report)
        assert "Good" in output

    def test_contains_explanations(self, sample_report):
        """Test that output contains explanations."""
        output = format_report_terminal(sample_report)
        assert "Almost perfect" in output
        assert "Needs work" in output

    def test_shows_eval_count_for_multi_eval(self, sample_report):
        """Test that eval count is shown for criteria with multiple evals."""
        output = format_report_terminal(sample_report)
        assert "5 evaluations" in output

    def test_contains_progress_bars(self, sample_report):
        """Test that output contains progress bars."""
        output = format_report_terminal(sample_report)
        assert "█" in output
        assert "░" in output


class TestFormatReportSummary:
    """Tests for summary line formatting."""

    def test_summary_contains_name(self, sample_report):
        """Test that summary contains test name."""
        summary = format_report_summary(sample_report)
        assert "Test Suite" in summary

    def test_summary_contains_score(self, sample_report):
        """Test that summary contains score."""
        summary = format_report_summary(sample_report)
        assert "75.0" in summary
        assert "100.0" in summary

    def test_summary_contains_grade(self, sample_report):
        """Test that summary contains grade."""
        summary = format_report_summary(sample_report)
        assert "Good" in summary

    def test_summary_is_one_line(self, sample_report):
        """Test that summary is a single line."""
        summary = format_report_summary(sample_report)
        assert "\n" not in summary


class TestSaveLoadReportJson:
    """Tests for JSON report saving and loading."""

    def test_save_report(self, sample_report, tmp_path):
        """Test saving report to JSON file."""
        output_path = tmp_path / "results.json"

        save_report_json(sample_report, output_path)

        assert output_path.exists()
        content = output_path.read_text()
        data = json.loads(content)
        assert data["name"] == "Test Suite"
        assert data["total_score"] == 75.0

    def test_save_creates_parent_dirs(self, sample_report, tmp_path):
        """Test that save creates parent directories."""
        output_path = tmp_path / "nested" / "dir" / "results.json"

        save_report_json(sample_report, output_path)

        assert output_path.exists()

    def test_load_report(self, sample_report, tmp_path):
        """Test loading report from JSON file."""
        output_path = tmp_path / "results.json"
        save_report_json(sample_report, output_path)

        data = load_report_json(output_path)

        assert data["name"] == "Test Suite"
        assert data["total_score"] == 75.0
        assert len(data["criteria_results"]) == 2

    def test_save_string_path(self, sample_report, tmp_path):
        """Test saving with string path."""
        output_path = str(tmp_path / "results.json")

        save_report_json(sample_report, output_path)

        assert Path(output_path).exists()

    def test_report_roundtrip(self, sample_report, tmp_path):
        """Test that saved report can be loaded back."""
        output_path = tmp_path / "results.json"
        save_report_json(sample_report, output_path)

        loaded = load_report_json(output_path)

        assert loaded["name"] == sample_report.name
        assert loaded["total_score"] == sample_report.total_score
        assert loaded["max_score"] == sample_report.max_score
        assert loaded["grade"] == sample_report.grade
        assert len(loaded["criteria_results"]) == len(sample_report.criteria_results)

"""Tests for the agent_testing.results module."""

import pytest
from datetime import datetime, timezone

from agent_testing.results import CriterionResult, EvalReport, EvalResult


class TestEvalResult:
    """Tests for the EvalResult class."""

    def test_valid_result(self):
        """Test creating a valid test result."""
        result = EvalResult(
            score=8.0,
            max_score=10.0,
            explanation="8 out of 10 items completed",
        )

        assert result.score == 8.0
        assert result.max_score == 10.0
        assert result.explanation == "8 out of 10 items completed"
        assert result.details is None

    def test_result_with_details(self):
        """Test result with details dictionary."""
        details = {"items_found": ["a", "b", "c"], "missing": ["d"]}
        result = EvalResult(
            score=3.0,
            max_score=4.0,
            explanation="Found 3 of 4 items",
            details=details,
        )

        assert result.details == details

    def test_percentage_calculation(self):
        """Test percentage property."""
        result = EvalResult(score=7.5, max_score=10.0, explanation="Test")
        assert result.percentage == 75.0

    def test_percentage_full_score(self):
        """Test percentage with full score."""
        result = EvalResult(score=10.0, max_score=10.0, explanation="Perfect")
        assert result.percentage == 100.0

    def test_percentage_zero_score(self):
        """Test percentage with zero score."""
        result = EvalResult(score=0.0, max_score=10.0, explanation="None")
        assert result.percentage == 0.0

    def test_negative_score_rejected(self):
        """Test that negative scores are rejected."""
        with pytest.raises(ValueError) as exc_info:
            EvalResult(score=-1.0, max_score=10.0, explanation="Invalid")
        assert "negative" in str(exc_info.value).lower()

    def test_zero_max_score_rejected(self):
        """Test that zero max_score is rejected."""
        with pytest.raises(ValueError) as exc_info:
            EvalResult(score=0.0, max_score=0.0, explanation="Invalid")
        assert "positive" in str(exc_info.value).lower()

    def test_negative_max_score_rejected(self):
        """Test that negative max_score is rejected."""
        with pytest.raises(ValueError):
            EvalResult(score=0.0, max_score=-5.0, explanation="Invalid")

    def test_score_exceeds_max_rejected(self):
        """Test that score > max_score is rejected."""
        with pytest.raises(ValueError) as exc_info:
            EvalResult(score=15.0, max_score=10.0, explanation="Invalid")
        assert "exceed" in str(exc_info.value).lower()

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = EvalResult(
            score=7.0,
            max_score=10.0,
            explanation="Test explanation",
            details={"key": "value"},
        )

        d = result.to_dict()

        assert d["score"] == 7.0
        assert d["max_score"] == 10.0
        assert d["percentage"] == 70.0
        assert d["explanation"] == "Test explanation"
        assert d["details"] == {"key": "value"}


class TestCriterionResult:
    """Tests for the CriterionResult class."""

    def test_valid_result(self):
        """Test creating a valid criterion result."""
        result = CriterionResult(
            id="test_criterion",
            name="Test Criterion",
            score=15.0,
            max_score=20.0,
            explanation="Completed 15/20",
        )

        assert result.id == "test_criterion"
        assert result.name == "Test Criterion"
        assert result.score == 15.0
        assert result.max_score == 20.0
        assert result.eval_count == 1

    def test_percentage(self):
        """Test percentage calculation."""
        result = CriterionResult(
            id="test",
            name="Test",
            score=18.0,
            max_score=20.0,
            explanation="Test",
        )
        assert result.percentage == 90.0

    def test_with_individual_results(self):
        """Test criterion result with individual EvalResults."""
        individual = [
            EvalResult(score=1.0, max_score=1.0, explanation="Pass"),
            EvalResult(score=0.5, max_score=1.0, explanation="Partial"),
            EvalResult(score=0.0, max_score=1.0, explanation="Fail"),
        ]

        result = CriterionResult(
            id="multi",
            name="Multi-eval",
            score=7.5,
            max_score=10.0,
            explanation="3 evaluations",
            eval_count=3,
            individual_results=individual,
            raw_score=1.5,
            raw_max_score=3.0,
        )

        assert len(result.individual_results) == 3
        assert result.raw_score == 1.5
        assert result.raw_max_score == 3.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        individual = [
            EvalResult(score=1.0, max_score=1.0, explanation="Pass"),
        ]

        result = CriterionResult(
            id="test",
            name="Test",
            score=8.0,
            max_score=10.0,
            explanation="Test",
            eval_count=1,
            individual_results=individual,
        )

        d = result.to_dict()

        assert d["id"] == "test"
        assert d["name"] == "Test"
        assert d["score"] == 8.0
        assert d["max_score"] == 10.0
        assert d["percentage"] == 80.0
        assert d["eval_count"] == 1
        assert len(d["individual_results"]) == 1


class TestEvalReport:
    """Tests for the EvalReport class."""

    @pytest.fixture
    def sample_criterion_results(self):
        """Create sample criterion results for testing."""
        return [
            CriterionResult(
                id="crit_1",
                name="Criterion 1",
                score=18.0,
                max_score=20.0,
                explanation="18/20",
            ),
            CriterionResult(
                id="crit_2",
                name="Criterion 2",
                score=7.0,
                max_score=10.0,
                explanation="7/10",
            ),
        ]

    def test_create_report(self, sample_criterion_results):
        """Test creating a report from criterion results."""
        report = EvalReport.create(
            name="Test Suite",
            criteria_results=sample_criterion_results,
            duration_seconds=5.5,
        )

        assert report.name == "Test Suite"
        assert report.total_score == 25.0  # 18 + 7
        assert report.max_score == 30.0  # 20 + 10
        assert report.duration_seconds == 5.5
        assert len(report.criteria_results) == 2

    def test_percentage(self, sample_criterion_results):
        """Test percentage calculation."""
        report = EvalReport.create(
            name="Test",
            criteria_results=sample_criterion_results,
            duration_seconds=1.0,
        )
        # 25/30 = 83.33%
        assert abs(report.percentage - 83.33) < 0.1

    def test_grade_excellent(self):
        """Test grade for excellent score (>=90%)."""
        result = CriterionResult(
            id="test", name="Test", score=95.0, max_score=100.0, explanation="Test"
        )
        report = EvalReport.create(
            name="Test", criteria_results=[result], duration_seconds=1.0
        )
        assert report.grade == "Excellent"

    def test_grade_good(self):
        """Test grade for good score (>=70%)."""
        result = CriterionResult(
            id="test", name="Test", score=75.0, max_score=100.0, explanation="Test"
        )
        report = EvalReport.create(
            name="Test", criteria_results=[result], duration_seconds=1.0
        )
        assert report.grade == "Good"

    def test_grade_needs_improvement(self):
        """Test grade for needs improvement (>=50%)."""
        result = CriterionResult(
            id="test", name="Test", score=55.0, max_score=100.0, explanation="Test"
        )
        report = EvalReport.create(
            name="Test", criteria_results=[result], duration_seconds=1.0
        )
        assert report.grade == "Needs Improvement"

    def test_grade_failing(self):
        """Test grade for failing score (<50%)."""
        result = CriterionResult(
            id="test", name="Test", score=30.0, max_score=100.0, explanation="Test"
        )
        report = EvalReport.create(
            name="Test", criteria_results=[result], duration_seconds=1.0
        )
        assert report.grade == "Failing"

    def test_passed_true(self):
        """Test passed property when score >= 50%."""
        result = CriterionResult(
            id="test", name="Test", score=60.0, max_score=100.0, explanation="Test"
        )
        report = EvalReport.create(
            name="Test", criteria_results=[result], duration_seconds=1.0
        )
        assert report.passed is True

    def test_passed_false(self):
        """Test passed property when score < 50%."""
        result = CriterionResult(
            id="test", name="Test", score=40.0, max_score=100.0, explanation="Test"
        )
        report = EvalReport.create(
            name="Test", criteria_results=[result], duration_seconds=1.0
        )
        assert report.passed is False

    def test_to_dict(self, sample_criterion_results):
        """Test conversion to dictionary."""
        report = EvalReport.create(
            name="Test Suite",
            criteria_results=sample_criterion_results,
            duration_seconds=3.5,
            scenario_path="/path/to/scenario.json",
            metadata={"custom": "data"},
        )

        d = report.to_dict()

        assert d["name"] == "Test Suite"
        assert d["total_score"] == 25.0
        assert d["max_score"] == 30.0
        assert d["duration_seconds"] == 3.5
        assert d["scenario_path"] == "/path/to/scenario.json"
        assert d["metadata"] == {"custom": "data"}
        assert "timestamp" in d
        assert "grade" in d
        assert "passed" in d
        assert len(d["criteria_results"]) == 2

    def test_timestamp_is_set(self, sample_criterion_results):
        """Test that timestamp is automatically set."""
        report = EvalReport.create(
            name="Test",
            criteria_results=sample_criterion_results,
            duration_seconds=1.0,
        )

        assert report.timestamp is not None
        assert report.timestamp.tzinfo is not None  # Should be timezone-aware

"""Tests for the agent_testing.schema module."""

import pytest
from pydantic import ValidationError

from ues.agent_testing.schema import (
    CriteriaSchema,
    CriterionSchema,
    EvalTiming,
    load_criteria_from_dict,
    load_criteria_from_file,
)


class TestCriterionSchema:
    """Tests for the CriterionSchema model."""

    def test_valid_post_scenario_criterion(self):
        """Test creating a valid post_scenario criterion."""
        criterion = CriterionSchema(
            id="test_criterion",
            name="Test Criterion",
            description="A test criterion",
            evaluator="check_something",
            max_points=20.0,
            eval_timing=EvalTiming.POST_SCENARIO,
            params={"expected": 5},
        )

        assert criterion.id == "test_criterion"
        assert criterion.name == "Test Criterion"
        assert criterion.evaluator == "check_something"
        assert criterion.max_points == 20.0
        assert criterion.eval_timing == EvalTiming.POST_SCENARIO
        assert criterion.params == {"expected": 5}

    def test_valid_on_event_criterion(self):
        """Test creating a valid on_event criterion with filter."""
        criterion = CriterionSchema(
            id="email_quality",
            name="Email Quality",
            evaluator="check_email_quality",
            max_points=10.0,
            eval_timing=EvalTiming.ON_EVENT,
            event_filter="filter_sent_emails",
        )

        assert criterion.eval_timing == EvalTiming.ON_EVENT
        assert criterion.event_filter == "filter_sent_emails"

    def test_minimal_criterion(self):
        """Test criterion with only required fields."""
        criterion = CriterionSchema(
            id="minimal",
            name="Minimal Criterion",
            evaluator="check_minimal",
            max_points=5.0,
            eval_timing="post_scenario",  # String should work too
        )

        assert criterion.id == "minimal"
        assert criterion.description is None
        assert criterion.event_filter is None
        assert criterion.params == {}

    def test_invalid_id_special_chars(self):
        """Test that invalid IDs are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CriterionSchema(
                id="test criterion!",  # Invalid: has space and !
                name="Test",
                evaluator="check",
                max_points=10.0,
                eval_timing="post_scenario",
            )

        assert "alphanumeric" in str(exc_info.value).lower()

    def test_valid_id_with_underscore_and_hyphen(self):
        """Test that IDs with underscores and hyphens are valid."""
        criterion = CriterionSchema(
            id="test_criterion-1",
            name="Test",
            evaluator="check",
            max_points=10.0,
            eval_timing="post_scenario",
        )
        assert criterion.id == "test_criterion-1"

    def test_invalid_evaluator_name(self):
        """Test that invalid function names are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CriterionSchema(
                id="test",
                name="Test",
                evaluator="invalid-function-name",  # Hyphens invalid in Python
                max_points=10.0,
                eval_timing="post_scenario",
            )

        assert "identifier" in str(exc_info.value).lower()

    def test_invalid_max_points_zero(self):
        """Test that zero max_points is rejected."""
        with pytest.raises(ValidationError):
            CriterionSchema(
                id="test",
                name="Test",
                evaluator="check",
                max_points=0,  # Must be > 0
                eval_timing="post_scenario",
            )

    def test_invalid_max_points_negative(self):
        """Test that negative max_points is rejected."""
        with pytest.raises(ValidationError):
            CriterionSchema(
                id="test",
                name="Test",
                evaluator="check",
                max_points=-5,
                eval_timing="post_scenario",
            )

    def test_invalid_eval_timing(self):
        """Test that invalid eval_timing is rejected."""
        with pytest.raises(ValidationError):
            CriterionSchema(
                id="test",
                name="Test",
                evaluator="check",
                max_points=10.0,
                eval_timing="invalid_timing",
            )


class TestCriteriaSchema:
    """Tests for the CriteriaSchema model."""

    def test_valid_criteria(self):
        """Test creating valid test criteria."""
        criteria = CriteriaSchema(
            name="Test Suite",
            description="A test suite",
            test_module="my_tests",
            criteria=[
                CriterionSchema(
                    id="criterion_1",
                    name="Criterion 1",
                    evaluator="check_1",
                    max_points=10.0,
                    eval_timing="post_scenario",
                ),
                CriterionSchema(
                    id="criterion_2",
                    name="Criterion 2",
                    evaluator="check_2",
                    max_points=20.0,
                    eval_timing="on_event",
                    event_filter="filter_events",
                ),
            ],
        )

        assert criteria.name == "Test Suite"
        assert criteria.test_module == "my_tests"
        assert len(criteria.criteria) == 2

    def test_default_test_module(self):
        """Test that test_module defaults to scenario_tests."""
        criteria = CriteriaSchema(
            name="Test Suite",
            criteria=[
                CriterionSchema(
                    id="test",
                    name="Test",
                    evaluator="check",
                    max_points=10.0,
                    eval_timing="post_scenario",
                ),
            ],
        )

        assert criteria.test_module == "scenario_tests"

    def test_empty_criteria_list(self):
        """Test that empty criteria list is rejected."""
        with pytest.raises(ValidationError):
            CriteriaSchema(
                name="Test Suite",
                criteria=[],  # Must have at least one criterion
            )

    def test_duplicate_criterion_ids(self):
        """Test that duplicate criterion IDs are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CriteriaSchema(
                name="Test Suite",
                criteria=[
                    CriterionSchema(
                        id="same_id",
                        name="First",
                        evaluator="check",
                        max_points=10.0,
                        eval_timing="post_scenario",
                    ),
                    CriterionSchema(
                        id="same_id",  # Duplicate!
                        name="Second",
                        evaluator="check_other",
                        max_points=10.0,
                        eval_timing="post_scenario",
                    ),
                ],
            )

        assert "duplicate" in str(exc_info.value).lower()

    def test_invalid_module_name(self):
        """Test that invalid module names are rejected."""
        with pytest.raises(ValidationError):
            CriteriaSchema(
                name="Test Suite",
                test_module="invalid-module-name",  # Hyphens invalid
                criteria=[
                    CriterionSchema(
                        id="test",
                        name="Test",
                        evaluator="check",
                        max_points=10.0,
                        eval_timing="post_scenario",
                    ),
                ],
            )

    def test_dotted_module_name(self):
        """Test that dotted module names are valid."""
        criteria = CriteriaSchema(
            name="Test Suite",
            test_module="my_package.tests.evaluators",
            criteria=[
                CriterionSchema(
                    id="test",
                    name="Test",
                    evaluator="check",
                    max_points=10.0,
                    eval_timing="post_scenario",
                ),
            ],
        )

        assert criteria.test_module == "my_package.tests.evaluators"


class TestLoadCriteriaFromDict:
    """Tests for load_criteria_from_dict function."""

    def test_load_valid_dict(self):
        """Test loading criteria from a valid dictionary."""
        data = {
            "name": "Test Suite",
            "criteria": [
                {
                    "id": "test_1",
                    "name": "Test 1",
                    "evaluator": "check_1",
                    "max_points": 10,
                    "eval_timing": "post_scenario",
                }
            ],
        }

        criteria = load_criteria_from_dict(data)

        assert criteria.name == "Test Suite"
        assert len(criteria.criteria) == 1
        assert criteria.criteria[0].id == "test_1"

    def test_load_invalid_dict(self):
        """Test that invalid data raises ValidationError."""
        data = {
            "name": "Test Suite",
            "criteria": [
                {
                    "id": "test",
                    # Missing required fields
                }
            ],
        }

        with pytest.raises(ValidationError):
            load_criteria_from_dict(data)


class TestLoadCriteriaFromFile:
    """Tests for load_criteria_from_file function."""

    def test_file_not_found(self, tmp_path):
        """Test that FileNotFoundError is raised for missing file."""
        with pytest.raises(FileNotFoundError):
            load_criteria_from_file(str(tmp_path / "nonexistent.json"))

    def test_load_valid_file(self, tmp_path):
        """Test loading criteria from a valid JSON file."""
        import json

        criteria_file = tmp_path / "test_criteria.json"
        criteria_file.write_text(
            json.dumps(
                {
                    "name": "File Test",
                    "criteria": [
                        {
                            "id": "file_test",
                            "name": "File Test",
                            "evaluator": "check_file",
                            "max_points": 15,
                            "eval_timing": "post_scenario",
                        }
                    ],
                }
            )
        )

        criteria = load_criteria_from_file(str(criteria_file))

        assert criteria.name == "File Test"
        assert criteria.criteria[0].max_points == 15

    def test_load_invalid_json(self, tmp_path):
        """Test that invalid JSON raises an error."""
        import json

        criteria_file = tmp_path / "invalid.json"
        criteria_file.write_text("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            load_criteria_from_file(str(criteria_file))

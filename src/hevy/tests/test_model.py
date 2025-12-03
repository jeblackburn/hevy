"""
Unit tests for Pydantic model classes.
"""

import pytest
from pydantic import ValidationError

from ..model import ExerciseSet, Exercise, WorkoutSection


class TestExerciseSet:
    """Test ExerciseSet model"""

    def test_exercise_set_creation(self):
        """Test creating valid exercise set"""
        exercise_set = ExerciseSet(
            type="normal",
            weight_kg=15.0,
            reps=10
        )

        assert exercise_set.type == "normal"
        assert exercise_set.weight_kg == 15.0
        assert exercise_set.reps == 10
        assert exercise_set.distance_meters is None
        assert exercise_set.duration_seconds is None

    def test_exercise_set_defaults(self):
        """Test exercise set default values"""
        exercise_set = ExerciseSet()

        assert exercise_set.type == "normal"
        assert exercise_set.weight_kg is None
        assert exercise_set.reps is None

    def test_exercise_set_with_distance(self):
        """Test exercise set with distance metric"""
        exercise_set = ExerciseSet(
            type="normal",
            distance_meters=1000.0,
            duration_seconds=300
        )

        assert exercise_set.distance_meters == 1000.0
        assert exercise_set.duration_seconds == 300

    def test_exercise_set_model_dump(self):
        """Test serialization with model_dump"""
        exercise_set = ExerciseSet(
            type="normal",
            weight_kg=20.0,
            reps=8
        )

        data = exercise_set.model_dump()

        assert isinstance(data, dict)
        assert data['type'] == "normal"
        assert data['weight_kg'] == 20.0
        assert data['reps'] == 8

    def test_exercise_set_optional_fields(self):
        """Test that optional fields can be None"""
        exercise_set = ExerciseSet(
            type="normal",
            weight_kg=None,
            reps=None
        )

        assert exercise_set.weight_kg is None
        assert exercise_set.reps is None


class TestExercise:
    """Test Exercise model"""

    def test_exercise_creation(self):
        """Test creating valid exercise"""
        exercise = Exercise(
            exercise_template_id="ex001",
            superset_id="1A",
            rest_seconds=90,
            notes="Test note"
        )

        assert exercise.exercise_template_id == "ex001"
        assert exercise.superset_id == "1A"
        assert exercise.rest_seconds == 90
        assert exercise.notes == "Test note"
        assert exercise.sets == []

    def test_exercise_defaults(self):
        """Test exercise default values"""
        exercise = Exercise(exercise_template_id="ex001")

        assert exercise.superset_id is None
        assert exercise.rest_seconds == 0
        assert exercise.notes is None
        assert exercise.sets == []

    def test_exercise_with_sets(self):
        """Test exercise with sets"""
        exercise = Exercise(
            exercise_template_id="ex001",
            sets=[
                {'type': 'normal', 'weight_kg': 15.0, 'reps': 10},
                {'type': 'normal', 'weight_kg': 20.0, 'reps': 8}
            ]
        )

        assert len(exercise.sets) == 2
        assert exercise.sets[0]['reps'] == 10

    def test_exercise_model_dump(self):
        """Test serialization with model_dump"""
        exercise = Exercise(
            exercise_template_id="ex001",
            rest_seconds=60
        )

        data = exercise.model_dump()

        assert isinstance(data, dict)
        assert data['exercise_template_id'] == "ex001"
        assert data['rest_seconds'] == 60

    def test_exercise_validation_required_field(self):
        """Test that exercise_template_id is required"""
        with pytest.raises(ValidationError):
            Exercise()


class TestWorkoutSection:
    """Test WorkoutSection model"""

    def test_workout_section_creation(self):
        """Test creating valid workout section"""
        section = WorkoutSection(
            section_id="A",
            section_type="GIANT SET",
            rounds=6,
            rest_between_rounds=150,
            target="QUADS, HAMSTRINGS",
            exercises=[]
        )

        assert section.section_id == "A"
        assert section.section_type == "GIANT SET"
        assert section.rounds == 6
        assert section.rest_between_rounds == 150
        assert section.target == "QUADS, HAMSTRINGS"
        assert section.exercises == []

    def test_workout_section_with_exercises(self):
        """Test workout section with exercises"""
        section = WorkoutSection(
            section_id="A",
            section_type="SUPERSET",
            rounds=4,
            rest_between_rounds=90,
            target="CHEST",
            exercises=[
                {
                    'exercise_template_id': 'ex001',
                    'superset_id': '1A',
                    'rest_seconds': 0,
                    'sets': []
                },
                {
                    'exercise_template_id': 'ex002',
                    'superset_id': '1A',
                    'rest_seconds': 90,
                    'sets': []
                }
            ]
        )

        assert len(section.exercises) == 2
        assert section.exercises[0]['exercise_template_id'] == 'ex001'

    def test_workout_section_model_dump(self):
        """Test serialization with model_dump"""
        section = WorkoutSection(
            section_id="B",
            section_type="FINISHER",
            rounds=3,
            rest_between_rounds=60,
            target="CORE",
            exercises=[]
        )

        data = section.model_dump()

        assert isinstance(data, dict)
        assert data['section_id'] == "B"
        assert data['section_type'] == "FINISHER"
        assert data['rounds'] == 3

    def test_workout_section_validation_required_fields(self):
        """Test that all fields are required"""
        with pytest.raises(ValidationError):
            WorkoutSection()

        with pytest.raises(ValidationError):
            WorkoutSection(section_id="A")

        with pytest.raises(ValidationError):
            WorkoutSection(
                section_id="A",
                section_type="GIANT SET"
            )


class TestModelIntegration:
    """Test model integration and serialization"""

    def test_nested_serialization(self):
        """Test serialization of nested structures"""
        # Create exercise sets
        set1 = ExerciseSet(type="normal", weight_kg=15.0, reps=10)
        set2 = ExerciseSet(type="normal", weight_kg=20.0, reps=8)

        # Create exercises with sets
        exercise_data = {
            'exercise_template_id': 'ex001',
            'superset_id': '1A',
            'rest_seconds': 0,
            'sets': [set1.model_dump(), set2.model_dump()]
        }

        # Create section with exercises
        section = WorkoutSection(
            section_id="A",
            section_type="GIANT SET",
            rounds=2,
            rest_between_rounds=120,
            target="LEGS",
            exercises=[exercise_data]
        )

        # Serialize entire structure
        data = section.model_dump()

        assert data['exercises'][0]['sets'][0]['weight_kg'] == 15.0
        assert data['exercises'][0]['sets'][1]['weight_kg'] == 20.0

    def test_model_json_compatibility(self):
        """Test that models can be converted to JSON-compatible format"""
        import json

        exercise_set = ExerciseSet(type="normal", weight_kg=15.0, reps=10)
        data = exercise_set.model_dump()

        # Should be JSON serializable
        json_str = json.dumps(data)
        assert isinstance(json_str, str)

        # Should be able to parse back
        parsed = json.loads(json_str)
        assert parsed['weight_kg'] == 15.0
        assert parsed['reps'] == 10
"""
Unit tests for PDFWorkoutParser class.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from hevy.model import ExerciseSet, WorkoutSection
from hevy.workout_parser import PDFWorkoutParser, WEIGHT_MAPPING


class TestPDFWorkoutParser:
    """Test suite for PDFWorkoutParser class"""

    def test_init(self, tmp_path, exercises_json_file, sample_exercises):
        """Test parser initialization"""
        # Create a dummy PDF file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy pdf content")

        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        assert parser.pdf_path == Path(pdf_file)
        assert len(parser.exercises) == len(sample_exercises)
        assert parser.exercise_titles["ex001"] == "Barbell Back Squat"
        assert parser.current_workout_number is None

    def test_load_exercises(self, tmp_path):
        """Test loading exercises from JSON file"""
        # Create test exercises JSON
        exercises = [
            {"id": "test1", "title": "Test Exercise 1"},
            {"id": "test2", "title": "Test Exercise 2"}
        ]
        json_file = tmp_path / "test_exercises.json"
        with open(json_file, 'w') as f:
            json.dump(exercises, f)

        # Create parser
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(json_file))

        assert len(parser.exercises) == 2
        assert parser.exercises[0]["title"] == "Test Exercise 1"


class TestRestPeriodParsing:
    """Test rest period parsing"""

    def test_parse_rest_minutes_range(self, tmp_path, exercises_json_file):
        """Test parsing rest period with minute range"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        text = "Rest 2-3 Minutes Between Rounds"
        result = parser._parse_rest_period(text)

        assert result == 150  # Average of 2-3 minutes = 2.5 * 60 = 150 seconds

    def test_parse_rest_single_minute(self, tmp_path, exercises_json_file):
        """Test parsing rest period with single minute value"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        text = "Rest 2 Minutes Between Rounds"
        result = parser._parse_rest_period(text)

        assert result == 120  # 2 minutes = 120 seconds

    def test_parse_rest_seconds(self, tmp_path, exercises_json_file):
        """Test parsing rest period in seconds"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        text = "Rest 30-45 Seconds Between Rounds"
        result = parser._parse_rest_period(text)

        assert result == 37  # Average of 30-45 = 37.5 rounded down

    def test_parse_rest_default(self, tmp_path, exercises_json_file):
        """Test default rest period when not specified"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        text = "Some text without rest info"
        result = parser._parse_rest_period(text)

        assert result == 90  # Default from PLAN.md


class TestTargetParsing:
    """Test target muscle group parsing"""

    def test_parse_target_single(self, tmp_path, exercises_json_file):
        """Test parsing single target muscle"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        text = "TARGET: QUADS"
        result = parser._parse_target(text)

        assert result == "QUADS"

    def test_parse_target_multiple(self, tmp_path, exercises_json_file):
        """Test parsing multiple target muscles"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        text = "TARGET: QUADS, HAMSTRINGS, GLUTES"
        result = parser._parse_target(text)

        assert result == "QUADS, HAMSTRINGS, GLUTES"

    def test_parse_target_missing(self, tmp_path, exercises_json_file):
        """Test parsing when target is missing"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        text = "Some text without target info"
        result = parser._parse_target(text)

        assert result == ""


class TestExerciseNameMatching:
    """Test exercise name matching"""

    def test_match_exact(self, tmp_path, exercises_json_file):
        """Test exact exercise name match"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        exercise_id, confidence = parser._match_exercise_name("Barbell Back Squat")

        assert exercise_id == "ex001"
        assert confidence == 100

    def test_match_case_insensitive(self, tmp_path, exercises_json_file):
        """Test case-insensitive matching"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        exercise_id, confidence = parser._match_exercise_name("barbell back squat")

        assert exercise_id == "ex001"
        assert confidence == 100

    def test_match_fuzzy(self, tmp_path, exercises_json_file):
        """Test fuzzy matching for similar names"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        exercise_id, confidence = parser._match_exercise_name("BB Back Squat")

        assert exercise_id == "ex001"
        assert confidence >= 70  # Should have reasonable confidence

    def test_match_no_match(self, tmp_path, exercises_json_file, capsys):
        """Test behavior when no good match found"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        exercise_id, confidence = parser._match_exercise_name("Completely Unknown Exercise")

        # Should return some exercise with low confidence
        # Fuzzy matching always returns something, even if it's a poor match
        assert exercise_id in parser.exercise_titles
        assert confidence < 70  # Low confidence match


class TestWeightConversion:
    """Test weight conversion"""

    def test_convert_weight_exact_match(self, tmp_path, exercises_json_file):
        """Test exact weight description match"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        assert parser._convert_weight_to_kg("medium") == 15
        assert parser._convert_weight_to_kg("heavy") == 40
        assert parser._convert_weight_to_kg("bodyweight") == 0
        assert parser._convert_weight_to_kg("light") == 10

    def test_convert_weight_case_insensitive(self, tmp_path, exercises_json_file):
        """Test case-insensitive weight conversion"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        assert parser._convert_weight_to_kg("MEDIUM") == 15
        assert parser._convert_weight_to_kg("Heavy") == 40

    def test_convert_weight_fuzzy_match(self, tmp_path, exercises_json_file):
        """Test fuzzy matching for weight descriptions"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        # Should match "medium plus"
        assert parser._convert_weight_to_kg("medium plus weight") == 20

    def test_convert_weight_none_for_unknown(self, tmp_path, exercises_json_file):
        """Test return None for unknown weights"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        assert parser._convert_weight_to_kg("unknown weight") is None

    def test_convert_weight_as_heavy_as_possible(self, tmp_path, exercises_json_file):
        """Test 'as heavy as possible' returns None"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        assert parser._convert_weight_to_kg("as heavy as possible") is None


class TestRepsParsing:
    """Test reps parsing"""

    def test_parse_reps_single_value(self, tmp_path, exercises_json_file):
        """Test parsing single rep value for all rounds"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        block_text = "1 Exercise Name\n10\nMedium"
        result = parser._parse_reps_from_block(block_text, rounds=4)

        assert result == [10, 10, 10, 10]

    def test_parse_reps_range(self, tmp_path, exercises_json_file):
        """Test parsing rep range"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        block_text = "1 Exercise Name\n8-10\nMedium"
        result = parser._parse_reps_from_block(block_text, rounds=3)

        assert result == [9, 9, 9]  # Midpoint of 8-10

    def test_parse_reps_by_round(self, tmp_path, exercises_json_file):
        """Test parsing different reps per round"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        block_text = """1 Exercise Name
Round 1: 8
Round 2: 10
Round 3: 12
Medium"""
        result = parser._parse_reps_from_block(block_text, rounds=3)

        assert result == [8, 10, 12]

    def test_parse_reps_round_range(self, tmp_path, exercises_json_file):
        """Test parsing rep count for range of rounds"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        block_text = """1 Exercise Name
Round 1: 8
Round 2-6: 6
Medium"""
        result = parser._parse_reps_from_block(block_text, rounds=6)

        assert result == [8, 6, 6, 6, 6, 6]


class TestWeightParsing:
    """Test weight parsing from blocks"""

    def test_parse_weight_uniform(self, tmp_path, exercises_json_file):
        """Test parsing uniform weight for all rounds"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        block_text = "1 Exercise Name\n10\nMedium"
        result = parser._parse_weight_from_block(block_text, rounds=4)

        assert result == [15, 15, 15, 15]  # Medium = 15kg

    def test_parse_weight_by_round(self, tmp_path, exercises_json_file):
        """Test parsing different weights per round"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        block_text = """1 Exercise Name
Round 1: Medium
Round 2-3: Heavy
10 reps"""
        result = parser._parse_weight_from_block(block_text, rounds=3)

        assert result == [15, 40, 40]  # Medium=15, Heavy=40

    def test_parse_weight_bodyweight(self, tmp_path, exercises_json_file):
        """Test parsing bodyweight exercises"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        block_text = "1 Walking Lunge\n16\nBodyweight"
        result = parser._parse_weight_from_block(block_text, rounds=3)

        assert result == [0, 0, 0]  # Bodyweight = 0kg


class TestNoteExtraction:
    """Test note extraction"""

    def test_extract_notes_with_parenthetical(self, tmp_path, exercises_json_file):
        """Test extracting parenthetical notes"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        block_text = "1 Exercise Name (Pause at bottom)\n10\nMedium"
        result = parser._extract_notes_from_block(block_text)

        assert "(Pause at bottom)" in result

    def test_extract_notes_with_keywords(self, tmp_path, exercises_json_file):
        """Test extracting notes with instruction keywords"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        block_text = "1 Exercise. Contract at the top. Hold for 2 seconds\n10\nMedium"
        result = parser._extract_notes_from_block(block_text)

        assert "Contract" in result or "Hold" in result

    def test_extract_notes_none_when_empty(self, tmp_path, exercises_json_file):
        """Test return None when no notes found"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        block_text = "1 Exercise Name\n10\nMedium"
        result = parser._extract_notes_from_block(block_text)

        assert result is None


class TestSetGeneration:
    """Test set generation"""

    def test_generate_sets(self, tmp_path, exercises_json_file):
        """Test generating exercise sets"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        reps_data = [10, 10, 10]
        weight_data = [15, 15, 15]
        rounds = 3

        result = parser._generate_sets(reps_data, weight_data, rounds)

        assert len(result) == 3
        assert all(isinstance(s, ExerciseSet) for s in result)
        assert result[0].reps == 10
        assert result[0].weight_kg == 15
        assert result[0].type == "normal"

    def test_generate_sets_different_values(self, tmp_path, exercises_json_file):
        """Test generating sets with varying reps and weights"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        reps_data = [8, 10, 12]
        weight_data = [15, 20, 25]
        rounds = 3

        result = parser._generate_sets(reps_data, weight_data, rounds)

        assert result[0].reps == 8
        assert result[0].weight_kg == 15
        assert result[1].reps == 10
        assert result[1].weight_kg == 20
        assert result[2].reps == 12
        assert result[2].weight_kg == 25

    def test_generate_sets_with_none_values(self, tmp_path, exercises_json_file):
        """Test generating sets with None values"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        reps_data = [10, None, 10]
        weight_data = [None, 15, None]
        rounds = 3

        result = parser._generate_sets(reps_data, weight_data, rounds)

        assert result[0].reps == 10
        assert result[0].weight_kg is None
        assert result[1].reps is None
        assert result[1].weight_kg == 15


class TestFindWorkouts:
    """Test workout segmentation"""

    def test_find_workouts(self, tmp_path, exercises_json_file, sample_pages_data):
        """Test finding and segmenting workouts"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        workouts = parser.find_workouts(sample_pages_data)

        assert len(workouts) == 2
        assert 1 in workouts
        assert 2 in workouts
        assert len(workouts[1]) == 1
        assert len(workouts[2]) == 1

    def test_find_workouts_multiple_pages(self, tmp_path, exercises_json_file):
        """Test workout spanning multiple pages"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        pages_data = [
            {'page_number': 1, 'text': 'WORKOUT #1\nSome content', 'links': []},
            {'page_number': 2, 'text': 'More content for workout 1', 'links': []},
            {'page_number': 3, 'text': 'WORKOUT #2\nNew workout', 'links': []},
        ]

        workouts = parser.find_workouts(pages_data)

        assert len(workouts[1]) == 2  # Workout 1 has 2 pages
        assert len(workouts[2]) == 1  # Workout 2 has 1 page


class TestBuildRoutine:
    """Test routine building"""

    def test_build_routine(self, tmp_path, exercises_json_file):
        """Test building final routine structure"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        sections = [
            WorkoutSection(
                section_id="A",
                section_type="GIANT SET",
                rounds=6,
                rest_between_rounds=150,
                target="QUADS, HAMSTRINGS",
                exercises=[
                    {
                        'exercise_template_id': 'ex001',
                        'superset_id': '1A',
                        'rest_seconds': 90,
                        'notes': None,
                        'sets': []
                    }
                ]
            )
        ]

        result = parser._build_routine(
            workout_number=1,
            week_number=1,
            day_in_week=1,
            sections=sections
        )

        assert 'routine' in result
        assert result['routine']['title'] == "PaulSklarXfit365-v14 - Week 1 - Workout 1"
        assert len(result['routine']['exercises']) == 1
        assert result['routine']['folder_id'] is None

    def test_build_workout_notes(self, tmp_path, exercises_json_file):
        """Test building workout notes"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        sections = [
            WorkoutSection(
                section_id="A",
                section_type="GIANT SET",
                rounds=6,
                rest_between_rounds=150,
                target="QUADS",
                exercises=[]
            ),
            WorkoutSection(
                section_id="B",
                section_type="SUPERSET",
                rounds=4,
                rest_between_rounds=90,
                target="CHEST",
                exercises=[]
            )
        ]

        result = parser._build_workout_notes(sections)

        assert "Section A: GIANT SET - 6 rounds" in result
        assert "Target: QUADS" in result
        assert "Section B: SUPERSET - 4 rounds" in result
        assert "Target: CHEST" in result


class TestWeightMapping:
    """Test weight mapping constants"""

    def test_weight_mapping_values(self):
        """Test that weight mapping has expected values"""
        assert WEIGHT_MAPPING["medium"] == 15
        assert WEIGHT_MAPPING["medium plus"] == 20
        assert WEIGHT_MAPPING["heavy"] == 40
        assert WEIGHT_MAPPING["bodyweight"] == 0
        assert WEIGHT_MAPPING["light"] == 10

    def test_weight_mapping_none_values(self):
        """Test that 'as heavy as possible' variants return None"""
        assert WEIGHT_MAPPING["as heavy as possible"] is None
        assert WEIGHT_MAPPING["as heavy as possible to complete"] is None
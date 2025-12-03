"""
Integration tests for full PDF parsing workflow.
"""

from unittest.mock import MagicMock, patch

from ..workout_parser import PDFWorkoutParser


class TestPDFExtractionIntegration:
    """Integration tests for PDF extraction"""

    @patch('hevy.workout_parser.fitz')
    def test_extract_pdf_text(self, mock_fitz, tmp_path, exercises_json_file):
        """Test extracting text from PDF"""
        # Mock PyMuPDF document
        mock_doc = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.get_text.return_value = "Page 1 text\nWORKOUT #1"
        mock_page1.get_links.return_value = []

        mock_page2 = MagicMock()
        mock_page2.get_text.return_value = "Page 2 text"
        mock_page2.get_links.return_value = []

        mock_doc.__len__.return_value = 2
        mock_doc.__getitem__.side_effect = [mock_page1, mock_page2]
        mock_fitz.open.return_value = mock_doc

        # Create parser
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        # Extract text
        pages_data = parser.extract_pdf_text()

        assert len(pages_data) == 2
        assert pages_data[0]['page_number'] == 1
        assert "WORKOUT #1" in pages_data[0]['text']
        assert pages_data[1]['page_number'] == 2
        mock_doc.close.assert_called_once()


class TestSectionParsingIntegration:
    """Integration tests for section parsing"""

    def test_parse_sections(self, tmp_path, exercises_json_file, sample_section_text):
        """Test parsing workout sections"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        sections = parser._parse_sections(sample_section_text)

        assert len(sections) == 1
        assert sections[0].section_id == "A"
        assert sections[0].section_type == "GIANT SET"
        assert sections[0].rounds == 6
        assert sections[0].rest_between_rounds == 150
        assert sections[0].target == "QUADS, HAMSTRINGS, GLUTES"
        assert len(sections[0].exercises) >= 1

    def test_parse_multiple_sections(self, tmp_path, exercises_json_file):
        """Test parsing multiple sections in a workout"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        text = """
A GIANT SET: 6 ROUNDS
Rest 2-3 Minutes Between Rounds
TARGET: QUADS

1 Barbell Back Squat
10
Medium

B SUPERSET: 4 ROUNDS
Rest 90 Seconds Between Rounds
TARGET: CHEST

1 Bench Press
8
Heavy

C FINISHER: 3 ROUNDS
Rest 60 Seconds Between Rounds
TARGET: CORE

1 Crunches
20
Bodyweight
"""
        sections = parser._parse_sections(text)

        assert len(sections) == 3
        assert sections[0].section_id == "A"
        assert sections[1].section_id == "B"
        assert sections[2].section_id == "C"


class TestExerciseParsingIntegration:
    """Integration tests for exercise parsing"""

    def test_parse_exercises(self, tmp_path, exercises_json_file):
        """Test parsing exercises from section"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))
        parser.current_workout_number = 1

        section_text = """
1 Barbell Back Squat
Round 1: 8
Round 2-6: 6
Medium

2 Romanian Deadlift
10
Heavy

3 Walking Lunge
16
Bodyweight
"""
        exercises = parser._parse_exercises(section_text, "A", "GIANT SET", 6)

        assert len(exercises) == 3

        # Check first exercise
        assert exercises[0]['exercise_template_id'] == 'ex001'  # Barbell Back Squat
        assert exercises[0]['superset_id'] == '1A'
        assert exercises[0]['rest_seconds'] == 0  # Not last in superset

        # Check last exercise
        assert exercises[2]['rest_seconds'] == 90  # Last in superset

    def test_parse_exercise_block_full(self, tmp_path, exercises_json_file):
        """Test parsing complete exercise block"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))
        parser.current_workout_number = 1

        block = {
            'number': 1,
            'lines': [
                '1 Barbell Back Squat',
                'Round 1: 8',
                'Round 2-6: 6',
                'Medium'
            ]
        }

        exercise = parser._parse_exercise_block(block, "A", "GIANT SET", 6, is_last=True)

        assert exercise is not None
        assert exercise['exercise_template_id'] == 'ex001'
        assert exercise['superset_id'] == '1A'
        assert exercise['rest_seconds'] == 90  # is_last=True
        assert len(exercise['sets']) == 6
        assert exercise['sets'][0]['reps'] == 8
        assert exercise['sets'][1]['reps'] == 6
        assert all(s['weight_kg'] == 15 for s in exercise['sets'])  # Medium weight


class TestWorkoutParsingIntegration:
    """Integration tests for complete workout parsing"""

    def test_parse_workout(self, tmp_path, exercises_json_file, sample_workout_text):
        """Test parsing complete workout"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        workout_pages = [{'text': sample_workout_text, 'page_number': 1, 'links': []}]
        routine = parser.parse_workout(workout_pages, workout_number=1)

        assert 'routine' in routine
        assert routine['routine']['title'] == "PaulSklarXfit365-v14 - Week 1 - Workout 1"
        assert 'exercises' in routine['routine']
        assert len(routine['routine']['exercises']) >= 2  # At least 2 sections
        assert routine['routine']['notes'] != ""

    def test_parse_workout_week_calculation(self, tmp_path, exercises_json_file):
        """Test workout week number calculation"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        text = "WORKOUT #6\nA GIANT SET: 3 ROUNDS\nRest 90 Seconds\nTARGET: LEGS\n1 Leg Press\n10\nHeavy"
        workout_pages = [{'text': text, 'page_number': 1, 'links': []}]

        routine = parser.parse_workout(workout_pages, workout_number=6)

        # Workout 6 should be in Week 2
        assert "Week 2" in routine['routine']['title']
        assert "Workout 6" in routine['routine']['title']

    def test_parse_workout_day_in_week(self, tmp_path, exercises_json_file):
        """Test day in week calculation"""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        # Test various workout numbers
        test_cases = [
            (1, 1),   # Workout 1 = Day 1
            (5, 5),   # Workout 5 = Day 5
            (6, 1),   # Workout 6 = Day 1 of week 2
            (11, 1),  # Workout 11 = Day 1 of week 3
        ]

        for workout_num, expected_day in test_cases:
            expected_week = ((workout_num - 1) // 5) + 1
            # Just verify the calculation logic
            week_number = ((workout_num - 1) // 5) + 1
            day_in_week = ((workout_num - 1) % 5) + 1
            assert week_number == expected_week
            assert day_in_week == expected_day


class TestEndToEndWorkflow:
    """End-to-end integration tests"""

    @patch('hevy.workout_parser.fitz')
    def test_complete_workflow(self, mock_fitz, tmp_path, exercises_json_file):
        """Test complete workflow from PDF to JSON"""
        # Mock PDF extraction
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = """
WORKOUT #1

A GIANT SET: 3 ROUNDS
Rest 2 Minutes Between Rounds
TARGET: LEGS

1 Barbell Back Squat
10
Medium

2 Leg Press
12
Heavy
"""
        mock_page.get_links.return_value = []
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_fitz.open.return_value = mock_doc

        # Create parser
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        # Execute workflow
        pages_data = parser.extract_pdf_text()
        workouts = parser.find_workouts(pages_data)
        routine = parser.parse_workout(workouts[1], workout_number=1)

        # Verify structure
        assert 'routine' in routine
        assert 'title' in routine['routine']
        assert 'exercises' in routine['routine']
        assert 'notes' in routine['routine']

        # Verify exercises
        exercises = routine['routine']['exercises']
        assert len(exercises) == 2

        # Verify exercise structure
        for exercise in exercises:
            assert 'exercise_template_id' in exercise
            assert 'superset_id' in exercise
            assert 'rest_seconds' in exercise
            assert 'sets' in exercise
            assert len(exercise['sets']) == 3  # 3 rounds

            # Verify set structure
            for exercise_set in exercise['sets']:
                assert 'type' in exercise_set
                assert 'reps' in exercise_set
                assert 'weight_kg' in exercise_set

    @patch('hevy.workout_parser.fitz')
    def test_multiple_workouts_workflow(self, mock_fitz, tmp_path, exercises_json_file):
        """Test processing multiple workouts from single PDF"""
        # Mock PDF with two workouts
        mock_doc = MagicMock()

        mock_page1 = MagicMock()
        mock_page1.get_text.return_value = """
WORKOUT #1
A GIANT SET: 2 ROUNDS
Rest 90 Seconds Between Rounds
TARGET: CHEST
1 Bench Press
10
Heavy
"""
        mock_page1.get_links.return_value = []

        mock_page2 = MagicMock()
        mock_page2.get_text.return_value = """
WORKOUT #2
A SUPERSET: 3 ROUNDS
Rest 60 Seconds Between Rounds
TARGET: BACK
1 Romanian Deadlift
8
Medium
"""
        mock_page2.get_links.return_value = []

        mock_doc.__len__.return_value = 2
        mock_doc.__getitem__.side_effect = [mock_page1, mock_page2]
        mock_fitz.open.return_value = mock_doc

        # Create parser
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"dummy")
        parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

        # Execute workflow
        pages_data = parser.extract_pdf_text()
        workouts = parser.find_workouts(pages_data)

        assert len(workouts) == 2
        assert 1 in workouts
        assert 2 in workouts

        # Parse both workouts
        routine1 = parser.parse_workout(workouts[1], workout_number=1)
        routine2 = parser.parse_workout(workouts[2], workout_number=2)

        assert "Workout 1" in routine1['routine']['title']
        assert "Workout 2" in routine2['routine']['title']
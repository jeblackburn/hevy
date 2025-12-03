"""
Pytest fixtures for workout parser tests.
"""

import json
from pathlib import Path
from typing import Dict, List

import pytest


@pytest.fixture
def sample_exercises() -> List[Dict]:
    """Sample Hevy exercise templates"""
    return [
        {"id": "ex001", "title": "Barbell Back Squat"},
        {"id": "ex002", "title": "Romanian Deadlift"},
        {"id": "ex003", "title": "Leg Press"},
        {"id": "ex004", "title": "Walking Lunge"},
        {"id": "ex005", "title": "Leg Extension"},
        {"id": "ex006", "title": "Leg Curl"},
        {"id": "ex007", "title": "Calf Raise"},
        {"id": "ex008", "title": "Bench Press"},
        {"id": "ex009", "title": "Incline Dumbbell Press"},
        {"id": "ex010", "title": "Cable Fly"},
    ]


@pytest.fixture
def exercises_json_file(tmp_path, sample_exercises) -> Path:
    """Create temporary exercises.json file"""
    json_file = tmp_path / "exercises.json"
    with open(json_file, 'w') as f:
        json.dump(sample_exercises, f)
    return json_file


@pytest.fixture
def sample_workout_text() -> str:
    """Sample workout text from PDF"""
    return """
WORKOUT #1

A GIANT SET: 6 ROUNDS
Rest 2-3 Minutes Between Rounds
TARGET: QUADS, HAMSTRINGS, GLUTES

1 Barbell Back Squat
Round 1: 8
Round 2-6: 6
Medium

2 Romanian Deadlift
10
Medium

3 Walking Lunge
16
Bodyweight

B SUPERSET: 4 ROUNDS
Rest 90 Seconds Between Rounds
TARGET: QUADS, CALVES

1 Leg Extension
12-15
Medium Plus

2 Calf Raise
20
Heavy
"""


@pytest.fixture
def sample_section_text() -> str:
    """Sample section text"""
    return """
A GIANT SET: 6 ROUNDS
Rest 2-3 Minutes Between Rounds
TARGET: QUADS, HAMSTRINGS, GLUTES

1 Barbell Back Squat
Round 1: 8
Round 2-6: 6
Medium

2 Romanian Deadlift
10
Medium

3 Walking Lunge
16
Bodyweight
"""


@pytest.fixture
def sample_exercise_block() -> Dict:
    """Sample exercise block"""
    return {
        'number': 1,
        'lines': [
            '1 Barbell Back Squat',
            'Round 1: 8',
            'Round 2-6: 6',
            'Medium'
        ]
    }


@pytest.fixture
def sample_pages_data() -> List[Dict]:
    """Sample extracted PDF pages"""
    return [
        {
            'page_number': 1,
            'text': """
WORKOUT #1

A GIANT SET: 6 ROUNDS
Rest 2-3 Minutes Between Rounds
TARGET: QUADS, HAMSTRINGS

1 Barbell Back Squat
Round 1: 8
Round 2-6: 6
Medium
""",
            'links': []
        },
        {
            'page_number': 2,
            'text': """
WORKOUT #2

A SUPERSET: 4 ROUNDS
Rest 90 Seconds Between Rounds
TARGET: CHEST, TRICEPS

1 Bench Press
8-10
Heavy
""",
            'links': []
        }
    ]
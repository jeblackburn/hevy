"""
Data models for workout parsing.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExerciseSet(BaseModel):
    """Represents a single set of an exercise"""
    type: str = "normal"
    weight_kg: Optional[float] = None
    reps: Optional[int] = None
    distance_meters: Optional[float] = None
    duration_seconds: Optional[int] = None
    custom_metric: Optional[str] = None
    rep_range: Optional[Dict[str, int]] = None


class Exercise(BaseModel):
    """Represents an exercise within a routine"""
    exercise_template_id: str
    superset_id: Optional[str] = None
    rest_seconds: int = 0
    notes: Optional[str] = None
    sets: List[Dict[str, Any]] = Field(default_factory=list)


class WorkoutSection(BaseModel):
    """Represents a section (A, B, C, etc.) within a workout"""
    section_id: str
    section_type: str  # GIANT SET, SUPERSET, FINISHER, SEQUENCE
    rounds: int
    rest_between_rounds: int
    target: str
    exercises: List[Dict[str, Any]]
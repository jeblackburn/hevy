"""
Data models for workout parsing.
"""
from datetime import datetime
from enum import StrEnum, auto, IntEnum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, PastDatetime


class RepRange(BaseModel):
    start: int
    end: int

class ExerciseSetType(StrEnum):
    normal = auto()
    warmup = auto()
    dropset = auto()
    failure = auto()



class ExerciseSet(BaseModel):
    index: int
    type: ExerciseSetType
    weight_kg: Optional[float]
    reps: Optional[int]
    rep_range: Optional[RepRange]
    distance_meters: Optional[int]
    duration_seconds: Optional[int]
    rpe: Optional[float]
    custom_metric: Optional[int]


class Exercise(BaseModel):
    """Represents an exercise within a routine"""
    exercise_template_id: str
    superset_id: Optional[str]
    rest_seconds: int = 0
    notes: Optional[str]
    sets: List[ExerciseSet] = Field(default_factory=list)


class SuperSet(BaseModel):
    superset_id: int
    section_type: str  # GIANT SET, SUPERSET, FINISHER, SEQUENCE
    rounds: int
    rest_between_rounds: int
    target: str
    exercises: List[Exercise]

class Routine(BaseModel):
    id: str
    title: str # e.g. "Week 1 Workout 1"
    folder_id: int
    updated_at: PastDatetime
    created_at: PastDatetime
    exercises: List[SuperSet]

class Week(IntEnum):
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4

class MonthlyWorkoutSchedule(BaseModel):
    RoutinesByWeek: dict[Week, List[Routine]]
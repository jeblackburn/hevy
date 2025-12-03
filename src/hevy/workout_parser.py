"""
PDF Workout Parser for Hevy API.

This module contains the main parser class for extracting workout data from PDFs.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF
from fuzzywuzzy import fuzz, process

from .model import ExerciseSet, WorkoutSection


# Weight conversion mapping from PLAN.md
WEIGHT_MAPPING = {
    "medium": 15,
    "medium plus": 20,
    "heavy": 40,
    "bodyweight": 0,
    "light": 10,
    "light/medium": 12.5,
    "medium to moderate": 17.5,
    "medium or medium plus": 17.5,
    "medium plus or heavy": 30,
    "as heavy as possible": None,
    "as heavy as possible to complete": None,
    "as heavy as necessary to complete rep count": None,
}


class PDFWorkoutParser:
    """Main parser class for extracting workout data from PDF"""

    def __init__(self, pdf_path: str, exercises_json_path: str):
        self.pdf_path = Path(pdf_path)
        self.exercises = self._load_exercises(exercises_json_path)
        self.exercise_titles = {ex['id']: ex['title'] for ex in self.exercises}
        self.current_workout_number = None

    def _load_exercises(self, json_path: str) -> List[Dict]:
        """Load Hevy exercise templates from JSON file"""
        with open(json_path, 'r') as f:
            return json.load(f)

    def extract_pdf_text(self) -> List[Dict]:
        """Extract text from all pages of the PDF"""
        doc = fitz.open(self.pdf_path)
        pages_data = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            pages_data.append({
                'page_number': page_num + 1,
                'text': page.get_text(),
                'links': page.get_links()
            })

        doc.close()
        return pages_data

    def find_workouts(self, pages_data: List[Dict]) -> Dict[int, List[Dict]]:
        """
        Segment pages by workout number.
        Returns: {workout_number: [page_data, ...]}
        """
        workouts = {}
        current_workout = None

        for page_data in pages_data:
            text = page_data['text']

            # Look for workout header
            workout_match = re.search(r'WORKOUT\s*#(\d+)', text, re.IGNORECASE)
            if workout_match:
                current_workout = int(workout_match.group(1))
                if current_workout not in workouts:
                    workouts[current_workout] = []

            # Add page to current workout if we're in one
            if current_workout is not None:
                workouts[current_workout].append(page_data)

        return workouts

    def parse_workout(self, workout_pages: List[Dict], workout_number: int) -> Dict:
        """Parse a complete workout from its pages"""
        self.current_workout_number = workout_number

        # Combine all text from workout pages
        full_text = "\n".join(page['text'] for page in workout_pages)

        # Extract workout metadata
        week_number = ((workout_number - 1) // 5) + 1
        day_in_week = ((workout_number - 1) % 5) + 1

        # Parse sections (A, B, C, etc.)
        sections = self._parse_sections(full_text)

        # Convert to Hevy routine format
        routine = self._build_routine(
            workout_number=workout_number,
            week_number=week_number,
            day_in_week=day_in_week,
            sections=sections
        )

        return routine

    def _parse_sections(self, text: str) -> List[WorkoutSection]:
        """Parse all sections (A, B, C, etc.) from workout text"""
        sections = []

        # Pattern to find section headers
        # Example: "A GIANT SET: 6 ROUNDS"
        section_pattern = r'([A-Z])\s+(GIANT SET|SUPERSET|FINISHER|SEQUENCE):\s*(\d+)\s+ROUNDS?'

        section_matches = list(re.finditer(section_pattern, text, re.IGNORECASE))

        for i, match in enumerate(section_matches):
            section_id = match.group(1)
            section_type = match.group(2)
            rounds = int(match.group(3))

            # Extract text for this section (until next section or end)
            start_pos = match.end()
            end_pos = section_matches[i + 1].start() if i + 1 < len(section_matches) else len(text)
            section_text = text[start_pos:end_pos]

            # Parse rest period
            rest_seconds = self._parse_rest_period(section_text)

            # Parse target muscle groups
            target = self._parse_target(section_text)

            # Parse exercises in this section
            exercises = self._parse_exercises(section_text, section_id, section_type, rounds)

            section = WorkoutSection(
                section_id=section_id,
                section_type=section_type,
                rounds=rounds,
                rest_between_rounds=rest_seconds,
                target=target,
                exercises=exercises
            )
            sections.append(section)

        return sections

    def _parse_rest_period(self, text: str) -> int:
        """Parse rest period from section text and convert to seconds"""
        # Look for patterns like "Rest 2-3 Minutes Between Rounds"
        rest_pattern = r'Rest\s+(\d+)(?:-(\d+))?\s+(Minutes?|Seconds?)'
        match = re.search(rest_pattern, text, re.IGNORECASE)

        if match:
            min_time = int(match.group(1))
            max_time = int(match.group(2)) if match.group(2) else min_time
            unit = match.group(3).lower()

            # Use midpoint
            avg_time = (min_time + max_time) / 2

            # Convert to seconds
            if 'minute' in unit:
                return int(avg_time * 60)
            else:
                return int(avg_time)

        return 90  # Default from PLAN.md

    def _parse_target(self, text: str) -> str:
        """Parse target muscle groups from section text"""
        target_pattern = r'TARGET:\s*([A-Z\s,/]+)'
        match = re.search(target_pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""

    def _parse_exercises(self, section_text: str, section_id: str,
                        section_type: str, rounds: int) -> List[Dict]:
        """Parse exercises from a section"""
        exercises = []

        # Find the table or list of exercises
        # Look for numbered exercises: "1 Exercise Name"
        exercise_pattern = r'(\d+)\s+([A-Z][^\n]+?)(?:\s+(\d+|[\d-]+|Round\s+\d+[^\n]+?))\s+(Medium|Heavy|Bodyweight|Light|[^\n]+?weight[^\n]*?)\s*\n'

        # More robust: find exercise blocks
        lines = section_text.split('\n')
        current_exercise = None
        exercise_blocks = []

        for line in lines:
            # Check if line starts with a number (exercise number)
            num_match = re.match(r'^(\d+)\s+(.+)', line.strip())
            if num_match:
                if current_exercise:
                    exercise_blocks.append(current_exercise)
                current_exercise = {
                    'number': int(num_match.group(1)),
                    'lines': [line]
                }
            elif current_exercise and line.strip():
                current_exercise['lines'].append(line)

        if current_exercise:
            exercise_blocks.append(current_exercise)

        # Parse each exercise block
        for block in exercise_blocks:
            exercise = self._parse_exercise_block(
                block,
                section_id,
                section_type,
                rounds,
                is_last=(block == exercise_blocks[-1])
            )
            if exercise:
                exercises.append(exercise)

        return exercises

    def _parse_exercise_block(self, block: Dict, section_id: str,
                              section_type: str, rounds: int, is_last: bool) -> Optional[Dict]:
        """Parse a single exercise block"""
        block_text = '\n'.join(block['lines'])

        # Extract exercise name (first line, after number)
        first_line = block['lines'][0]
        name_match = re.match(r'^\d+\s+(.+?)(?:\s+Round|\s+\d+|\s*$)', first_line.strip())
        if not name_match:
            return None

        exercise_name = name_match.group(1).strip()

        # Match to Hevy exercise template
        template_id, confidence = self._match_exercise_name(exercise_name)
        if confidence < 70:  # Low confidence
            print(f"Warning: Low confidence match for '{exercise_name}': {confidence}%")

        # Parse reps and weight information
        reps_data = self._parse_reps_from_block(block_text, rounds)
        weight_data = self._parse_weight_from_block(block_text, rounds)
        notes = self._extract_notes_from_block(block_text)

        # Generate sets
        sets = self._generate_sets(reps_data, weight_data, rounds)

        # Create superset_id
        superset_id = f"{self.current_workout_number}{section_id}"

        # Determine rest seconds based on superset rules
        rest_seconds = 90 if is_last else 0

        exercise = {
            'exercise_template_id': template_id,
            'superset_id': superset_id,
            'rest_seconds': rest_seconds,
            'notes': notes,
            'sets': [s.model_dump() for s in sets]
        }

        return exercise

    def _match_exercise_name(self, pdf_name: str) -> Tuple[str, int]:
        """
        Match PDF exercise name to Hevy exercise template.
        Returns: (exercise_template_id, confidence_score)
        """
        # Clean the name
        pdf_name = pdf_name.strip()
        pdf_name = re.sub(r'\s+', ' ', pdf_name)

        # Try exact match first
        for template_id, title in self.exercise_titles.items():
            if pdf_name.lower() == title.lower():
                return template_id, 100

        # Fuzzy match
        match = process.extractOne(
            pdf_name,
            self.exercise_titles.values(),
            scorer=fuzz.token_sort_ratio
        )

        if match:
            matched_title, score = match[0], match[1]
            matched_id = [k for k, v in self.exercise_titles.items() if v == matched_title][0]
            return matched_id, score

        # Fallback: return first exercise with warning
        print(f"ERROR: Could not match exercise '{pdf_name}'")
        return list(self.exercise_titles.keys())[0], 0

    def _parse_reps_from_block(self, block_text: str, rounds: int) -> List[Optional[int]]:
        """
        Parse reps information from exercise block.
        Returns list of reps for each round.
        """
        reps = [None] * rounds

        # Look for round-specific reps
        # Example: "Round 1: 16" or "Round 1-2: 10"
        round_patterns = [
            r'Round\s+(\d+):\s*(\d+)',
            r'Round\s+(\d+)-(\d+):\s*(\d+)',
            r'Rounds?\s+(\d+)-(\d+):\s*(\d+)',
        ]

        for pattern in round_patterns:
            for match in re.finditer(pattern, block_text, re.IGNORECASE):
                if len(match.groups()) == 2:  # Single round
                    round_num = int(match.group(1))
                    rep_count = int(match.group(2))
                    if 1 <= round_num <= rounds:
                        reps[round_num - 1] = rep_count
                elif len(match.groups()) == 3:  # Range of rounds
                    start_round = int(match.group(1))
                    end_round = int(match.group(2))
                    rep_count = int(match.group(3))
                    for r in range(start_round, end_round + 1):
                        if 1 <= r <= rounds:
                            reps[r - 1] = rep_count

        # Look for simple rep count (applies to all rounds)
        simple_rep_match = re.search(r'^\s*(\d+)\s*$', block_text, re.MULTILINE)
        if simple_rep_match and all(r is None for r in reps):
            rep_count = int(simple_rep_match.group(1))
            reps = [rep_count] * rounds

        # Look for rep ranges: "8-10" or "6-10"
        rep_range_match = re.search(r'(\d+)-(\d+)(?!\s*Minutes?)', block_text)
        if rep_range_match and all(r is None for r in reps):
            # Use midpoint of range
            start = int(rep_range_match.group(1))
            end = int(rep_range_match.group(2))
            midpoint = (start + end) // 2
            reps = [midpoint] * rounds

        return reps

    def _parse_weight_from_block(self, block_text: str, rounds: int) -> List[Optional[float]]:
        """
        Parse weight information from exercise block.
        Returns list of weights (in kg) for each round.
        """
        weights = [None] * rounds

        # Look for round-specific weights
        # Use [A-Za-z ]+ instead of [A-Za-z\s]+ to avoid matching newlines
        round_weight_pattern = r'Round[s]?\s+(\d+)(?:-(\d+))?:\s*([A-Za-z ]+?)(?:\n|$|(?=\s*(?:Round|\d+)))'

        for match in re.finditer(round_weight_pattern, block_text, re.IGNORECASE):
            start_round = int(match.group(1))
            end_round = int(match.group(2)) if match.group(2) else start_round
            weight_desc = match.group(3).strip().lower()

            weight_kg = self._convert_weight_to_kg(weight_desc)

            for r in range(start_round, end_round + 1):
                if 1 <= r <= rounds:
                    weights[r - 1] = weight_kg

        # Look for general weight description
        if all(w is None for w in weights):
            # Search for weight keywords
            for weight_key, weight_val in WEIGHT_MAPPING.items():
                if weight_key in block_text.lower():
                    weights = [weight_val] * rounds
                    break

        return weights

    def _convert_weight_to_kg(self, weight_desc: str) -> Optional[float]:
        """Convert weight description to kg value"""
        weight_desc = weight_desc.lower().strip()

        # Direct lookup
        if weight_desc in WEIGHT_MAPPING:
            return WEIGHT_MAPPING[weight_desc]

        # Fuzzy match - check longer keys first to prefer specific matches
        # Sort keys by length descending so "medium plus" is checked before "medium"
        for key in sorted(WEIGHT_MAPPING.keys(), key=len, reverse=True):
            if key in weight_desc or weight_desc in key:
                return WEIGHT_MAPPING[key]

        return None

    def _extract_notes_from_block(self, block_text: str) -> Optional[str]:
        """Extract special notes or instructions from exercise block"""
        notes = []

        # Look for parenthetical notes
        paren_notes = re.findall(r'\([^)]+\)', block_text)
        notes.extend(paren_notes)

        # Look for instruction keywords
        instruction_keywords = ['contract', 'pause', 'hold', 'squeeze', 'slow', 'controlled']
        for keyword in instruction_keywords:
            if keyword in block_text.lower():
                # Extract sentence containing keyword
                sentences = re.split(r'[.!?]', block_text)
                for sentence in sentences:
                    if keyword in sentence.lower():
                        notes.append(sentence.strip())

        return '; '.join(notes) if notes else None

    def _generate_sets(self, reps_data: List[Optional[int]],
                       weight_data: List[Optional[float]],
                       rounds: int) -> List[ExerciseSet]:
        """Generate set objects from reps and weight data"""
        sets = []

        for i in range(rounds):
            exercise_set = ExerciseSet(
                type="normal",
                weight_kg=weight_data[i] if i < len(weight_data) else None,
                reps=reps_data[i] if i < len(reps_data) else None,
            )
            sets.append(exercise_set)

        return sets

    def _build_routine(self, workout_number: int, week_number: int,
                      day_in_week: int, sections: List[WorkoutSection]) -> Dict:
        """Build final Hevy routine JSON structure"""
        # Flatten all exercises from all sections
        all_exercises = []
        for section in sections:
            all_exercises.extend(section.exercises)

        # Create title
        title = f"PaulSklarXfit365-v14 - Week {week_number} - Workout {workout_number}"

        # Build routine
        routine = {
            "routine": {
                "title": title,
                "folder_id": None,  # Will be set when uploading
                "notes": self._build_workout_notes(sections),
                "exercises": all_exercises
            }
        }

        return routine

    def _build_workout_notes(self, sections: List[WorkoutSection]) -> str:
        """Build notes summary from sections"""
        notes_parts = []

        for section in sections:
            section_note = f"Section {section.section_id}: {section.section_type} - {section.rounds} rounds"
            if section.target:
                section_note += f" (Target: {section.target})"
            notes_parts.append(section_note)

        return "\n".join(notes_parts)
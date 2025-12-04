"""
LLM-based PDF Workout Parser for Hevy API.

This module uses LiteLLM to send PDF content to an LLM for structured extraction.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

import fitz  # PyMuPDF
from dotenv import load_dotenv
from litellm import completion

load_dotenv()

class LLMWorkoutParser:
    """LLM-based parser for extracting workout data from PDFs"""

    def __init__(self, pdf_path: str, exercises_json_path: str, model: str = "claude-3-5-sonnet-20241022", api_key: Optional[str] = None):
        self.pdf_path = Path(pdf_path)
        self.exercises = self._load_exercises(exercises_json_path)
        self.model = model

        # Create exercise lookup for fuzzy matching
        self.exercise_titles = {ex['id']: ex['title'] for ex in self.exercises}

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

            # Look for workout header - try various patterns
            workout_match = re.search(r'WORKOUT\s*#?(\d+)', text, re.IGNORECASE)
            if workout_match:
                current_workout = int(workout_match.group(1))
                if current_workout not in workouts:
                    workouts[current_workout] = []

            # Add page to current workout if we're in one
            if current_workout is not None:
                workouts[current_workout].append(page_data)

        return workouts

    def parse_workout_with_llm(self, workout_pages: List[Dict], workout_number: int) -> Dict:
        """Parse a workout using LLM to extract structured data"""

        # Combine all text from workout pages
        full_text = "\n\n".join(f"--- Page {page['page_number']} ---\n{page['text']}"
                                for page in workout_pages)

        # Calculate week and day
        week_number = ((workout_number - 1) // 5) + 1
        day_in_week = ((workout_number - 1) % 5) + 1

        # Create the prompt for the LLM
        prompt = self._create_parsing_prompt(full_text, workout_number, week_number)

        # Call LLM
        response = completion(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a fitness data extraction expert. Extract workout information from PDFs into structured JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,  # Low temperature for consistent extraction
        )

        # Parse the LLM response
        llm_output = response.choices[0].message.content

        # Extract JSON from the response (handle markdown code blocks)
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', llm_output, re.DOTALL)
        if json_match:
            workout_data = json.loads(json_match.group(1))
        else:
            # Try to parse the entire response as JSON
            workout_data = json.loads(llm_output)

        # Build the final routine structure
        routine = {
            "routine": {
                "title": f"PaulSklarXfit365-v14 - Week {week_number} - Workout {workout_number}",
                "folder_id": None,
                "notes": workout_data.get("notes", ""),
                "exercises": workout_data.get("exercises", [])
            }
        }

        return routine

    def _create_parsing_prompt(self, workout_text: str, workout_number: int, week_number: int) -> str:
        """Create the prompt for LLM to parse workout data"""

        # Create a simplified exercise list for the LLM
        exercise_list = "\n".join([f"- {ex['title']} (ID: {ex['id']})"
                                   for ex in self.exercises[:50]])  # Limit to first 50 to save tokens

        prompt = f"""
Extract the workout routine from the following PDF text and convert it to JSON format.

**Workout Information:**
- Workout Number: {workout_number}
- Week: {week_number}

**Available Exercise Templates (use these IDs):**
{exercise_list}

**Weight Conversion Table:**
- "Medium" = 15 kg
- "Medium Plus" = 20 kg
- "Heavy" = 40 kg
- "Bodyweight" = 0 kg
- "Light" = 10 kg
- "Challenge" = null (user should determine)

**Instructions:**
1. Extract all exercises from the workout
2. For each exercise, match it to the closest exercise template ID from the list above
3. Extract sets, reps, and weights for each exercise
4. Group exercises by their section (A, B, C, D, etc.) using the same superset_id
5. For rest times: within a superset/giant set, all exercises except the last should have rest_seconds=0. The last exercise should have rest_seconds=90 (or the value from the PDF)
6. Convert weight descriptions to kg values using the table above

**Output Format (JSON only, no other text):**
{{
  "notes": "Brief summary of the workout sections",
  "exercises": [
    {{
      "exercise_template_id": "EXERCISE_ID",
      "superset_id": "SECTION_LETTER",
      "rest_seconds": 0 or 90,
      "notes": "any specific instructions for this exercise",
      "sets": [
        {{
          "type": "normal",
          "weight_kg": 15.0,
          "reps": 10
        }}
      ]
    }}
  ]
}}

**PDF Text:**
{workout_text}

Extract the workout and return ONLY the JSON object (wrapped in ```json code block).
"""
        return prompt

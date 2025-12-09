"""
LLM-based PDF Workout Parser for Hevy API.

This module uses LiteLLM to send PDF content to an LLM for structured extraction.
"""

import json
import os
from typing import Dict, List, Optional

from dotenv import load_dotenv
from litellm import completion
from litellm.utils import supports_pdf_input

from src.hevy.model import MonthlyWorkoutSchedule

load_dotenv()

class LLMWorkoutParser:
    """LLM-based parser for extracting workout data from PDFs"""

    def __init__(self, exercises_json_path: str, api_key: Optional[str] = None):
        self.exercises = self._load_exercises(exercises_json_path)
        model = os.getenv("MODEL_NAME")
        print("Using LiteLLM model: {}".format(model))
        self.model = model

        # Create exercise lookup for fuzzy matching
        self.exercise_titles = {ex['id']: ex['title'] for ex in self.exercises}

    def _load_exercises(self, json_path: str) -> List[Dict]:
        """Load Hevy exercise templates from JSON file"""
        with open(json_path, 'r') as f:
            return json.load(f)

    def parse_workout_with_llm(self, pdf_url: str, ) -> MonthlyWorkoutSchedule:
        """Parse a workout using LLM to extract structured data"""

        # Create the parsing prompt
        prompt = self._create_parsing_prompt()

        # Check if model supports PDF input
        if not supports_pdf_input(self.model, None):
            raise ValueError(f"Model {self.model} does not support PDF input")

        # Create file content with PDF URL
        file_content = [
            {
                "type": "file",
                "file": {
                    "file_data": pdf_url,
                }
            },
        ]

        # Call LLM with PDF URL and prompt
        response = completion(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a fitness data extraction expert. Extract workout information from PDFs into structured JSON format."
                },
                {
                    "role": "user",
                    "content": file_content
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            response_format=MonthlyWorkoutSchedule,
        )

        # Parse the LLM response
        llm_output = response.choices[0].message.content
        return MonthlyWorkoutSchedule.model_validate_json(llm_output)

    def _create_parsing_prompt(self) -> str:
        """Create the prompt for LLM to parse workout data"""

        # Create a simplified exercise list for the LLM
        exercise_list = "\n".join([f"- {ex['title']} (ID: {ex['id']})"
                                   for ex in self.exercises[:50]])  # Limit to first 50 to save tokens

        prompt = f"""
This PDF file contains a series of 20 strength training routines. They are organized into 4 weeks, 5 Routines per week.
Extract the workout routines from the PDF and convert them to JSON format.

** Exercises **
{exercise_list}

**Weight Conversion Table:**
- "Medium" = 15 kg
- "Medium Plus" = 20 kg
- "Heavy" = 40 kg
- "Bodyweight" = 0 kg
- "Light" = 10 kg
- "Challenge" = null (user should determine)

**Instructions:**
1. Extract all exercises from the workout. Each workout should have at least three SuperSets, each of them containing at least three exercises. 
   Continue to iterate util all exercises have been read from the PDF.
2. For each exercise, match it to the closest exercise template ID from the list above
3. Extract sets, reps, and weights for each exercise
4. Group exercises by their section (A, B, C, D, etc.) using the same superset_id
5. For rest times: within a superset/giant set, all exercises except the last should have rest_seconds=0. The last exercise should have rest_seconds=90 (or the value from the PDF)
6. Convert weight descriptions to kg values using the table above


The response should adhere to the requested format. Return only the JSON, no extra text. Do NOT quote-enclose the output JSON.
"""
        return prompt

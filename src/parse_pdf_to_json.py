"""
CLI tool for parsing workout PDFs to JSON format.

This script parses PaulSklarXfit workout PDFs and converts them to JSON format
compatible with the Hevy API.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from src.hevy.model import MonthlyWorkoutSchedule

load_dotenv()

from hevy.llm_workout_parser import LLMWorkoutParser

PDF_URLS = [
    ("PaulSklarXfit365-Monthly-Program-v5", "https://drive.google.com/file/d/1UgMSGt44QzCdcFtbrNQmQlZitleDPXXq/view?usp=sharing"),
    ("PaulSklarXfit365-Monthly-Programming-v71", "https://drive.google.com/file/d/1zhdx9O7nkBOVSVDZC998wuqERhCs9b6q/view?usp=sharing"),
    ("PaulSklarXfit365-V10", "https://drive.google.com/file/d/1PP2vjB56JpVTd7EWGZ42AV7Hoek4O3NW/view?usp=sharing"),
    ("PaulSklarXfit365-v12_2020-06", "https://drive.google.com/file/d/1TgSGDtWyyrygXs_MMii-V12BVxAPi6z3/view?usp=sharing"),
    ("PaulSklarXfit365-v14", "https://drive.google.com/file/d/1jgm4K5orULFctIMn7hUhXmREUwbHDOER/view?usp=sharing"),
]


def get_folder_id(folders_data: dict, program_name: str, week_id: str) -> int | None:
    """
    Look up the folder ID for a given program and week.

    Args:
        folders_data: Dictionary loaded from hevy_folders.json
        program_name: Name of the program (e.g., "PaulSklarXfit365-v14")
        week_num: Week number (1-4)

    Returns:
        The folder ID, or None if not found
    """
    if program_name in folders_data and week_id in folders_data[program_name]:
        return folders_data[program_name][week_id]["routine_folder"]["id"]
    return None


def parse_pdf_to_json(exercises_json_path: str, output_dir: str, folders_json_path: str):
    """
    Main function to parse PDF and generate JSON files.

    Args:
        pdf_path: Path to the workout PDF
        exercises_json_path: Path to exercises.json with Hevy templates
        output_dir: Directory to save output JSON files
        folders_json_path: Path to hevy_folders.json with folder IDs
    """
    # Load folder data
    with open(folders_json_path, 'r') as f:
        folders_data = json.load(f)

    parser = LLMWorkoutParser(exercises_json_path)

    # Create output directory structure
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for (pdf_name, pdf_url) in PDF_URLS:
        print(f"\nParsing Workout {pdf_name}...")

        month_schedule = parser.parse_workout_with_llm(pdf_url)

        save_routine(folders_data, month_schedule, output_path, pdf_name)


    print(f"\n✓ Parsing complete! Generated workout JSON files")
    print(f"✓ Output directory: {output_path}")


def save_routine(folders_data, month_schedule: MonthlyWorkoutSchedule, output_path: Path, pdf_name: str):
    for week_id in month_schedule.RoutinesByWeek:
        routine = month_schedule.RoutinesByWeek[week_id]
        routine.folder_id = get_folder_id(folders_data, program_name=pdf_name, week_id=week_id)
        week_id_path = week_id.replace(" ", "_")
        week_dir_path = output_path / pdf_name / week_id_path
        os.makedirs(week_dir_path, exist_ok=True)
        output_file = week_dir_path / f"{week_id_path}.json"
        with open(output_file, 'w') as f:
            json.dump(routine.model_dump(mode='json'), f)
        print(f"  Saved to {output_file}")


if __name__ == "__main__":
    # Configuration
    EXERCISES_JSON = "exercises.json"
    FOLDERS_JSON = "hevy_folders.json"
    OUTPUT_DIR = "output"

    # Parse PDF to JSON
    parse_pdf_to_json(EXERCISES_JSON, OUTPUT_DIR, FOLDERS_JSON)

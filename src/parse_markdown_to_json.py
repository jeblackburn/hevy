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

# MARKDOWN_FILES = [
#     ("Workouts/PaulSklarXfit365-V10.md", "PaulSklarXfit365-V10"),
#     ("Workouts/PaulSklarXfit365-v12_2020-06.md", "PaulSklarXfit365-v12_2020-06"),
#     ("Workouts/PaulSklarXfit365-v14.md", "PaulSklarXfit365-v14"),
# ]


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


def parse_markdown_to_json(markdowns, exercises_json_path: str, output_dir: str, folders_json_path: str):
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

    for (markdown_filename, routine_name) in markdowns:
        print(f"\nParsing Workout {markdown_filename}...")

        month_schedule = parser.parse_markdown_with_llm(markdown_filename, routine_name)

        save_routine(folders_data, month_schedule, output_path, routine_name)


    print(f"\n✓ Parsing complete! Generated workout JSON files")
    print(f"✓ Output directory: {output_path}")


def save_routine(folders_data, month_schedule: MonthlyWorkoutSchedule, output_path: Path, routine_name: str):
    for week, routines in month_schedule.RoutinesByWeek.items():
        week_id = f"Week {week}"
        for routine in routines:
            routine.folder_id = get_folder_id(folders_data, program_name=routine_name, week_id=week_id)
        week_id_path = f"Week_{week}"
        week_dir_path = output_path / routine_name / week_id_path
        os.makedirs(week_dir_path, exist_ok=True)
        output_file = week_dir_path / f"{week_id_path}.json"
        with open(output_file, 'w') as f:
            routines_dicts = [r.model_dump() for r in routines]
            json.dump(routines_dicts, f, indent=4, default=str)
        print(f"  Saved to {output_file}")


if __name__ == "__main__":
    # Configuration
    EXERCISES_JSON = "exercises.json"
    FOLDERS_JSON = "hevy_folders.json"
    OUTPUT_DIR = "output"

    os.makedirs(f"{OUTPUT_DIR}/llm", exist_ok=True)
    markdown_filenames = Path("Workouts")
    markdown_paths = markdown_filenames.glob("*.md")
    just_filenames = [f"Workouts/{p.name}" for p in markdown_paths]
    markdowns = [(fn, fn.split(".")[0].split("/")[1]) for fn in just_filenames]
    print("Parsing Markdown files...", markdowns)

    # Parse MARKDOWN to JSON
    parse_markdown_to_json(markdowns, EXERCISES_JSON, OUTPUT_DIR, FOLDERS_JSON)

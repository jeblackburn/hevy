"""
CLI tool for parsing workout PDFs to JSON format.

This script parses PaulSklarXfit workout PDFs and converts them to JSON format
compatible with the Hevy API.
"""

import json
from pathlib import Path

from hevy.workout_parser import PDFWorkoutParser


def parse_pdf_to_json(pdf_path: str, exercises_json_path: str, output_dir: str):
    """
    Main function to parse PDF and generate JSON files.

    Args:
        pdf_path: Path to the workout PDF
        exercises_json_path: Path to exercises.json with Hevy templates
        output_dir: Directory to save output JSON files
    """
    parser = PDFWorkoutParser(pdf_path, exercises_json_path)

    # Extract pages
    print("Extracting PDF pages...")
    pages_data = parser.extract_pdf_text()

    # Find workouts
    print("Identifying workouts...")
    workouts = parser.find_workouts(pages_data)
    print(f"Found {len(workouts)} workouts")

    # Create output directory structure
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Parse each workout
    all_routines = []
    for workout_num in sorted(workouts.keys()):
        print(f"\nParsing Workout {workout_num}...")

        workout_pages = workouts[workout_num]
        routine = parser.parse_workout(workout_pages, workout_num)

        all_routines.append(routine)

        # Save individual workout JSON
        week_num = ((workout_num - 1) // 5) + 1
        week_dir = output_path / f"week{week_num}"
        week_dir.mkdir(exist_ok=True)

        output_file = week_dir / f"workout{workout_num:02d}.json"
        with open(output_file, 'w') as f:
            json.dump(routine, f, indent=2)

        print(f"  Saved to {output_file}")

    # Save summary metadata
    metadata = {
        "pdf_file": str(Path(pdf_path).name),
        "total_workouts": len(all_routines),
        "weeks": 4,
        "workouts_per_week": 5,
    }

    metadata_file = output_path / "metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"\n✓ Parsing complete! Generated {len(all_routines)} workout JSON files")
    print(f"✓ Output directory: {output_path}")


if __name__ == "__main__":
    # Configuration
    PDF_PATH = "../Workouts/PaulSklarXfit365-v14.pdf"
    EXERCISES_JSON = "../exercises.json"
    OUTPUT_DIR = "output"

    # Parse PDF to JSON
    parse_pdf_to_json(PDF_PATH, EXERCISES_JSON, OUTPUT_DIR)
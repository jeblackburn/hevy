#!/usr/bin/env python3
"""
Convert workout JSON files to Hevy API format.

Reads JSON files from the output directory and transforms them into the format
required by the Hevy.com REST API for posting routines.
"""

import json
from pathlib import Path
from time import sleep
from typing import Any, Dict, List
import requests


def remove_null_values(obj: Any) -> Any:
    """
    Recursively remove all keys with null values from dictionaries.

    Args:
        obj: The object to clean (dict, list, or other)

    Returns:
        The cleaned object with null values removed
    """
    if isinstance(obj, dict):
        return {k: remove_null_values(v) for k, v in obj.items() if v is not None}
    elif isinstance(obj, list):
        return [remove_null_values(item) for item in obj]
    else:
        return obj


def convert_workout_to_api_format(workout: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a single workout from internal format to Hevy API format.

    Args:
        workout: Workout data in internal format

    Returns:
        Dict formatted for Hevy API POST request
    """
    # Step 1: Extract routine metadata (remove generated fields)
    api_routine = {
        "title": workout["title"],
        "folder_id": str(workout["folder_id"]),
        "notes": None
    }

    # Step 2: Flatten SuperSets into exercises
    flat_exercises = []

    for superset in workout["exercises"]:
        # Extract nested exercises from superset wrapper
        for exercise in superset["exercises"]:
            # Step 3: Clean sets (remove index field)
            clean_sets = []
            for set_data in exercise["sets"]:
                # Remove 'index' field and keep all others
                clean_set = {k: v for k, v in set_data.items() if k != "index"}
                clean_sets.append(clean_set)

            # Add flattened exercise
            flat_exercises.append({
                "exercise_template_id": exercise["exercise_template_id"],
                "superset_id": superset.get("superset_id"),
                "rest_seconds": exercise["rest_seconds"],
                "notes": exercise.get("notes"),
                "sets": clean_sets
            })

    api_routine["exercises"] = flat_exercises

    # Step 4: Wrap in API structure and remove null values
    api_response = {"routine": api_routine}
    return remove_null_values(api_response)


def convert_file(json_path: Path) -> List[Dict[str, Any]]:
    """
    Convert all workouts in a JSON file to API format.

    Args:
        json_path: Path to JSON file containing workout data

    Returns:
        List of API payloads, one per workout in the file
    """
    with open(json_path, 'r') as f:
        workouts = json.load(f)

    # Handle both single workout and array of workouts
    if isinstance(workouts, dict):
        workouts = [workouts]

    api_payloads = []
    for workout in workouts:
        api_payload = convert_workout_to_api_format(workout)
        api_payloads.append(api_payload)

    return api_payloads


def find_all_workout_files(output_dir: Path = Path("output")) -> List[Path]:
    """
    Find all workout JSON files in the output directory.

    Args:
        output_dir: Root output directory to search

    Returns:
        List of paths to workout JSON files
    """
    json_files = []

    # Find all JSON files in the output directory structure
    for json_file in output_dir.rglob("*.json"):
        json_files.append(json_file)

    return sorted(json_files)


def post_to_hevy_api(payload: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    """
    POST a routine to the Hevy API.

    Args:
        payload: API payload in correct format
        api_key: Hevy API key

    Returns:
        API response as dict

    Raises:
        requests.HTTPError: If the API request fails
    """
    url = "https://api.hevyapp.com/v1/routines"
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()

    return response.json()


def preview_conversion(json_path: Path, output_path: Path = None):
    """
    Preview the conversion of a single file without posting to API.

    Args:
        json_path: Path to JSON file to convert
        output_path: Optional path to write converted JSON
    """
    print(f"Converting: {json_path}")
    print(f"{'=' * 80}\n")

    api_payloads = convert_file(json_path)

    print(f"Found {len(api_payloads)} workout(s) in file\n")

    for i, payload in enumerate(api_payloads, 1):
        print(f"Workout {i}: {payload['routine']['title']}")
        print(f"  Folder ID: {payload['routine']['folder_id']}")
        print(f"  Exercises: {len(payload['routine']['exercises'])}")

        # Count total sets
        total_sets = sum(len(ex['sets']) for ex in payload['routine']['exercises'])
        print(f"  Total Sets: {total_sets}")

        # Show superset info
        supersets = set(ex['superset_id'] for ex in payload['routine']['exercises']
                       if ex['superset_id'])
        if supersets:
            print(f"  Supersets: {', '.join(str(s) for s in sorted(supersets))}")

        print()

    # Optionally write to file
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(api_payloads, f, indent=2)
        print(f"Converted data written to: {output_path}")

    # Show first payload as example
    print("\nFirst workout API payload:")
    print(json.dumps(api_payloads[0], indent=2))


def post_single_file(json_path: Path, api_key: str):
    """
    Convert and post a single JSON file to Hevy API.

    Args:
        json_path: Path to JSON file to convert and post
        api_key: Hevy API key

    Returns:
        Tuple of (successful_count, failed_count)
    """
    print(f"Processing: {json_path}")
    print(f"{'=' * 80}\n")

    try:
        api_payloads = convert_file(json_path)
        print(f"Found {len(api_payloads)} workout(s) to post\n")

        successful = 0
        failed = 0

        for i, payload in enumerate(api_payloads, 1):
            title = payload['routine']['title']
            try:
                print(f"[{i}/{len(api_payloads)}] Posting: {title}...", end=" ")
                response = post_to_hevy_api(payload, api_key)
                routine_id = response.get('id', 'N/A')
                print(f"✓ Success (ID: {routine_id})")
                successful += 1
            except requests.HTTPError as e:
                print(f"✗ Failed")
                print(f"    Error: {e.response.status_code} - {e.response.text}")
                failed += 1
            except Exception as e:
                print(f"✗ Failed")
                print(f"    Error: {e}")
                failed += 1

        print(f"\n{'=' * 80}")
        print(f"Summary:")
        print(f"  Total workouts: {len(api_payloads)}")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")

        return successful, failed

    except Exception as e:
        print(f"✗ Error reading file: {e}")
        return 0, 1


def batch_convert_all(output_dir: Path = Path("output"),
                      api_key: str = None,
                      dry_run: bool = True):
    """
    Convert and optionally post all workout files to Hevy API.

    Args:
        output_dir: Root output directory
        api_key: Hevy API key (required if not dry_run)
        dry_run: If True, only preview conversion without posting
    """
    json_files = find_all_workout_files(output_dir)

    print(f"Found {len(json_files)} JSON files to process\n")

    total_workouts = 0
    successful = 0
    failed = 0

    for json_file in json_files:
        try:
            api_payloads = convert_file(json_file)
            total_workouts += len(api_payloads)

            print(f"\n{json_file}")
            print(f"  Workouts: {len(api_payloads)}")

            if not dry_run:
                if not api_key:
                    raise ValueError("API key required for posting to Hevy")

                for payload in api_payloads:
                    try:
                        response = post_to_hevy_api(payload, api_key)
                        print(f"  ✓ Posted: {payload['routine']['title']}")
                        print(f"    Routine ID: {response.get('id', 'N/A')}")
                        successful += 1
                        if successful % 10 == 0:
                            print(f"We've processed {successful} workouts. Time for a nap.")
                            sleep(10)
                    except requests.HTTPError as e:
                        print(f"  ✗ Failed: {payload['routine']['title']}")
                        print(f"    Error: {e}")
                        failed += 1
            else:
                print(f"  (Dry run - not posting)")
                successful += len(api_payloads)

        except Exception as e:
            print(f"  ✗ Error processing file: {e}")
            failed += 1

    print(f"\n{'=' * 80}")
    print(f"Summary:")
    print(f"  Total files: {len(json_files)}")
    print(f"  Total workouts: {total_workouts}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")


if __name__ == "__main__":
    import sys

    # Default: Preview conversion of first file found
    if len(sys.argv) == 1:
        output_dir = Path("output")
        json_files = find_all_workout_files(output_dir)

        if json_files:
            print("Preview mode: Converting first file found\n")
            preview_conversion(json_files[0])
        else:
            print("No JSON files found in output directory")

    # Batch convert all files
    elif sys.argv[1] == "--batch":
        # Extract API key if provided
        api_key = None
        for arg in sys.argv:
            if arg.startswith("--api-key="):
                api_key = arg.split("=", 1)[1]

        # If api_key is present, post; otherwise just preview
        dry_run = api_key is None
        batch_convert_all(dry_run=dry_run, api_key=api_key)

    # Handle file path with optional --api-key
    elif len(sys.argv) >= 2 and not sys.argv[1].startswith("--"):
        json_path = Path(sys.argv[1])

        # Extract API key if provided
        api_key = None
        for arg in sys.argv:
            if arg.startswith("--api-key="):
                api_key = arg.split("=", 1)[1]

        if api_key:
            # Post single file to API
            post_single_file(json_path, api_key)
        else:
            # Just preview the conversion
            preview_conversion(json_path)

    else:
        print("Usage:")
        print("  python convert_to_hevy_api.py                        # Preview first file")
        print("  python convert_to_hevy_api.py <file.json>            # Preview specific file")
        print("  python convert_to_hevy_api.py <file.json> --api-key=KEY  # Post single file")
        print("  python convert_to_hevy_api.py --batch                # Preview all files")
        print("  python convert_to_hevy_api.py --batch --api-key=KEY  # Post all to API")
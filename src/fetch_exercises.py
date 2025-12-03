import json
import requests
from typing import List, Dict, Any


API_BASE_URL = "https://api.hevyapp.com"
API_KEY = "2bbe200e-4435-4964-8ed7-cbb52a9d4491"
HEADERS = {
    "accept": "application/json",
    "api-key": API_KEY
}


def fetch_all_exercises() -> List[Dict[str, Any]]:
    """
    Fetch all exercise templates from the Hevy API.
    The API returns max 100 records per page, so we need to paginate.
    """
    all_exercises = []
    page = 1
    page_size = 100

    while True:
        url = f"{API_BASE_URL}/v1/exercise_templates"
        params = {
            "page": page,
            "pageSize": page_size
        }

        print(f"Fetching page {page}...")
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()

        data = response.json()

        # The API returns exercise templates in the response
        # We need to check the structure of the response
        if isinstance(data, dict):
            exercises = data.get("exercise_templates", [])
            if not exercises:
                # Try other possible keys
                exercises = data.get("exercises", [])
            if not exercises:
                # If it's still empty and we're on page 1, the data might be directly a list
                if page == 1 and isinstance(data, list):
                    exercises = data
                else:
                    break
        elif isinstance(data, list):
            exercises = data
        else:
            break

        if not exercises:
            break

        all_exercises.extend(exercises)
        print(f"  Retrieved {len(exercises)} exercises")

        # If we got fewer than page_size, we've reached the end
        if len(exercises) < page_size:
            break

        page += 1

    return all_exercises


def save_exercises_to_file(exercises: List[Dict[str, Any]], filename: str = "exercises.json"):
    """Save exercises to a JSON file."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(exercises, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(exercises)} exercises to {filename}")


def main():
    """Main function to fetch and save all exercises."""
    try:
        print("Fetching exercises from Hevy API...")
        exercises = fetch_all_exercises()

        if exercises:
            save_exercises_to_file(exercises)
            print(f"\nTotal exercises retrieved: {len(exercises)}")
        else:
            print("No exercises found or error occurred.")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching exercises: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()

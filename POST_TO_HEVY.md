# Converting Output JSON to Hevy API Format

## Overview

This document explains how to convert the JSON workout files in the `output/` directory to the format required by the Hevy.com REST API for posting routines.

## Current Directory Structure

```
output/
├── PaulSklarXfit365-Monthly-Program-v5/
│   ├── Week_1/Week_1.json
│   ├── Week_2/Week_2.json
│   ├── Week_3/Week_3.json
│   └── Week_4/Week_4.json
├── PaulSklarXfit365-Monthly-Programming-v71/
│   ├── Week_1/Week_1.json
│   ├── Week_2/Week_2.json
│   ├── Week_3/Week_3.json
│   └── Week_4/Week_4.json
├── PaulSklarXfit365-V10/
│   ├── Week_1/Week_1.json
│   ├── Week_2/Week_2.json
│   ├── Week_3/Week_3.json
│   └── Week_4/Week_4.json
├── PaulSklarXfit365-v12_2020-06/
│   ├── Week_1/Week_1.json
│   ├── Week_2/Week_2.json
│   ├── Week_3/Week_3.json
│   └── Week_4/Week_4.json
└── PaulSklarXfit365-v14/
    ├── Week_1/Week_1.json
    ├── Week_2/Week_2.json
    ├── Week_3/Week_3.json
    └── Week_4/Week_4.json
```

**Total**: 5 programs × 4 weeks = 20 JSON files to convert

---

## Format Comparison

### Current Format (Output Directory)

```json
[
  {
    "id": "workout_1",
    "title": "WORKOUT #1",
    "folder_id": 1913850,
    "updated_at": "2024-01-01 00:00:00+00:00",
    "created_at": "2024-01-01 00:00:00+00:00",
    "exercises": [
      {
        "superset_id": "A",
        "section_type": "GIANT SET",
        "rounds": 6,
        "rest_between_rounds": 150,
        "target": "LEGS",
        "exercises": [
          {
            "exercise_template_id": "C284D923",
            "superset_id": "A",
            "rest_seconds": 0,
            "notes": "Round 1: 16 reps Medium...",
            "sets": [
              {
                "index": 0,
                "type": "normal",
                "weight_kg": 15.0,
                "reps": 16,
                "rep_range": null,
                "distance_meters": null,
                "duration_seconds": null,
                "rpe": null,
                "custom_metric": null
              }
            ]
          }
        ]
      }
    ]
  }
]
```

### Hevy API Format (Required)

```json
{
  "routine": {
    "title": "WORKOUT #1",
    "folder_id": "1913850",
    "notes": null,
    "exercises": [
      {
        "exercise_template_id": "C284D923",
        "superset_id": "A",
        "rest_seconds": 0,
        "notes": "Round 1: 16 reps Medium...",
        "sets": [
          {
            "type": "normal",
            "weight_kg": 15.0,
            "reps": 16,
            "rep_range": null,
            "distance_meters": null,
            "duration_seconds": null,
            "custom_metric": null
          }
        ]
      }
    ]
  }
}
```

---

## Conversion Steps

### Step 1: Unwrap the Top-Level Array

**Current**: Each JSON file contains an array of workouts
**Action**: Process each workout in the array individually

### Step 2: Remove Generated Fields

Remove these fields from the routine level:
- `id` (API will generate this)
- `updated_at` (API will generate this)
- `created_at` (API will generate this)

Keep:
- `title`
- `folder_id`

Add:
- `notes`: Set to `null` or optionally include a description

### Step 3: Flatten SuperSet Structure

**Current Structure**: Exercises are wrapped in SuperSet objects with metadata
```json
{
  "superset_id": "A",
  "section_type": "GIANT SET",
  "rounds": 6,
  "rest_between_rounds": 150,
  "target": "LEGS",
  "exercises": [/* nested exercises */]
}
```

**Target Structure**: Flat array of exercises with `superset_id` preserved
```json
{
  "exercise_template_id": "...",
  "superset_id": "A",
  "rest_seconds": 0,
  "notes": "...",
  "sets": [...]
}
```

**Action**:
1. Extract all exercises from each SuperSet's `exercises` array
2. Preserve the `superset_id` on each exercise (already present)
3. Discard SuperSet wrapper fields: `section_type`, `rounds`, `rest_between_rounds`, `target`

**Note**: SuperSet metadata is lost in the API format. Consider preserving it in the routine's `notes` field or individual exercise `notes` if needed.

### Step 4: Clean Exercise Sets

Remove the `index` field from each set:

**Before**:
```json
{
  "index": 0,
  "type": "normal",
  "weight_kg": 15.0,
  "reps": 16
}
```

**After**:
```json
{
  "type": "normal",
  "weight_kg": 15.0,
  "reps": 16
}
```

Keep all other fields:
- `type`
- `weight_kg`
- `reps`
- `rep_range`
- `distance_meters`
- `duration_seconds`
- `rpe` (Note: API schema shows `custom_metric` instead)
- `custom_metric`

### Step 5: Wrap in API Structure

Wrap the transformed routine in the required API wrapper:

```json
{
  "routine": {
    /* transformed routine here */
  }
}
```

---

## Transformation Algorithm

### Pseudocode

```python
def convert_workout_to_api_format(workout):
    # Step 1: Extract routine metadata
    api_routine = {
        "title": workout["title"],
        "folder_id": str(workout["folder_id"]),  # Convert to string if needed
        "notes": None
    }

    # Step 2: Flatten SuperSets into exercises
    flat_exercises = []
    for superset in workout["exercises"]:
        for exercise in superset["exercises"]:
            # Step 3: Clean sets (remove index)
            clean_sets = []
            for set_data in exercise["sets"]:
                clean_set = {k: v for k, v in set_data.items() if k != "index"}
                clean_sets.append(clean_set)

            # Add flattened exercise
            flat_exercises.append({
                "exercise_template_id": exercise["exercise_template_id"],
                "superset_id": exercise["superset_id"],
                "rest_seconds": exercise["rest_seconds"],
                "notes": exercise["notes"],
                "sets": clean_sets
            })

    api_routine["exercises"] = flat_exercises

    # Step 4: Wrap in API structure
    return {"routine": api_routine}

def process_all_files():
    for json_file in find_all_workout_jsons():
        workouts = read_json(json_file)
        for workout in workouts:
            api_payload = convert_workout_to_api_format(workout)
            post_to_hevy_api(api_payload)
```

---

## Example Transformation

### Input (from output/PaulSklarXfit365-Monthly-Program-v5/Week_1/Week_1.json)

```json
[
  {
    "id": "workout_1",
    "title": "WORKOUT #1",
    "folder_id": 1913850,
    "updated_at": "2024-01-01 00:00:00+00:00",
    "created_at": "2024-01-01 00:00:00+00:00",
    "exercises": [
      {
        "superset_id": "A",
        "section_type": "GIANT SET",
        "rounds": 6,
        "rest_between_rounds": 150,
        "target": "LEGS",
        "exercises": [
          {
            "exercise_template_id": "C284D923",
            "superset_id": "A",
            "rest_seconds": 0,
            "notes": "Round 1: 16 reps Medium",
            "sets": [
              {
                "index": 0,
                "type": "normal",
                "weight_kg": 15.0,
                "reps": 16,
                "rep_range": null,
                "distance_meters": null,
                "duration_seconds": null,
                "rpe": null,
                "custom_metric": null
              }
            ]
          },
          {
            "exercise_template_id": "B923B230",
            "superset_id": "A",
            "rest_seconds": 150,
            "notes": "Round 1: 10 reps",
            "sets": [
              {
                "index": 0,
                "type": "normal",
                "weight_kg": 20.0,
                "reps": 10,
                "rep_range": null,
                "distance_meters": null,
                "duration_seconds": null,
                "rpe": null,
                "custom_metric": null
              }
            ]
          }
        ]
      }
    ]
  }
]
```

### Output (Ready for Hevy API POST)

```json
{
  "routine": {
    "title": "WORKOUT #1",
    "folder_id": "1913850",
    "notes": null,
    "exercises": [
      {
        "exercise_template_id": "C284D923",
        "superset_id": "A",
        "rest_seconds": 0,
        "notes": "Round 1: 16 reps Medium",
        "sets": [
          {
            "type": "normal",
            "weight_kg": 15.0,
            "reps": 16,
            "rep_range": null,
            "distance_meters": null,
            "duration_seconds": null,
            "rpe": null,
            "custom_metric": null
          }
        ]
      },
      {
        "exercise_template_id": "B923B230",
        "superset_id": "A",
        "rest_seconds": 150,
        "notes": "Round 1: 10 reps",
        "sets": [
          {
            "type": "normal",
            "weight_kg": 20.0,
            "reps": 10,
            "rep_range": null,
            "distance_meters": null,
            "duration_seconds": null,
            "rpe": null,
            "custom_metric": null
          }
        ]
      }
    ]
  }
}
```

---

## Implementation Checklist

- [ ] Create a Python script to read all JSON files from `output/` directory
- [ ] For each JSON file:
  - [ ] Read the array of workouts
  - [ ] For each workout in the array:
    - [ ] Apply transformation steps 1-5
    - [ ] Generate API payload
    - [ ] POST to `https://api.hevyapp.com/v1/routines`
- [ ] Handle API authentication (api-key header)
- [ ] Handle rate limiting and errors
- [ ] Log successful uploads
- [ ] Optionally: Store API response (routine IDs) for reference

---

## Key Differences Summary

| Field | Current Format | API Format | Action |
|-------|---------------|------------|--------|
| Top-level structure | Array of workouts | Single routine object wrapped in `{"routine": {...}}` | Unwrap array, wrap each routine |
| `id` | Present | Not sent (API generates) | Remove |
| `updated_at` | Present | Not sent (API generates) | Remove |
| `created_at` | Present | Not sent (API generates) | Remove |
| `folder_id` | Integer | String | Convert to string |
| `notes` | Not present | Optional | Add as `null` |
| Exercises structure | Nested in SuperSets | Flat array | Flatten |
| SuperSet metadata | `section_type`, `rounds`, `rest_between_rounds`, `target` | Not supported | Remove/preserve in notes |
| Set `index` | Present | Not in API schema | Remove |
| `rpe` | Present | Use `custom_metric` instead? | Verify API behavior |

---

## API Endpoint

**POST** `https://api.hevyapp.com/v1/routines`

**Headers**:
```
api-key: 2bbe200e-4435-4964-8ed7-cbb52a9d4491
Content-Type: application/json
Accept: application/json
```

**Reference**: See `HEVY_INTEGRATION.md` for full API documentation and schema.

---

## Next Steps

1. Implement the converter script following the algorithm above
2. Test with a single workout from one file first
3. Verify the API response and created routine in Hevy
4. Batch process all remaining files
5. Monitor for errors and adjust as needed

**Note**: Each week folder already has the correct `folder_id` embedded in the JSON. Make sure these folder IDs actually exist in your Hevy account before posting, or update them to match your actual Hevy folder structure.
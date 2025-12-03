# Hevy API Integration Guide

## Background

**Hevy** is a web-based platform for:
- Tracking workouts
- Designing repeatable workout routines
- Interacting with other users

## Project Goal

Integrate with the Hevy API to transcribe workout routines from PDF files into data on the Hevy platform.

---

## API Integration Details

### Base URL
```
https://api.hevyapp.com/docs/
```

### Authentication
- **Header**: `api-key`
- **Key**: `2bbe200e-4435-4964-8ed7-cbb52a9d4491`

### API Documentation
Full REST API schema available at: https://api.hevyapp.com/docs/

---

## Workflow

### Step 1: Download Exercise Templates

The API limits responses to **100 records per page**, requiring multiple paginated calls.

**Example using `curl`:**
```bash
curl -X 'GET' \
  'https://api.hevyapp.com/v1/exercise_templates?page=1&pageSize=100' \
  -H 'accept: application/json' \
  -H 'api-key: 2bbe200e-4435-4964-8ed7-cbb52a9d4491'
```

**Key Points:**
- Paginate through all available exercises
- Use `page` parameter starting from 1
- Set `pageSize=100` for maximum efficiency

---

### Step 2: Parse PDF Files

**Input:** Local PDF files containing workout programs

**Structure:**
- Each PDF contains **4 weeks** of scheduled workouts
- Each week contains **5 workouts**
- Convert each workout into a Hevy Routine

#### Converting PDF Data to JSON

When converting unstructured PDF data into JSON format for the REST API, follow these guidelines:

##### 1. Exercise Matching
- Match each exercise found in the PDF to the exercise templates downloaded from the REST API (Step 1)
- Use fuzzy matching or string similarity algorithms to find the best match
- Consider variations in naming (e.g., "Pull Up" vs "Pull-Up" vs "Pullup")
- If no good match is found, log a warning and skip the exercise or use the closest match

##### 2. Weight Conversion
PDF files use descriptive weight labels that must be converted to kilogram values:

| PDF Description | Weight (kg) |
|----------------|-------------|
| Medium | 15 |
| Medium Plus | 20 |
| Heavy | 40 |

**Notes:**
- These are starting values and can be adjusted based on your specific needs
- Additional weight descriptions may need to be mapped as encountered
- Consider adding support for custom weight mappings per user

##### 3. Reps and Rep Ranges
- Use the `reps` field for single rep counts (e.g., "10 reps" → `reps: 10`)
- Use the `rep_range` field for rep ranges (e.g., "8-12 reps" → `rep_range: "8-12"`)
- If the rep count/range cannot be determined from the PDF, omit these fields entirely
- Do not guess or provide default values for reps

##### 4. Rest Periods in Supersets
Handle rest periods carefully for supersets and giant sets:

- **Within a superset:** Set `rest_seconds: 0` for all exercises except the last one
- **After the superset:** The last exercise in the superset should have:
  - `rest_seconds` value extracted from the PDF if available
  - Default to `rest_seconds: 90` if not specified in the PDF

**Example:**
```json
{
  "exercises": [
    {
      "exercise_template_id": "123",
      "superset_id": "A",
      "rest_seconds": 0
    },
    {
      "exercise_template_id": "456",
      "superset_id": "A",
      "rest_seconds": 0
    },
    {
      "exercise_template_id": "789",
      "superset_id": "A",
      "rest_seconds": 90
    }
  ]
}
```

---

### Step 3: Create Folders for Organization

For each PDF file, create **4 folders** via the API, one per week.

**Naming Convention:**
```
{PDF_FILENAME}-Week{X}
```
Where `X` = [1, 2, 3, 4]

**Example:**
For file `PaulSklarFitnessMonthlyProgram5.pdf`, create:
- `PaulSklarFitnessMonthlyProgram5-Week1`
- `PaulSklarFitnessMonthlyProgram5-Week2`
- `PaulSklarFitnessMonthlyProgram5-Week3`
- `PaulSklarFitnessMonthlyProgram5-Week4`

---

### Step 4: Create Workout Routines

For each workout in each week:
1. Convert the workout into a Hevy Workout Routine
2. Save it via REST API into the corresponding folder

**Important Concepts:**

#### SuperSets and Giant Sets
- PDF files use terms **"SuperSet"** and **"Giant Set"**
- These map directly to the API's `superset_id` field
- All exercises in the same SuperSet/Giant Set must share the same `superset_id`

**Schema Reference:**
- Use the API documentation at https://api.hevyapp.com/docs/ for detailed schema
- Request clarification if additional details are needed

#### POST Request Example

**Endpoint:** `POST /v1/routines`

**Example Request:**
```bash
curl -X 'POST' \
  'https://api.hevyapp.com/v1/routines' \
  -H 'accept: application/json' \
  -H 'api-key: 2bbe200e-4435-4964-8ed7-cbb52a9d4491' \
  -H 'Content-Type: application/json' \
  -d '{
  "routine": {
    "title": "April Leg Day 🔥",
    "folder_id": null,
    "notes": "Focus on form over weight. Remember to stretch.",
    "exercises": [
      {
        "exercise_template_id": "D04AC939",
        "superset_id": null,
        "rest_seconds": 90,
        "notes": "Stay slow and controlled.",
        "sets": [
          {
            "type": "normal",
            "weight_kg": 100,
            "reps": 10,
            "distance_meters": null,
            "duration_seconds": null,
            "custom_metric": null,
            "rep_range": {
              "start": 8,
              "end": 12
            }
          }
        ]
      }
    ]
  }
}'
```

#### JSON Schema

For validation and code generation purposes, here's the JSON schema for creating a routine:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Create Routine Request",
  "type": "object",
  "required": ["routine"],
  "properties": {
    "routine": {
      "type": "object",
      "required": ["title", "exercises"],
      "properties": {
        "title": {
          "type": "string",
          "description": "The name of the routine"
        },
        "folder_id": {
          "type": ["string", "null"],
          "description": "Optional folder ID to organize the routine"
        },
        "notes": {
          "type": "string",
          "description": "Optional notes for the routine"
        },
        "exercises": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "object",
            "required": ["exercise_template_id", "sets"],
            "properties": {
              "exercise_template_id": {
                "type": "string",
                "description": "ID from the exercise templates API"
              },
              "superset_id": {
                "type": ["string", "null"],
                "description": "Identifier to group exercises in a superset/giant set"
              },
              "rest_seconds": {
                "type": "integer",
                "minimum": 0,
                "description": "Rest time in seconds after this exercise"
              },
              "notes": {
                "type": "string",
                "description": "Optional notes for this exercise"
              },
              "sets": {
                "type": "array",
                "minItems": 1,
                "items": {
                  "type": "object",
                  "required": ["type"],
                  "properties": {
                    "type": {
                      "type": "string",
                      "enum": ["normal", "warmup", "failure", "dropset"],
                      "description": "Type of set"
                    },
                    "weight_kg": {
                      "type": ["number", "null"],
                      "minimum": 0,
                      "description": "Weight in kilograms"
                    },
                    "reps": {
                      "type": ["integer", "null"],
                      "minimum": 0,
                      "description": "Number of repetitions"
                    },
                    "distance_meters": {
                      "type": ["number", "null"],
                      "minimum": 0,
                      "description": "Distance in meters (for cardio)"
                    },
                    "duration_seconds": {
                      "type": ["integer", "null"],
                      "minimum": 0,
                      "description": "Duration in seconds (for timed exercises)"
                    },
                    "custom_metric": {
                      "type": ["string", "null"],
                      "description": "Custom metric value"
                    },
                    "rep_range": {
                      "type": ["object", "null"],
                      "properties": {
                        "start": {
                          "type": "integer",
                          "minimum": 1,
                          "description": "Minimum reps in range"
                        },
                        "end": {
                          "type": "integer",
                          "minimum": 1,
                          "description": "Maximum reps in range"
                        }
                      },
                      "required": ["start", "end"],
                      "description": "Target rep range for the set"
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

**Key Schema Notes:**
- `routine.title` and `routine.exercises` are required
- Each exercise must have at least one set
- Set types: `normal`, `warmup`, `failure`, `dropset`
- Use `rep_range` for target ranges (e.g., 8-12 reps)
- Use `reps` for specific rep counts
- Weight should be in kilograms (`weight_kg`)

---

## Summary

1. ✅ Fetch all exercise templates (paginated, 100 per page)
2. ✅ Parse PDF files into weekly workout structures
3. ✅ Create 4 folders per PDF (one per week)
4. ✅ Create 5 routines per week (saved to appropriate folder)
5. ✅ Map SuperSets/Giant Sets to `superset_id` in API

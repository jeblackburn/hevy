# PDF Workout Parser - Usage Guide

## Overview

This parser extracts workout data from PaulSklarXfit PDF files and converts them to JSON format compatible with the Hevy API.

## Installation

```bash
# Sync dependencies using uv
uv sync
```

This will install all required dependencies including:
- `pymupdf` - Fast PDF parsing
- `fuzzywuzzy` - Fuzzy string matching for exercise names
- `python-levenshtein` - Faster fuzzy matching backend

## Usage

### Basic Usage

```python
from hevy.parse_pdf_to_json import parse_pdf_to_json

# Parse the PDF
parse_pdf_to_json(
    pdf_path="Workouts/PaulSklarXfit365-v14.pdf",
    exercises_json_path="exercises.json",
    output_dir="output"
)
```

### Running from Command Line

```bash
# Using uv to run the script
uv run python src/hevy/parse_pdf_to_json.py

# Or activate the virtual environment first
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
python src/hevy/parse_pdf_to_json.py
```

## Output Structure

The parser generates the following structure:

```
output/
├── week1/
│   ├── workout01.json
│   ├── workout02.json
│   ├── workout03.json
│   ├── workout04.json
│   └── workout05.json
├── week2/
│   ├── workout06.json
│   └── ...
├── week3/
│   └── ...
├── week4/
│   └── ...
└── metadata.json
```

## Output Format

Each workout JSON file follows the Hevy API format:

```json
{
  "routine": {
    "title": "PaulSklarXfit365-v14 - Week 1 - Workout 1",
    "folder_id": null,
    "notes": "Section A: GIANT SET - 6 rounds (Target: LEGS)",
    "exercises": [
      {
        "exercise_template_id": "ABC123",
        "superset_id": "1A",
        "rest_seconds": 0,
        "notes": "Medium weight",
        "sets": [
          {
            "type": "normal",
            "weight_kg": 15,
            "reps": 10,
            "distance_meters": null,
            "duration_seconds": null,
            "custom_metric": null,
            "rep_range": null
          }
        ]
      }
    ]
  }
}
```

## Key Features

### 1. Automatic Workout Detection
- Identifies all 20 workouts in the PDF
- Organizes by week (4 weeks, 5 workouts per week)

### 2. Section Parsing
- Detects Giant Sets, Supersets, Finishers, and Sequences
- Extracts rounds and rest periods
- Identifies target muscle groups

### 3. Exercise Matching
- Fuzzy matches PDF exercise names to Hevy exercise templates
- Handles variations in naming (e.g., "Pull Up" vs "Pull-Up")
- Warns on low-confidence matches (<70%)

### 4. Weight Conversion
- Converts descriptive weights to kg values:
  - Medium → 15 kg
  - Medium Plus → 20 kg
  - Heavy → 40 kg
  - Bodyweight → 0 kg

### 5. Rep Parsing
- Handles single values: "10" → 10 reps
- Handles ranges: "8-12" → uses midpoint
- Handles round-specific reps: "Round 1: 16, Round 2-4: 10"

### 6. Superset Handling
- Groups exercises with `superset_id`
- Sets rest_seconds = 0 for all but last exercise in superset
- Last exercise gets appropriate rest period

## Customization

### Modifying Weight Mappings

Edit the `WEIGHT_MAPPING` dictionary in `parse_pdf_to_json.py`:

```python
WEIGHT_MAPPING = {
    "medium": 15,
    "medium plus": 20,
    "heavy": 40,
    # Add your custom mappings here
}
```

### Adjusting Fuzzy Match Threshold

In the `_match_exercise_name` method, adjust the confidence threshold:

```python
if confidence < 70:  # Change this value (0-100)
    print(f"Warning: Low confidence match...")
```

## Troubleshooting

### Issue: Low Confidence Exercise Matches

**Symptom**: Console shows warnings like:
```
Warning: Low confidence match for 'Pull Up Variation': 65%
```

**Solution**:
1. Check the output JSON for the matched exercise
2. Manually review if the match is correct
3. Add manual overrides if needed

### Issue: Missing Exercises

**Symptom**: Some exercises not appearing in output

**Solution**:
1. Check if exercise is in `exercises.json`
2. Verify PDF formatting is consistent
3. Check parser console output for errors

### Issue: Incorrect Rep/Weight Parsing

**Symptom**: Reps or weights don't match PDF

**Solution**:
1. Check the specific workout JSON
2. Review the `_parse_reps_from_block` or `_parse_weight_from_block` methods
3. Add additional regex patterns if needed

## Validation

After parsing, validate the output:

1. **Check metadata.json**: Verify 20 workouts were found
2. **Spot check workouts**: Review a few JSON files for accuracy
3. **Exercise matching**: Look for low-confidence warnings
4. **Weight values**: Ensure conversions are correct
5. **Superset grouping**: Verify superset_id and rest_seconds

## Next Steps

After parsing:

1. Review generated JSON files for accuracy
2. Make any necessary manual corrections
3. Use the Hevy API upload script (separate) to send routines to Hevy
4. Create folders in Hevy for each week
5. Upload workouts to appropriate folders

## Limitations

- Requires consistent PDF formatting
- Complex exercise instructions may need manual review
- Exercise name matching depends on similarity to Hevy templates
- Some edge cases may require manual JSON editing

## Support

For issues or questions:
- Check PLAN.md for detailed parsing strategy
- Review HEVY_INTEGRATION.md for API details
- Check parser console output for warnings/errors
# PDF Workout Data Extraction Plan

## Overview

This document outlines the detailed plan for extracting workout data from PDF files in the `Workouts/` directory and converting them into a format compatible with the Hevy API.

## Document Structure Analysis

The PDFs contain 4-week workout programs with:
- **20 total workouts** (5 workouts per week × 4 weeks)
- Each workout organized into **sections** (A, B, C, etc.)
- Each section contains **multiple exercises** with specific parameters
- Exercises grouped as: Giant Sets, Supersets, Finisher Sets, or Sequences

### Sample Workout Structure

```
WORKOUT #1
TARGET: LEGS

A. GIANT SET: 6 ROUNDS
   Rest 2-3 Minutes Between Rounds

   1. Barbell Reverse Lunge
      - Round 1: 16 reps - Medium
      - Round 2-4: 10 reps - Medium Plus
      - Round 5-6: 8 reps - Heavy

   2. Kettlebell Deadlift
      - 10 reps - Medium Plus or Heavy

   3. Kettlebell Goblet Squat
      - 6-10 reps - Medium Plus or Heavy
```

## Data Extraction Strategy

### Phase 1: PDF Parsing & Text Extraction

**Tools**:
- `PyMuPDF` (fitz) or `pdfplumber` for text extraction
- `camelot-py` for table extraction (optional)

**Approach**:
1. Extract text page-by-page
2. Identify workout boundaries using headers like "WORKOUT #1", "WORKOUT #2"
3. Parse tabular data (exercises appear in structured tables)
4. Extract hyperlinks to exercise demonstration videos

### Phase 2: Workout Structure Identification

For each workout, extract:

#### A. Workout Metadata
- Week number (1-4)
- Workout day within week (1-5)

#### B. Section Structure (A, B, C, etc.)

```
Section:
├── Section ID: "A", "B", "C"
├── Type: "GIANT SET" / "SUPERSET" / "FINISHER" / "SEQUENCE"
├── Rounds: Number (e.g., 6)
├── Rest Period: "Rest 2-3 Minutes Between Rounds"
├── Target: "TARGET: LEGS"
└── Exercises: [List of exercises with details]
```

#### C. Exercise Details (for each exercise in a section)

```
Exercise:
├── Order: 1, 2, 3, 4...
├── Name: "Barbell Reverse Lunge"
├── Reps: "10" or conditional by round
├── Weight: "Medium", "Heavy", "Bodyweight"
├── Notes: Any special instructions
└── Video Link: URL (if present)
```

## Data Transformation Rules

### Weight Conversion

From HEVY_INTEGRATION.md:

| PDF Description | Weight (kg) |
|----------------|-------------|
| Medium         | 15          |
| Medium Plus    | 20          |
| Heavy          | 40          |

```python
WEIGHT_MAPPING = {
    "Medium": 15,
    "Medium Plus": 20,
    "Heavy": 40,
    "Bodyweight": 0,
    "As Heavy as Possible": None,  # User-determined
    # Add more as encountered
}
```

### Rep Parsing

- **Single value**: `"10"` → `reps: 10`
- **Range**: `"8-12"` → `rep_range: {"start": 8, "end": 12}`
- **Variable by round**: Create conditional logic or multiple set definitions
- **Time-based**: `"60 seconds"` → `duration_seconds: 60`

### Superset ID Assignment

- All exercises within a "GIANT SET" / "SUPERSET" / "FINISHER" / "SEQUENCE" share the same `superset_id`
- Naming convention: `"{workout_number}{section_letter}"`
  - Examples: `"1A"`, `"1B"`, `"2A"`, `"15C"`
- Single exercises (not in a superset): `superset_id: null`

### Rest Period Handling

From HEVY_INTEGRATION.md guidelines:

1
- **Within superset/giant set**: `rest_seconds: 0` for all exercises except the last
- **Last exercise in superset**: Extract from "Rest X Minutes Before..." text
- **Between rounds**: Specified in section header
- **Default**: If not specified for last exercise in superset: `rest_seconds: 90`

**Time Conversion**:
- `"2-3 Minutes"` → Use midpoint: `150 seconds`
- `"1-2 Minutes"` → Use midpoint: `90 seconds`
- `"30-60 seconds"` → Use midpoint: `45 seconds`

## Implementation Steps

### Step 1: PDF Text Extraction

```python
import fitz  # PyMuPDF

def extract_pdf_text(pdf_path):
    """Extract text from all pages of a PDF."""
    doc = fitz.open(pdf_path)
    pages_text = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        pages_text.append({
            'page_number': page_num + 1,
            'text': page.get_text(),
            'links': page.get_links()  # For video URLs
        })
    doc.close()
    return pages_text
```

### Step 2: Workout Segmentation

- Use regex to find workout boundaries: `r"WORKOUT #(\d+)"`
- Group consecutive pages belonging to same workout
- Identify section boundaries: `r"^([A-Z])\s+(GIANT SET|SUPERSET|FINISHER|SEQUENCE)"`

### Step 3: Table Parsing

- Identify table structures (headers: "REPS", "WEIGHT")
- Extract rows containing exercise data
- Parse exercise names (column 1), reps (column 2), weights (column 3)
- Handle merged cells and multi-line content

### Step 4: Exercise Name Matching

Load Hevy exercise templates from `exercises.json` and match:

```python
from fuzzywuzzy import fuzz, process

def match_exercise(pdf_exercise_name, exercise_templates):
    """
    Match PDF exercise name to Hevy exercise template.
    Returns: (exercise_template_id, confidence_score)
    """
    # Extract just the titles from templates
    template_titles = {ex['id']: ex['title'] for ex in exercise_templates}

    # Fuzzy match
    match = process.extractOne(
        pdf_exercise_name,
        template_titles.values(),
        scorer=fuzz.token_sort_ratio
    )

    # Find the ID for the matched title
    matched_title, score = match[0], match[1]
    matched_id = [k for k, v in template_titles.items() if v == matched_title][0]

    return matched_id, score
```

**Handling Mismatches**:
- Threshold: Require 85%+ confidence
- Log low-confidence matches for manual review
- Build override dictionary for known problematic names

### Step 5: JSON Structure Generation

Target structure for Hevy API:

```json
{
  "routine": {
    "title": "Week 1 - Workout 1 - Legs & Chest",
    "folder_id": "week1_folder_id",
    "notes": "Focus on form. Progressive overload by week.",
    "exercises": [
      {
        "exercise_template_id": "D04AC939",
        "superset_id": "1A",
        "rest_seconds": 0,
        "notes": "Medium weight",
        "sets": [
          {
            "type": "normal",
            "weight_kg": 15,
            "reps": 16,
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

### Step 6: Set Generation Logic

Handle variable rep/weight schemes:

```python
def generate_sets(exercise_data, rounds):
    """
    Generate set definitions based on rep/weight variations.

    Example input:
    - Round 1: 16 reps, Medium
    - Round 2-4: 10 reps, Medium Plus
    - Round 5-6: 8 reps, Heavy

    Output: 6 sets with appropriate weights
    """
    sets = []

    for round_num in range(1, rounds + 1):
        # Determine reps and weight for this round
        reps = determine_reps_for_round(exercise_data, round_num)
        weight = determine_weight_for_round(exercise_data, round_num)

        sets.append({
            "type": "normal",
            "weight_kg": WEIGHT_MAPPING.get(weight),
            "reps": reps,
            "distance_meters": None,
            "duration_seconds": None,
            "custom_metric": None,
            "rep_range": None
        })

    return sets
```

## Challenge Areas & Solutions

### Challenge 1: Exercise Name Matching

**Problem**: Variations in naming conventions
- "Pull Up" vs "Pull-Up" vs "Pullup" vs "Parallel Grip Pull-Up"

**Solutions**:
1. Use fuzzy matching with high threshold (85%+)
2. Build manual override dictionary for known mismatches
3. Use muscle group as secondary validation
4. Log all matches below 95% for review

### Challenge 2: Variable Rep Schemes

**Problem**: Complex rep patterns
- "Round 1: 16, Round 2-4: 10, Round 5-6: 8"
- "8 Total reps with 2 second pause at bottom, 4 reps with no pause"

**Solutions**:
1. Parse round ranges: "2-4" → rounds 2, 3, 4
2. Create appropriate number of sets
3. Use notes field for complex instructions
4. Consider rep_range for approximations

### Challenge 3: Complex Exercise Descriptions

**Problem**: Flow exercises with multiple movements
- "Battle Rope Chest Fly Pushup Flow: Chest Fly 10 seconds then Pushups 5 reps then repeat"

**Solutions**:
1. Treat as single exercise with detailed notes
2. Use duration_seconds for timed components
3. Document complex patterns in notes field
4. Consider breaking into separate exercises if needed

### Challenge 4: Table Detection Accuracy

**Problem**: PDF tables may not parse cleanly

**Solutions**:
1. Try multiple extraction methods (pdfplumber, camelot, custom regex)
2. Implement fallback to pattern-based extraction
3. Validate extracted data against expected structure
4. Manual review for edge cases

### Challenge 5: Special Instructions

**Problem**: Exercise-specific notes embedded in tables
- "Contract Triceps at bottom of every curl"
- "Stay slow and controlled"

**Solutions**:
1. Extract notes from additional columns or parenthetical text
2. Store in exercise notes field
3. Preserve for user reference

## Python Libraries Needed

```bash
# PDF Processing
pip install PyMuPDF  # Fast and reliable
pip install pdfplumber  # Alternative with good table support
pip install camelot-py[cv]  # Excellent table extraction

# Text Matching
pip install fuzzywuzzy  # Fuzzy string matching
pip install python-Levenshtein  # Faster fuzzy matching

# Data Processing
pip install pandas  # Data organization and manipulation

# Validation
pip install jsonschema  # Validate against Hevy API schema
```

## Output Format

### File Organization

```
output/
├── week1/
│   ├── workout01.json
│   ├── workout02.json
│   ├── workout03.json
│   ├── workout04.json
│   └── workout05.json
├── week2/
│   └── ...
├── week3/
│   └── ...
├── week4/
│   └── ...
└── metadata.json  # Summary of all workouts
```

### Individual Workout JSON

Each file ready to POST to `/v1/routines` endpoint:

```json
{
  "routine": {
    "title": "PaulSklarXfit365-v5 - Week 1 - Workout 1",
    "folder_id": null,
    "notes": "TARGET: LEGS\nAverage workout time: 60 min",
    "exercises": [...]
  }
}
```

## Validation Steps

### 1. Exercise Coverage
- Ensure all exercises have valid template IDs
- Report unmatched exercises
- Verify muscle group alignment

### 2. Weight Validation
- Check all weight values are converted correctly
- Flag unusual weight combinations
- Verify bodyweight exercises have 0kg

### 3. Superset Grouping
- Verify superset_id consistency within sections
- Confirm null for non-superset exercises
- Check rest periods follow rules (0 within, value after)

### 4. Rest Periods
- Confirm rest_seconds = 0 for all but last in superset
- Verify rest times are in seconds (not minutes)
- Check default 90s applied where needed

### 5. Schema Compliance
- Validate against Hevy JSON schema
- Ensure all required fields present
- Check data types match schema

### 6. Completeness
- Verify all 20 workouts extracted
- Check 5 workouts per week
- Confirm all sections (A, B, C, etc.) captured

## Recommended Approach

### Option A: Rules-Based Extraction (Faster, Less Accurate)
**Pros**:
- Fast execution
- No API costs
- Deterministic results

**Cons**:
- Requires extensive regex patterns
- Brittle with format changes
- Manual fixes for edge cases

**Best for**: Consistent PDF formatting, limited budget

### Option B: ML-Based Extraction (Slower, More Accurate)
**Pros**:
- Handles variations well
- Better with complex instructions
- Less manual pattern writing

**Cons**:
- API costs for LLM usage
- Slower processing
- Non-deterministic results

**Best for**: Complex PDFs, high accuracy needed

### Option C: Hybrid Approach (Recommended)
**Pros**:
- Balance of speed and accuracy
- Rules for structure, ML for content
- Cost-effective

**Cons**:
- More complex implementation
- Requires both systems

**Approach**:
1. Use rules-based for structure detection (sections, tables)
2. Use LLM for exercise name normalization and complex parsing
3. Use fuzzy matching for exercise template matching
4. Manual review for low-confidence matches

## Success Criteria

1. **Extraction Completeness**: 100% of workouts extracted
2. **Exercise Matching**: >95% of exercises matched to Hevy templates
3. **Data Accuracy**: Manual review confirms correctness
4. **API Compatibility**: All JSON files valid for Hevy API
5. **Automation**: Process runs with minimal manual intervention

## Next Steps

1. Implement PDF extraction prototype
2. Test on 1-2 sample workouts
3. Build exercise matching system
4. Create JSON generation pipeline
5. Validate output against Hevy API
6. Process all 20 workouts
7. Create upload script for Hevy API
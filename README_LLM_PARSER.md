# LLM-Based PDF Workout Parser

This project uses an LLM (Claude) to parse workout PDFs into structured JSON format for the Hevy API.

## Setup

### 1. Set your Anthropic API Key

You need an Anthropic API key to use the LLM parser. Get one from https://console.anthropic.com/

Set it as an environment variable:

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

Or add it to a `.env` file in the project root:

```
ANTHROPIC_API_KEY=your-api-key-here
```

### 2. Run the test

Once the API key is set, you can run the test:

```bash
# Test with a single workout
uv run python test_llm_parser.py

# Run the full integration test (all 20 workouts)
uv run pytest src/hevy/tests/test_integration.py::TestRealPDFParsing::test_parse_paulsklarxfit365_v14_pdf -v -s
```

## How it works

1. **Extract PDF Text**: Uses PyMuPDF to extract text from all pages
2. **Find Workouts**: Segments pages by workout number (WORKOUT #1, WORKOUT #2, etc.)
3. **Parse with LLM**: Sends each workout's text to Claude with:
   - Exercise template IDs for matching
   - Weight conversion table (Medium=15kg, Heavy=40kg, etc.)
   - Instructions for extracting exercises, sets, reps, and weights
4. **Output JSON**: Saves structured workout routines to JSON file

## Output

The test creates a JSON file at `/Users/jon.blackburn/personal/hevy/paulsklarxfit365_v14_routines.json` containing all parsed workouts.

Each workout follows the Hevy API schema with:
- `routine.title`: Workout name with week and workout number
- `routine.exercises`: Array of exercises with sets, reps, weights
- `routine.notes`: Summary of workout sections
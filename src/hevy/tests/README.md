# Hevy Workout Parser - Test Suite

Comprehensive test suite for the PDFWorkoutParser class using pytest.

## Test Structure

```
tests/
├── __init__.py              # Package initialization
├── conftest.py              # Shared fixtures and test data
├── test_model.py            # Tests for Pydantic models
├── test_workout_parser.py   # Unit tests for parser methods
├── test_integration.py      # Integration tests for full workflow
└── README.md               # This file
```

## Test Coverage

### Unit Tests (`test_workout_parser.py`)

**PDFWorkoutParser Initialization:**
- Parser initialization with exercise templates
- Loading exercises from JSON file

**Rest Period Parsing:**
- Minute ranges (e.g., "2-3 Minutes")
- Single minute values
- Seconds
- Default values

**Target Muscle Group Parsing:**
- Single target muscles
- Multiple targets (comma-separated)
- Missing target information

**Exercise Name Matching:**
- Exact matches
- Case-insensitive matching
- Fuzzy matching for similar names
- Behavior with unmatched exercises

**Weight Conversion:**
- Exact weight descriptions (medium, heavy, etc.)
- Case-insensitive conversion
- Fuzzy matching
- Unknown weights
- "As heavy as possible" variants

**Reps Parsing:**
- Single rep values for all rounds
- Rep ranges (e.g., "8-10")
- Different reps per round
- Round ranges (e.g., "Round 2-6: 6")

**Weight Parsing:**
- Uniform weights across rounds
- Different weights per round
- Bodyweight exercises

**Note Extraction:**
- Parenthetical notes
- Instruction keywords (pause, hold, squeeze, etc.)
- Empty notes

**Set Generation:**
- Creating exercise sets
- Varying reps and weights
- Handling None values

**Workout Segmentation:**
- Finding workout headers
- Multi-page workouts

**Routine Building:**
- Final routine structure
- Workout notes generation

### Model Tests (`test_model.py`)

**ExerciseSet Model:**
- Creating valid sets
- Default values
- Distance-based exercises
- Serialization with `model_dump()`
- Optional field handling

**Exercise Model:**
- Creating valid exercises
- Default values
- Exercises with sets
- Validation of required fields

**WorkoutSection Model:**
- Creating valid sections
- Sections with exercises
- Validation of required fields

**Model Integration:**
- Nested serialization
- JSON compatibility

### Integration Tests (`test_integration.py`)

**PDF Extraction:**
- Extracting text from mocked PDF files
- Multi-page extraction

**Section Parsing:**
- Single section parsing
- Multiple sections in one workout

**Exercise Parsing:**
- Complete exercise blocks
- Multiple exercises in a section
- Superset rest period assignment

**Complete Workflow:**
- End-to-end parsing from PDF to JSON
- Multiple workouts in one PDF
- Week and day calculations

## Running Tests

### Install Test Dependencies

```bash
# Install dev dependencies including pytest
uv sync --extra dev
```

### Run All Tests

```bash
# Run all tests with verbose output
uv run pytest

# Run with coverage report
uv run pytest --cov=src/hevy --cov-report=html
```

### Run Specific Test Files

```bash
# Run only model tests
uv run pytest tests/test_model.py

# Run only unit tests
uv run pytest tests/test_workout_parser.py

# Run only integration tests
uv run pytest tests/test_integration.py
```

### Run Specific Test Classes or Functions

```bash
# Run a specific test class
uv run pytest tests/test_workout_parser.py::TestRestPeriodParsing

# Run a specific test function
uv run pytest tests/test_workout_parser.py::TestRestPeriodParsing::test_parse_rest_minutes_range
```

### Run Tests with Markers

```bash
# Run only unit tests (if marked)
uv run pytest -m unit

# Run only integration tests (if marked)
uv run pytest -m integration

# Exclude slow tests
uv run pytest -m "not slow"
```

### Test Output Options

```bash
# Show print statements
uv run pytest -s

# Show test duration
uv run pytest --durations=10

# Stop on first failure
uv run pytest -x

# Run in parallel (requires pytest-xdist)
uv run pytest -n auto
```

## Test Fixtures

Located in `conftest.py`, these fixtures provide reusable test data:

- **`sample_exercises`**: List of Hevy exercise templates
- **`exercises_json_file`**: Temporary JSON file with exercises
- **`sample_workout_text`**: Sample workout text from PDF
- **`sample_section_text`**: Sample section text
- **`sample_exercise_block`**: Sample exercise block dictionary
- **`sample_pages_data`**: Sample extracted PDF pages

## Mocking

Integration tests use `unittest.mock` to mock PyMuPDF (fitz) for PDF extraction:

```python
@patch('hevy.workout_parser.fitz')
def test_extract_pdf_text(self, mock_fitz, ...):
    # Mock PDF document and pages
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_text.return_value = "Page text"
    ...
```

## Writing New Tests

### Test Naming Convention

- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Example Test

```python
def test_parse_rest_period(self, tmp_path, exercises_json_file):
    """Test parsing rest period with minute range"""
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"dummy")
    parser = PDFWorkoutParser(str(pdf_file), str(exercises_json_file))

    text = "Rest 2-3 Minutes Between Rounds"
    result = parser._parse_rest_period(text)

    assert result == 150
```

### Using Fixtures

```python
def test_example(sample_exercises, exercises_json_file):
    """Fixtures are automatically injected by pytest"""
    assert len(sample_exercises) > 0
    assert exercises_json_file.exists()
```

## Coverage Goals

- **Unit test coverage**: Aim for >90% of parser methods
- **Integration tests**: Cover main workflows end-to-end
- **Edge cases**: Test error handling and boundary conditions

## Continuous Integration

To add tests to CI/CD:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install uv
          uv sync --extra dev
      - name: Run tests
        run: uv run pytest
```

## Troubleshooting

### Import Errors

If you see import errors, ensure:
1. You're in the project root directory
2. Dependencies are installed: `uv sync --extra dev`
3. Running tests via `uv run pytest` (not `python -m pytest`)

### Fixture Not Found

If fixtures aren't found:
1. Check `conftest.py` is in the `tests/` directory
2. Ensure test files are named `test_*.py`
3. Verify pytest discovery is working: `uv run pytest --collect-only`

### Mock Issues

If mocks aren't working:
1. Verify the import path matches the actual usage
2. Use `patch` at the point of use, not definition
3. Check mock method calls with `mock.assert_called_once()`
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

---

## Summary

1. ✅ Fetch all exercise templates (paginated, 100 per page)
2. ✅ Parse PDF files into weekly workout structures
3. ✅ Create 4 folders per PDF (one per week)
4. ✅ Create 5 routines per week (saved to appropriate folder)
5. ✅ Map SuperSets/Giant Sets to `superset_id` in API

# Load Testing Suite (Locust)

This directory contains a reusable Locust setup that simulates concurrent learners navigating the app via API calls.

Default target host:

- `http://141.76.47.6:5173`
- API prefix: `/api`
- Login user: `alice`

## What is modeled

The test runtime chooses between 10 weighted paths, each path containing concrete payloads:

1. `health_check`
   - `GET /api/health`

2. `library_browse`
   - `GET /api/questions`
   - `GET /api/question/{id}?difficulty=...&mode=...&seed=...`

3. `question_open_randomized`
   - `GET /api/question/{id}?difficulty=...&mode=...&seed=...`

4. `relalg_preview_then_submit`
   - `GET /api/question/relational_algebra?...`
   - `POST /api/question/relational_algebra/preview` payload example:
     - `{"statement":"\\proj{Studierende.MatrNr}(Studierende)"}`
   - `POST /api/question/relational_algebra/evaluate` payload example:
     - `{"0":"\\proj{Studierende.MatrNr}(Studierende)"}`

5. `sql_preview_then_submit`
   - `GET /api/question/sql_query?...`
   - `POST /api/question/sql_query/preview` payload example:
     - `{"statement":"SELECT 1 AS x"}`
   - `POST /api/question/sql_query/evaluate` payload example:
     - `{"0":"SELECT 1 AS x"}`

6. `generic_evaluate`
   - `GET /api/question/{type}?...`
   - `POST /api/question/{type}/evaluate` payload generated from discovered layout ids if available

7. `resubmit_pattern`
   - `GET /api/question/{type}?...`
   - 3x `POST /api/question/{type}/evaluate` with mutated attempts (`attempt_1`, `attempt_2`, `attempt_3`)

8. `external_types_navigation`
   - `GET /api/question/regex?...`
   - `GET /api/question/xpath_xquery?...`

9. `auth_login_success`
   - `POST /api/auth/login` body: `{"username":"alice","password":"test"}`

10. `negative_resilience`
   - `GET /api/question/not_a_real_type` (expected `404`)
   - malformed preview/evaluate payloads (expected controlled `200`/`400`)

## Install

```bash
python -m pip install -r loadtest/requirements.txt
```

## Run headless (50 users)

```bash
locust -f loadtest/locustfile.py \
  --host http://141.76.47.6:5173 \
  --users 50 \
  --spawn-rate 5 \
  --run-time 10m \
  --headless \
  --csv loadtest/results/run_$(date +%Y%m%d_%H%M%S)
```

## Optional web UI

```bash
locust -f loadtest/locustfile.py --host http://141.76.47.6:5173
```

Then open `http://localhost:8089`.

## Environment overrides

- `LOADTEST_HOST` (default `http://141.76.47.6:5173`)
- `LOADTEST_API_PREFIX` (default `/api`)
- `LOADTEST_USERNAME` (default `alice`)
- `LOADTEST_PASSWORD` (default `test`)
- `LOADTEST_USERS` (default `50`)
- `LOADTEST_SPAWN_RATE` (default `5`)
- `LOADTEST_RUN_TIME` (default `10m`)
- `LOADTEST_WAIT_MIN` (default `1`)
- `LOADTEST_WAIT_MAX` (default `4`)

## Notes

- This suite exercises backend robustness through realistic API navigation patterns.
- Some paths intentionally trigger expected errors; these are marked successful when the expected status is returned.

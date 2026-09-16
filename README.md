# Robotic Arm Operations

A clean predictive-maintenance dashboard for industrial robot fleets. The project is a rewritten implementation of the same domain, with a small and explicit architecture:

- `backend/`: FastAPI application, SQLite persistence, validation, and risk scoring.
- `backend/ml/`: explainable inference, training configuration, and model comparison scripts. The baseline can be replaced without changing the API contract.
- `frontend/`: Streamlit operations dashboard and HTTP client. It includes fleet overview, telemetry input, maintenance, sensors, incidents, notifications, and operator access.
- `tests/`: integration tests covering health, seeded data, telemetry-to-prediction flow, auth, CRUD, and validation.

The API includes `/auth`, `/robots`, `/sensors`, `/telemetry`, `/health`, `/predictions`, `/maintenance`, `/incidents`, and `/notifications` resources. This keeps the new implementation at the same functional level as the reference while using a separate, smaller internal design.

## Run locally

From this directory, create an environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Start the API in one terminal:

```powershell
python -m backend
```

Start the dashboard in another terminal:

```powershell
streamlit run frontend/app.py
```

Open the URL printed by Streamlit. The dashboard reads `ROBOTIC_ARM_API_URL` when configured, defaulting to `http://127.0.0.1:8000`.

## Verify

```powershell
pytest -q
```

The first run creates `robotic_arm.db` and seeds three robot units plus two maintenance tasks. Posting telemetry persists the reading and creates a new risk prediction in one API request.

The ML utilities can be run directly:

```powershell
python -m backend.ml.train
python -m backend.ml.compare_models
python -m backend.ml.predict
```

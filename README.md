# Plan2Scene WebApp

A Dockerized full-stack application that wraps the [Plan2Scene](https://github.com/3dlg-hcvc/plan2scene) inference pipeline to convert 2D floorplans into 3D textured meshes and walkthrough videos.

## 🏗️ Architecture

This project uses a **Hybrid Architecture** to handle heavy ML inference:

* **Frontend:** React (Vite) + Tailwind CSS. Uses polling to check job status.
* **Backend:** FastAPI + Python `subprocess`. Implements an asynchronous job queue (BackgroundTasks) to prevent HTTP timeouts during long inference steps.
* **Infrastructure:** Docker Compose with NVIDIA Runtime support.

## 🚀 How to Run

### Option A: Demo Mode (Default - CPU Friendly)

Designed for testing the UI/UX and API flow without requiring a GPU or the heavy Plan2Scene weights.

```bash
docker compose up --build
```

* **Behavior:** Simulates the processing delay (4s) and returns pre-validated assets to demonstrate the pipeline stability.
* **Access:**
  - Frontend: http://localhost:5173
  - Backend API: http://localhost:8000/docs

### Option B: GPU Inference Mode (Production)

Executes the actual `gnn_texture_prop.py` and rendering scripts.

**Prerequisites:** NVIDIA GPU, NVIDIA Container Toolkit installed, and the `plan2scene` repo cloned as a sibling directory.

```bash
# 1. Clone the core repo sibling to this project
git clone https://github.com/3dlg-hcvc/plan2scene.git ../plan2scene

# 2. Run with GPU enabled
MODE=gpu docker compose up --build
```

## 🛠️ Tech Stack

* **Frontend:** React 18 + TypeScript + Vite + Tailwind CSS
* **Backend:** FastAPI + Uvicorn + Pydantic
* **API:** FastAPI
* **Task Queue:** In-Memory (expandable to Redis/Celery)
* **Containerization:** Docker & Nvidia-Docker

## 📁 Project Structure

```
plan2scene-webapp/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI endpoints
│   │   ├── worker.py         # Background task processor
│   │   ├── services/
│   │   │   └── plan2scene.py # Core pipeline logic
│   │   └── config.py         # Environment configuration
│   ├── demo_assets/          # Pre-rendered video/model for demo mode
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── App.tsx           # Main application
│   │   └── api.ts            # API client
│   ├── Dockerfile
│   └── package.json
└── docker-compose.yml        # Orchestration config
- **Frontend**: `frontend/src`
- **Assets**: `backend/demo_assets` contains placeholder files for demo mode.

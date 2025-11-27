# Plan2Scene WebApp

A production-ready, Dockerized web application that wraps the [Plan2Scene](https://github.com/3dlg-hcvc/plan2scene) inference pipeline. It converts 2D floor plans into immersive 3D walkthroughs and textured meshes.

![App Screenshot](./Screenshot%202025-11-27%20164430.png)

## 🎥 Demo Video

https://github.com/user-attachments/assets/94fddaa0-440b-40b6-a3d6-f6c680eecdce

## 🏗️ Architecture & Engineering Decisions


To ensure robustness and ease of evaluation, this application utilizes a **Hybrid Architecture**:

1.  **Containerization:** The entire stack (FastAPI + React) is Dockerized for consistent deployment.
2.  **Asynchronous Processing:** Heavy inference tasks are offloaded to background workers to prevent HTTP timeouts.
3.  **Dual-Mode Engine:**
    * **`MODE=demo` (Default):** Runs a deterministic simulation of the pipeline. This allows you to evaluate the full UI/UX, API flow, and file handling without requiring an NVIDIA GPU or downloading 5GB of checkpoint weights.
    * **`MODE=gpu`:** Configured to execute the actual `gnn_texture_prop.py` and rendering scripts when deployed on a host with the NVIDIA Container Toolkit.

## 🚀 Quick Start (Demo Mode)

Prerequisites: Docker & Docker Compose.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/leok974/plan2scene-webapp.git
    cd plan2scene-webapp
    ```

2.  **Start the application:**
    ```bash
    docker compose up --build
    ```

3.  **Access the App:**
    * Frontend: `http://localhost:5173`
    * Backend Docs: `http://localhost:8000/docs`

## 🛠️ Tech Stack

* **Frontend:** React (TypeScript), Tailwind CSS v4, Framer Motion (Animations), Lucide React.
* **Backend:** FastAPI, Python 3.9, Uvicorn.
* **Infrastructure:** Docker Compose, Volume mapping for asset persistence.

## ✨ Key Features
* **Polished UI:** Dark mode architectural aesthetic with glassmorphism.
* **Smart Downloads:** Implemented Blob-based downloading to force file saves (bypassing browser media playback).
* **Interactive Status:** Real-time visual feedback of the inference pipeline steps.

## 🚀 Advanced: GPU Mode (Real Plan2Scene Pipeline)

To run the actual Plan2Scene inference pipeline with full GPU acceleration:

**Prerequisites:** 
- NVIDIA GPU with CUDA support
- NVIDIA Container Toolkit installed
- Docker & Docker Compose

**Setup:**

1.  **Clone the original Plan2Scene repository alongside this project:**
    ```bash
    cd ..
    git clone https://github.com/3dlg-hcvc/plan2scene.git
    ```

2.  **Download the pretrained weights** as described in the [Plan2Scene README](https://github.com/3dlg-hcvc/plan2scene#download-trained-models).

3.  **Set environment variables and start the stack:**
    ```bash
    cd plan2scene-webapp
    MODE=gpu docker compose up --build
    ```

The backend will automatically detect GPU mode and execute the real `gnn_texture_prop.py` and rendering scripts instead of the demo simulation.

---
*Built by Leo for the Plan2Scene Assessment.*

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

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

### GPU Mode - Preprocessed Data (Existing Behavior)

This mode assumes you have preprocessed Rent3D++ data and runs only the texture propagation and rendering stages.

**Prerequisites:** 
- NVIDIA GPU with CUDA support
- NVIDIA Container Toolkit installed
- Docker & Docker Compose
- Preprocessed Plan2Scene data (Rent3D++ format)

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
    MODE=gpu PIPELINE_MODE=preprocessed docker compose up --build
    ```

The backend will run texture propagation and rendering on existing preprocessed data.

### GPU Mode - Full Pipeline (Complete Plan2Scene from R2V Vectors)

This mode runs the **complete Plan2Scene pipeline** starting from vectorized floorplan data (R2V output), addressing all stages that were previously manual:

**What this mode provides:**
- ✅ Floorplan vectorization → scene.json conversion (via r2v-to-plan2scene)
- ✅ Room embedding generation
- ✅ VGG-based texture crop selection
- ✅ GNN texture propagation
- ✅ Seam correction for tileable textures
- ✅ Texture embedding into scene.json
- ✅ Final 3D rendering

**Prerequisites:**
- All prerequisites from GPU Mode above, plus:
- R2V (Raster-to-Vector) output or annotation file
- [r2v-to-plan2scene](https://github.com/3dlg-hcvc/r2v-to-plan2scene) repository cloned

**Important Note on Floorplan Vectorization:**
This webapp assumes you have **already vectorized your floorplan image** using the official R2V tools. The webapp picks up from the R2V output stage and runs the complete Plan2Scene pipeline. To generate R2V outputs from raw floorplan images, use the [raster-to-vector](https://github.com/art-programmer/FloorplanTransformation) tool separately.

**Setup:**

1.  **Clone required repositories alongside this project:**
    ```bash
    cd ..
    
    # Plan2Scene core
    git clone https://github.com/3dlg-hcvc/plan2scene.git
    
    # R2V to Plan2Scene converter
    git clone https://github.com/3dlg-hcvc/r2v-to-plan2scene.git
    
    # (Optional) Raster-to-Vector for generating R2V outputs from images
    git clone https://github.com/art-programmer/FloorplanTransformation.git raster-to-vector
    ```

2.  **Download Plan2Scene pretrained weights** as described in the [Plan2Scene README](https://github.com/3dlg-hcvc/plan2scene#download-trained-models).

3.  **Set environment variables in `.env` or export them:**
    ```bash
    MODE=gpu
    PIPELINE_MODE=full
    PLAN2SCENE_ROOT=../plan2scene
    R2V_TO_PLAN2SCENE_ROOT=../r2v-to-plan2scene
    RASTER_TO_VECTOR_ROOT=../raster-to-vector  # Optional
    ```

4.  **Start the application:**
    ```bash
    docker compose up --build
    ```

5.  **Upload floorplan + R2V annotation:**
   - Upload your floorplan image (PNG/JPG)
   - Upload the corresponding R2V annotation file (JSON format from R2V tool)
   - The backend will automatically run the complete pipeline

**Example R2V Workflow (External to this app):**

If you need to generate R2V outputs from raw floorplan images:

```bash
cd raster-to-vector
# Follow the raster-to-vector README to:
# 1. Set up the R2V environment
# 2. Download R2V pretrained weights
# 3. Run vectorization on your floorplan image:
python main.py --image your_floorplan.png --output annotations/

# This generates a JSON annotation file you can upload to the webapp
```

**Pipeline Stages (Automatic in Full Mode):**

The full pipeline executes these stages sequentially:

1. **R2V → scene.json Conversion** - Converts vector data to Plan2Scene format
2. **Room Embeddings** - Generates texture embeddings for each room
3. **VGG Crop Selection** - Selects optimal texture crops using VGG network
4. **GNN Texture Propagation** - Propagates textures across surfaces using graph neural network
5. **Seam Correction** - Makes textures tileable for seamless surfaces
6. **Texture Embedding** - Embeds textures into final scene.json
7. **3D Rendering** - Generates walkthrough video and 3D model preview

**Troubleshooting:**

If a stage fails, check the backend logs for detailed error messages:
```bash
docker logs plan2scene-webapp-backend-1 --tail 100
```

Common issues:
- **"Plan2Scene repository not found"** - Ensure Plan2Scene is cloned at `../plan2scene`
- **"R2V conversion failed"** - Verify r2v-to-plan2scene is cloned and R2V annotation file is valid
- **"Script not found"** - Ensure Plan2Scene weights are downloaded and scripts exist
- **CUDA errors** - Verify NVIDIA Container Toolkit is installed and GPU is accessible

### Limitations & Future Work

**Phase 4 (Future):** Automatic raster-to-vector integration
- Currently, R2V vectorization must be done offline using external tools
- Future: Integrate R2V directly into the webapp for end-to-end processing from raw floorplan images
- This would eliminate the need to manually run raster-to-vector tools

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

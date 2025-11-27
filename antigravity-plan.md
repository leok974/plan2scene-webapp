# Antigravity Plan – Plan2Scene Web App

## Goal

Build a minimal but working end-to-end web app around the official Plan2Scene repo:

- React frontend:
  - Upload a 2D floorplan image.
  - Show job status.
  - Display links for the generated 3D scene + walkthrough video (later: full 3D viewer and video player).

- FastAPI backend:
  - `POST /api/convert` to accept an image and create a "job".
  - `GET /api/jobs/{job_id}` to return job status + URLs.
  - Serve static files under `/static` for scene/video assets.
  - Currently use a **demo Plan2Scene integration** that maps any upload to a sample output.
  - Later, wire `run_plan2scene_local()` to call the real Plan2Scene repo in a GPU environment.

- Deployment targets: easy to run locally (`npm run dev`, `uvicorn app.main:app`), later deployable to Railway.

## Constraints

- Keep dependencies lightweight for now.
- No real Plan2Scene heavy pipeline in the first iteration (no GPU / big datasets).
- The core requirement is: **file upload from frontend → backend → job status → static URLs return → frontend displays them**.

## Tasks for you (Antigravity)

1. **Backend setup**
   - Make sure `backend/app/main.py` exposes:
     - `GET /healthz`
     - `POST /api/convert`
     - `GET /api/jobs/{job_id}`
     - Static mount at `/static` for `backend/static`.
   - Implement a simple in-memory job store in `backend/app/jobs.py`.
   - Implement Pydantic models in `backend/app/schemas.py` for:
     - `JobCreateResponse`
     - `JobStatusResponse`
   - Implement `backend/app/plan2scene_integration.py` with:
     - `run_plan2scene_demo(upload_path, job_output_dir)` that:
       - Copies `static/jobs/sample/*` into `static/jobs/{job_id}/` or writes placeholder files.
     - A stub `run_plan2scene_local(...)` with TODO comments for calling the real repo.
   - Ensure `backend/requirements.txt` includes:
     - `fastapi`
     - `uvicorn[standard]`
     - `pydantic`
     - `python-multipart`
     - `aiofiles` (for StaticFiles)
   - Add CORS so the frontend (Vite dev server) can call the API in dev.

2. **Frontend setup**
   - Use Vite + React + TypeScript in `frontend/`.
   - Implement:
     - `src/api.ts` with functions:
       - `createJob(file: File): Promise<{ job_id: string }>`
       - `getJobStatus(jobId: string): Promise<JobStatus>`
     - `src/components/UploadForm.tsx`:
       - Lets user choose an image and triggers `createJob`.
     - `src/components/JobStatus.tsx`:
       - Shows job ID + polling status.
     - `src/components/ResultView.tsx`:
       - Shows scene URL and video URL as clickable links (later: 3D viewer + `<video>`).
     - `src/App.tsx`:
       - Orchestrates: upload → job ID → poll → show result.
   - Set `VITE_API_BASE` in `frontend/.env.example` and use it in `api.ts`.

3. **End-to-end check**

   - From repo root:
     - Backend:
       - `cd backend`
       - `pip install -r requirements.txt`
       - `uvicorn app.main:app --reload --port 8000`
     - Frontend:
       - `cd frontend`
       - `npm install`
       - `npm run dev` (default port 5173).
   - Verify flow:
     - Open frontend → upload image → POST `/api/convert`.
     - Poll `/api/jobs/{id}` → get `status: "done"` + `scene_url` + `video_url`.
     - Click URLs to confirm they resolve to static files served by backend.

4. **Nice-to-have (if there is time)**

   - In `ResultView`, add:
     - `<video controls src={videoUrl} />` for walkthrough.
     - Placeholder 3D viewer (later: integrate Three.js / react-three-fiber).
   - Add basic error handling + loading states.

## Non-goals (for this first iteration)

- Running the full Plan2Scene pipeline in production.
- GPU integration.
- Full 3D scene editing; viewing a static scene is enough for now.

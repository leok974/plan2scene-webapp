const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export interface JobCreateResponse {
    job_id: string;
    status: string;
}

export interface JobStatusResponse {
    job_id: string;
    status: string;
    scene_url?: string;
    video_url?: string;
    error?: string;
}

export async function createJob(file: File): Promise<JobCreateResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${API_BASE}/api/convert`, {
        method: "POST",
        body: formData
    });

    if (!res.ok) {
        throw new Error(`Failed to create job: ${res.status}`);
    }

    return res.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
    const res = await fetch(`${API_BASE}/api/jobs/${jobId}`);
    if (!res.ok) {
        throw new Error(`Failed to get job status: ${res.status}`);
    }
    return res.json();
}

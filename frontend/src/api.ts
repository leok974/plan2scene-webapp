const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8002";

export interface PipelineConfig {
    mode: "demo" | "gpu" | string;
    pipeline_mode: "preprocessed" | "full" | string;
}

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
    current_stage?: string;
    failed_stage?: string;
}

export async function getConfig(): Promise<PipelineConfig> {
    const res = await fetch(`${API_BASE}/api/config`);
    if (!res.ok) {
        throw new Error(`Failed to get config: ${res.status}`);
    }
    return res.json();
}

export async function createJob(
    file: File,
    r2vAnnotation?: File
): Promise<JobCreateResponse> {
    const formData = new FormData();
    formData.append("file", file);
    if (r2vAnnotation) {
        formData.append("r2v_annotation", r2vAnnotation);
    }

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

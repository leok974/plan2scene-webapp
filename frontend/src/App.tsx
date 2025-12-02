import React, { useState, useEffect } from "react";
import { ArrowRight, RotateCcw } from "lucide-react";
import Layout from "./components/Layout";
import UploadZone from "./components/UploadZone";
import ProcessingSteps from "./components/ProcessingSteps";
import ResultDashboard from "./components/ResultDashboard";
import PipelineModeBadge from "./components/PipelineModeBadge";
import { createJob, getJobStatus, getConfig, JobStatusResponse, PipelineConfig } from "./api";

const App: React.FC = () => {
    const [jobId, setJobId] = useState<string | null>(null);
    const [job, setJob] = useState<JobStatusResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [file, setFile] = useState<File | null>(null);
    const [r2vFile, setR2vFile] = useState<File | null>(null);
    const [config, setConfig] = useState<PipelineConfig | null>(null);

    // Fetch pipeline config on mount
    useEffect(() => {
        getConfig()
            .then(setConfig)
            .catch((err) => console.error("Failed to fetch config:", err));
    }, []);

    useEffect(() => {
        if (!jobId) return;

        let cancelled = false;
        const poll = async () => {
            try {
                const status = await getJobStatus(jobId);
                if (!cancelled) {
                    setJob(status);
                }
            } catch (err) {
                console.error('Error fetching job status:', err);
            }
        };

        poll();
        const interval = setInterval(poll, 2000); // Poll every 2s
        return () => {
            cancelled = true;
            clearInterval(interval);
        };
    }, [jobId]);

    const handleFileSelected = (selected: File | null) => {
        setFile(selected);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!file) return;
        try {
            setLoading(true);
            const res = await createJob(file, r2vFile || undefined);
            setJobId(res.job_id);
            setJob({ job_id: res.job_id, status: res.status });
        } catch (err) {
            console.error(err);
            alert("Failed to upload job");
        } finally {
            setLoading(false);
        }
    };

    const handleReset = () => {
        setJobId(null);
        setJob(null);
        setFile(null);
        setR2vFile(null);
        setLoading(false);
    };

    const showR2vUpload = config?.mode === "gpu" && config?.pipeline_mode === "full";

    return (
        <Layout>
            <div className="max-w-5xl mx-auto space-y-8">
                {/* Pipeline Mode Badge */}
                {config && (
                    <div className="flex justify-center mb-4">
                        <PipelineModeBadge 
                            mode={config.mode} 
                            pipelineMode={config.pipeline_mode}
                            gpuEnabled={config.gpu_enabled}
                        />
                    </div>
                )}

                {/* Hero Section */}
                {!jobId && !job && (
                    <div className="text-center mb-12">
                        <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">
                            Transform Floor Plans into
                            <span className="block text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400">
                                Immersive 3D Scenes
                            </span>
                        </h2>
                        <p className="text-slate-400 text-lg max-w-2xl mx-auto">
                            Upload your architectural drawing and let AI generate a fully textured
                            3D walkthrough in seconds
                        </p>
                    </div>
                )}

                {/* Upload Section */}
                {!jobId && (
                    <form onSubmit={handleSubmit} className="space-y-6">
                        <UploadZone 
                            onFileSelect={handleFileSelected} 
                            selectedFile={file}
                            onR2vFileSelect={setR2vFile}
                            r2vFile={r2vFile}
                            showR2vUpload={showR2vUpload}
                        />

                        {file && (
                            <div className="flex justify-center">
                                <button
                                    type="submit"
                                    disabled={loading}
                                    className="group flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 disabled:from-slate-700 disabled:to-slate-800 disabled:cursor-not-allowed text-white rounded-xl font-semibold transition-all shadow-lg shadow-blue-500/20 hover:shadow-blue-500/40 hover:scale-105 disabled:scale-100"
                                >
                                    {loading ? "Initializing..." : "Generate 3D Scene"}
                                    <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                                </button>
                            </div>
                        )}
                    </form>
                )}

                {/* Processing Section */}
                {job && job.status === "processing" && (
                    <ProcessingSteps 
                        status={job.status}
                        currentStage={job.current_stage}
                        failedStage={job.failed_stage}
                        pipelineMode={config?.pipeline_mode}
                    />
                )}

                {/* Error Section */}
                {job && job.status === "failed" && (
                    <div className="text-center space-y-4">
                        <div className="p-6 bg-red-500/10 border border-red-500/30 rounded-xl">
                            <p className="text-red-400 font-medium">
                                {job.failed_stage 
                                    ? `GPU pipeline failed during ${job.failed_stage}. See server logs for details.`
                                    : "Processing failed. Please try again."
                                }
                            </p>
                            {job.error && (
                                <p className="text-sm text-red-400/70 mt-2 font-mono">
                                    {job.error}
                                </p>
                            )}
                        </div>
                        <button
                            onClick={handleReset}
                            className="flex items-center gap-2 mx-auto px-6 py-3 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl font-medium transition-colors"
                        >
                            <RotateCcw className="w-5 h-5" />
                            Try Again
                        </button>
                    </div>
                )}

                {/* Results Section */}
                {job && job.status === "done" && jobId && (
                    <div className="space-y-6">
                        <ResultDashboard job={job} />
                        <div className="flex justify-center">
                            <button
                                onClick={handleReset}
                                className="flex items-center gap-2 px-6 py-3 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl font-medium transition-colors"
                            >
                                <RotateCcw className="w-5 h-5" />
                                Process Another Floor Plan
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </Layout>
    );
};

export default App;

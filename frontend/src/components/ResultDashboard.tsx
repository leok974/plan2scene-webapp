import React, { useState } from "react";
import { motion } from "framer-motion";
import { Download, Video, Box, Eye } from "lucide-react";
import { cn } from "../lib/utils";
import { JobStatusResponse } from "../api";

interface ResultDashboardProps {
    job: JobStatusResponse;
}

const ResultDashboard: React.FC<ResultDashboardProps> = ({ job }) => {
    const [activeTab, setActiveTab] = useState<"video" | "model">("video");
    const API_BASE = "http://localhost:8000";
    const videoUrl = job.video_url ? `${API_BASE}${job.video_url}` : "";
    const modelUrl = job.scene_url ? `${API_BASE}${job.scene_url}` : "";
    const downloadVideoUrl = `${API_BASE}/api/jobs/${job.job_id}/download/walkthrough`;
    const downloadModelUrl = `${API_BASE}/api/jobs/${job.job_id}/download/scene`;

    const forceDownload = async (url: string, filename: string) => {
        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error("Download failed");
            
            const blob = await response.blob();
            const blobUrl = window.URL.createObjectURL(blob);
            
            const link = document.createElement('a');
            link.href = blobUrl;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            
            document.body.removeChild(link);
            window.URL.revokeObjectURL(blobUrl);
        } catch (error) {
            console.error("Download failed:", error);
            window.open(url, '_blank');
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-6xl mx-auto"
        >
            {/* Success Header */}
            <div className="text-center mb-8">
                <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.2, type: "spring" }}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-green-500/10 border border-green-500/30 rounded-full mb-4"
                >
                    <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                    <p className="text-sm text-green-400 font-medium">Generation Complete</p>
                </motion.div>
                <h2 className="text-3xl font-bold text-slate-200 mb-2">
                    Your 3D Scene is Ready
                </h2>
                <p className="text-slate-400">
                    Explore the walkthrough or download the 3D model
                </p>
            </div>

            {/* Tabs */}
            <div className="flex gap-2 mb-6">
                <button
                    onClick={() => setActiveTab("video")}
                    className={cn(
                        "flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-medium transition-all",
                        activeTab === "video"
                            ? "bg-blue-500 text-white shadow-lg shadow-blue-500/20"
                            : "bg-slate-900/60 text-slate-400 hover:bg-slate-800/60"
                    )}
                >
                    <Video className="w-5 h-5" />
                    Walkthrough
                </button>
                <button
                    onClick={() => setActiveTab("model")}
                    className={cn(
                        "flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-medium transition-all",
                        activeTab === "model"
                            ? "bg-blue-500 text-white shadow-lg shadow-blue-500/20"
                            : "bg-slate-900/60 text-slate-400 hover:bg-slate-800/60"
                    )}
                >
                    <Box className="w-5 h-5" />
                    3D Model
                </button>
            </div>

            {/* Content */}
            <div className="bg-slate-900/60 backdrop-blur-sm border border-slate-800 rounded-2xl overflow-hidden">
                {activeTab === "video" ? (
                    <div className="aspect-video bg-black">
                        {videoUrl ? (
                            <video
                                src={videoUrl}
                                controls
                                autoPlay
                                loop
                                muted
                                className="w-full h-full object-contain"
                            >
                                Your browser does not support video playback.
                            </video>
                        ) : (
                            <div className="flex items-center justify-center h-full text-slate-400">
                                No video URL available
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="aspect-video bg-gradient-to-br from-slate-900 to-slate-950 flex items-center justify-center">
                        <div className="text-center space-y-4">
                            <Eye className="w-16 h-16 text-slate-600 mx-auto" />
                            <p className="text-slate-400">3D Model Viewer</p>
                            <p className="text-sm text-slate-500">
                                Download the GLB file to view in your preferred 3D software
                            </p>
                        </div>
                    </div>
                )}

                {/* Download Actions */}
                <div className="p-6 border-t border-slate-800">
                    <div className="flex flex-wrap gap-3">
                        <button
                            onClick={() => forceDownload(downloadVideoUrl, "plan2scene-walkthrough.mp4")}
                            className="flex items-center gap-2 px-6 py-3 bg-blue-500 hover:bg-blue-600 text-white rounded-xl font-medium transition-colors shadow-lg shadow-blue-500/20"
                        >
                            <Download className="w-5 h-5" />
                            Download Walkthrough
                        </button>
                        <button
                            onClick={() => forceDownload(downloadModelUrl, "plan2scene-model.glb")}
                            className="flex items-center gap-2 px-6 py-3 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl font-medium transition-colors"
                        >
                            <Download className="w-5 h-5" />
                            Download 3D Model (.glb)
                        </button>
                    </div>
                </div>
            </div>

            {/* Job ID Info */}
            <div className="mt-6 p-4 bg-slate-900/40 rounded-lg border border-slate-800">
                <p className="text-xs text-slate-500 font-mono">
                    Job ID: <span className="text-slate-400">{job.job_id}</span>
                </p>
            </div>
        </motion.div>
    );
};

export default ResultDashboard;

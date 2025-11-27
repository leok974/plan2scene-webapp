import React from "react";
import { Video, Box } from "lucide-react";
import type { JobStatusResponse } from "../api";

interface ResultViewProps {
    job: JobStatusResponse | null;
}

const ResultView: React.FC<ResultViewProps> = ({ job }) => {
    if (!job || job.status !== "done") return null;

    const getFullUrl = (url: string) => {
        if (url.startsWith("http")) return url;
        const apiBase = import.meta.env.VITE_API_BASE || "http://localhost:8000";
        return `${apiBase}${url}`;
    };

    return (
        <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
                <div className="flex items-center gap-2 mb-4">
                    <Box className="w-5 h-5 text-purple-400" />
                    <h3 className="text-lg font-semibold text-gray-200">3D Scene</h3>
                </div>
                <div className="aspect-video bg-gray-900 rounded flex items-center justify-center text-gray-500">
                    {/* Placeholder for 3D viewer */}
                    <a href={getFullUrl(job.scene_url!)} target="_blank" rel="noreferrer" className="text-blue-400 hover:underline">
                        Download Scene (GLB)
                    </a>
                </div>
            </div>

            <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
                <div className="flex items-center gap-2 mb-4">
                    <Video className="w-5 h-5 text-pink-400" />
                    <h3 className="text-lg font-semibold text-gray-200">Walkthrough</h3>
                </div>
                <div className="aspect-video bg-gray-900 rounded overflow-hidden">
                    <video
                        controls
                        className="w-full h-full object-cover"
                        src={getFullUrl(job.video_url!)}
                    />
                </div>
            </div>
        </div>
    );
};

export default ResultView;

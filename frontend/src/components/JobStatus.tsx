import React from "react";
import { Loader2, CheckCircle, AlertCircle } from "lucide-react";
import type { JobStatusResponse } from "../api";

interface JobStatusProps {
    job: JobStatusResponse | null;
    isLoading: boolean;
}

const JobStatus: React.FC<JobStatusProps> = ({ job, isLoading }) => {
    if (!job && !isLoading) return null;

    return (
        <div className="mt-8 p-6 bg-gray-800 rounded-lg border border-gray-700">
            <div className="flex items-center justify-center gap-3">
                {isLoading || (job && job.status === "processing") ? (
                    <>
                        <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
                        <span className="text-blue-400 font-medium">Processing...</span>
                    </>
                ) : job?.status === "done" ? (
                    <>
                        <CheckCircle className="w-6 h-6 text-green-500" />
                        <span className="text-green-400 font-medium">Complete!</span>
                    </>
                ) : (
                    <>
                        <AlertCircle className="w-6 h-6 text-red-500" />
                        <span className="text-red-400 font-medium">Error</span>
                    </>
                )}
            </div>
            {job && <p className="mt-2 text-xs text-gray-500 font-mono">Job ID: {job.job_id}</p>}
        </div>
    );
};

export default JobStatus;

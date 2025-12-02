import React from "react";
import { Cpu, Zap, Sparkles } from "lucide-react";

interface PipelineModeBadgeProps {
    mode: string;
    pipelineMode: string;
    gpuEnabled?: boolean;
}

const PipelineModeBadge: React.FC<PipelineModeBadgeProps> = ({ mode, pipelineMode, gpuEnabled = true }) => {
    const getBadgeConfig = () => {
        if (mode === "demo") {
            return {
                label: "Demo Mode (No GPU)",
                icon: Sparkles,
                colors: "bg-slate-700/50 border-slate-600 text-slate-300"
            };
        }
        
        // CPU Fallback Mode
        if (mode === "gpu" && !gpuEnabled) {
            return {
                label: pipelineMode === "full" 
                    ? "CPU Mode: Full R2V + Plan2Scene Pipeline" 
                    : "CPU Mode: Preprocessed (Rent3D++)",
                icon: Cpu,
                colors: "bg-gradient-to-r from-amber-500/20 to-orange-500/20 border-amber-500/50 text-amber-300"
            };
        }
        
        if (mode === "gpu" && pipelineMode === "full") {
            return {
                label: "GPU Mode: Full R2V + Plan2Scene Pipeline",
                icon: Zap,
                colors: "bg-gradient-to-r from-purple-500/20 to-blue-500/20 border-purple-500/50 text-purple-300"
            };
        }
        
        if (mode === "gpu" && pipelineMode === "preprocessed") {
            return {
                label: "GPU Mode: Preprocessed (Rent3D++)",
                icon: Zap,
                colors: "bg-gradient-to-r from-blue-500/20 to-cyan-500/20 border-blue-500/50 text-blue-300"
            };
        }
        
        return {
            label: `Mode: ${mode}`,
            icon: Cpu,
            colors: "bg-slate-700/50 border-slate-600 text-slate-300"
        };
    };

    const config = getBadgeConfig();
    const Icon = config.icon;

    return (
        <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full border backdrop-blur-sm ${config.colors}`}>
            <Icon className="w-4 h-4" />
            <span className="text-sm font-medium">{config.label}</span>
        </div>
    );
};

export default PipelineModeBadge;

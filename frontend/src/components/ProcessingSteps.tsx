import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Check, Loader2, Cpu, Layers, Paintbrush, Box } from "lucide-react";

interface ProcessingStepsProps {
    status: string;
}

const steps = [
    { id: 1, label: "Analyzing Geometry", icon: Layers, delay: 0 },
    { id: 2, label: "Rectifying Surfaces", icon: Cpu, delay: 1000 },
    { id: 3, label: "Synthesizing Textures", icon: Paintbrush, delay: 2000 },
    { id: 4, label: "Rendering 3D Scene", icon: Box, delay: 3000 },
];

const ProcessingSteps: React.FC<ProcessingStepsProps> = ({ status }) => {
    const [completedSteps, setCompletedSteps] = useState<number[]>([]);

    useEffect(() => {
        if (status === "processing") {
            // Reset steps
            setCompletedSteps([]);
            
            // Animate steps completion
            steps.forEach((step) => {
                setTimeout(() => {
                    setCompletedSteps((prev) => [...prev, step.id]);
                }, step.delay);
            });
        }
    }, [status]);

    if (status !== "processing") {
        return null;
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-2xl mx-auto"
        >
            <div className="bg-slate-900/60 backdrop-blur-sm border border-slate-800 rounded-xl p-8">
                <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-blue-500/10 rounded-lg">
                        <Cpu className="w-5 h-5 text-blue-400" />
                    </div>
                    <h3 className="text-lg font-semibold text-slate-200">
                        Neural Processing Pipeline
                    </h3>
                </div>

                <div className="space-y-4">
                    {steps.map((step, index) => {
                        const isCompleted = completedSteps.includes(step.id);
                        const isCurrent =
                            !isCompleted &&
                            (index === 0 || completedSteps.includes(steps[index - 1].id));
                        const Icon = step.icon;

                        return (
                            <motion.div
                                key={step.id}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: index * 0.1 }}
                                className="flex items-center gap-4"
                            >
                                <div
                                    className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-300 ${
                                        isCompleted
                                            ? "bg-blue-500/20 border-2 border-blue-500"
                                            : isCurrent
                                            ? "bg-blue-500/10 border-2 border-blue-500/50"
                                            : "bg-slate-800/50 border-2 border-slate-700"
                                    }`}
                                >
                                    <AnimatePresence mode="wait">
                                        {isCompleted ? (
                                            <motion.div
                                                key="check"
                                                initial={{ scale: 0, rotate: -180 }}
                                                animate={{ scale: 1, rotate: 0 }}
                                                exit={{ scale: 0 }}
                                            >
                                                <Check className="w-5 h-5 text-blue-400" />
                                            </motion.div>
                                        ) : isCurrent ? (
                                            <motion.div
                                                key="loader"
                                                animate={{ rotate: 360 }}
                                                transition={{
                                                    duration: 1,
                                                    repeat: Infinity,
                                                    ease: "linear",
                                                }}
                                            >
                                                <Loader2 className="w-5 h-5 text-blue-400" />
                                            </motion.div>
                                        ) : (
                                            <Icon className="w-5 h-5 text-slate-600" />
                                        )}
                                    </AnimatePresence>
                                </div>

                                <div className="flex-1">
                                    <p
                                        className={`font-mono text-sm transition-colors ${
                                            isCompleted || isCurrent
                                                ? "text-slate-300"
                                                : "text-slate-600"
                                        }`}
                                    >
                                        {isCompleted && "✓ "}
                                        {isCurrent && "> "}
                                        {step.label}
                                        {isCurrent && (
                                            <span className="ml-2 text-blue-400 animate-pulse">
                                                ...
                                            </span>
                                        )}
                                    </p>
                                </div>

                                {/* Progress bar */}
                                <div className="flex-shrink-0 w-24 h-1 bg-slate-800 rounded-full overflow-hidden">
                                    <motion.div
                                        className="h-full bg-gradient-to-r from-blue-500 to-blue-400"
                                        initial={{ width: "0%" }}
                                        animate={{
                                            width: isCompleted
                                                ? "100%"
                                                : isCurrent
                                                ? "60%"
                                                : "0%",
                                        }}
                                        transition={{ duration: 0.5 }}
                                    />
                                </div>
                            </motion.div>
                        );
                    })}
                </div>

                {/* Terminal-style log */}
                <div className="mt-6 p-4 bg-slate-950/50 rounded-lg border border-slate-800">
                    <p className="text-xs font-mono text-slate-500">
                        <span className="text-green-400">$</span> Running Plan2Scene v2.0 Neural
                        Renderer
                    </p>
                    {completedSteps.length > 0 && (
                        <p className="text-xs font-mono text-slate-500 mt-1">
                            <span className="text-blue-400">[INFO]</span> Processing with GPU
                            acceleration...
                        </p>
                    )}
                </div>
            </div>
        </motion.div>
    );
};

export default ProcessingSteps;

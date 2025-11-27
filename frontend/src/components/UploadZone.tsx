import React, { useCallback, useState } from "react";
import { motion } from "framer-motion";
import { Upload, FileImage, Sparkles } from "lucide-react";
import { cn } from "../lib/utils";

interface UploadZoneProps {
    onFileSelect: (file: File | null) => void;
    selectedFile: File | null;
}

const UploadZone: React.FC<UploadZoneProps> = ({ onFileSelect, selectedFile }) => {
    const [isDragging, setIsDragging] = useState(false);

    const handleDrop = useCallback(
        (e: React.DragEvent) => {
            e.preventDefault();
            setIsDragging(false);
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith("image/")) {
                onFileSelect(file);
            }
        },
        [onFileSelect]
    );

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = () => {
        setIsDragging(false);
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0] ?? null;
        onFileSelect(file);
    };

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="w-full"
        >
            <div
                className={cn(
                    "relative border-2 rounded-2xl p-12 transition-all duration-300 cursor-pointer",
                    "bg-slate-900/40 backdrop-blur-sm",
                    isDragging
                        ? "border-blue-500 bg-blue-500/10 scale-105"
                        : "border-dashed border-slate-700 hover:border-blue-500/50"
                )}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
            >
                {/* Animated gradient overlay */}
                <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-transparent to-purple-500/5 rounded-2xl pointer-events-none" />

                <label className="relative flex flex-col items-center justify-center gap-6 cursor-pointer">
                    <motion.div
                        animate={{
                            scale: isDragging ? 1.1 : 1,
                            rotate: isDragging ? 5 : 0,
                        }}
                        className={cn(
                            "p-6 rounded-2xl transition-colors",
                            isDragging ? "bg-blue-500/20" : "bg-slate-800/50"
                        )}
                    >
                        {selectedFile ? (
                            <FileImage className="w-12 h-12 text-blue-400" />
                        ) : (
                            <Upload className="w-12 h-12 text-slate-400" />
                        )}
                    </motion.div>

                    <div className="text-center space-y-2">
                        <div className="flex items-center gap-2 justify-center">
                            <Sparkles className="w-4 h-4 text-blue-400" />
                            <p className="text-xl font-semibold text-slate-200">
                                {selectedFile ? selectedFile.name : "Upload Floor Plan"}
                            </p>
                        </div>
                        <p className="text-sm text-slate-400">
                            {selectedFile
                                ? "File ready for processing"
                                : "Drop your architectural drawing here or click to browse"}
                        </p>
                        {!selectedFile && (
                            <p className="text-xs text-slate-500 font-mono">
                                Supported: PNG, JPG, JPEG
                            </p>
                        )}
                    </div>

                    <input
                        type="file"
                        className="hidden"
                        accept="image/*"
                        onChange={handleChange}
                    />
                </label>
            </div>
        </motion.div>
    );
};

export default UploadZone;

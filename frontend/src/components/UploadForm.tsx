import React, { useCallback } from "react";
import { Upload, FileImage } from "lucide-react";

interface UploadFormProps {
    onJobCreated: (jobId: string) => void;
    onFileSelect: (file: File | null) => void;
}

const UploadForm: React.FC<UploadFormProps> = ({ onFileSelect }) => {
    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith("image/")) {
            onFileSelect(file);
        }
    }, [onFileSelect]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0] ?? null;
        onFileSelect(file);
    };

    return (
        <div
            className="border-2 border-dashed border-gray-600 rounded-lg p-8 hover:border-blue-500 transition-colors cursor-pointer bg-gray-800"
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
        >
            <label className="flex flex-col items-center justify-center gap-4 cursor-pointer">
                <div className="p-4 bg-gray-700 rounded-full">
                    <Upload className="w-8 h-8 text-blue-400" />
                </div>
                <div className="text-center">
                    <p className="text-lg font-medium text-gray-200">Drop your floorplan here</p>
                    <p className="text-sm text-gray-400">or click to browse</p>
                </div>
                <input
                    type="file"
                    className="hidden"
                    accept="image/*"
                    onChange={handleChange}
                />
            </label>
        </div>
    );
};

export default UploadForm;

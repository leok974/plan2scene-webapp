import React from "react";
import { motion } from "framer-motion";
import { Building2 } from "lucide-react";

interface LayoutProps {
    children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
            {/* Navbar */}
            <nav className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-xl sticky top-0 z-50">
                <div className="container mx-auto px-6 py-4">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-blue-500/10 rounded-lg">
                            <Building2 className="w-6 h-6 text-blue-400" />
                        </div>
                        <h1 className="text-xl font-bold text-white tracking-tight">
                            PLAN<span className="text-blue-400">2</span>SCENE
                        </h1>
                        <div className="ml-auto">
                            <span className="text-xs text-slate-500 font-mono">
                                AI Architectural Synthesis
                            </span>
                        </div>
                    </div>
                </div>
            </nav>

            {/* Main Content */}
            <main className="container mx-auto px-6 py-12">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                >
                    {children}
                </motion.div>
            </main>

            {/* Footer */}
            <footer className="border-t border-slate-800 mt-20">
                <div className="container mx-auto px-6 py-6">
                    <p className="text-center text-slate-500 text-sm">
                        Powered by Plan2Scene Neural Architecture
                    </p>
                </div>
            </footer>
        </div>
    );
};

export default Layout;

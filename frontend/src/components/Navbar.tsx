import { Search, Bell, ChevronRight } from 'lucide-react';

export const Navbar = () => {
    return (
        <header className="h-16 bg-layout-surface border-b border-gray-200 flex items-center justify-between px-6">

            <div className="flex items-center text-sm">
                <span className="text-content-muted">Workspace</span>
                <ChevronRight size={14} className="mx-2 text-gray-400" />
                <span className="font-medium text-content-main">Dashboard</span>
            </div>

            <div className="flex items-center gap-5">

                <div className="relative hidden md:block">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                    <input
                        type="text"
                        placeholder="Buscar data..."
                        className="pl-9 pr-16 py-1.5 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-brand w-64 transition-all"
                    />
                </div>

                <button className="relative p-1 text-content-muted hover:text-content-main transition-colors cursor-pointer">
                    <Bell size={20} />
                    <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full border border-white"></span>
                </button>

                <button className="w-8 h-8 bg-brand-light text-gray-700 rounded-full border border-gray-300 flex items-center justify-center text-sm font-bold transition-transform hover:scale-105 cursor-pointer">
                    JL
                </button>
            </div>
        </header>
    );
};
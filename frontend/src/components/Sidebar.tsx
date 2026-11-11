import {
    AlignStartVertical, LayoutDashboard,
    Search,
    Users,
    Briefcase,
    History,
    Settings,
    HelpCircle
} from 'lucide-react';

interface MenuItem {
    name: string;
    icon: React.ElementType;
    href: string;
    isActive?: boolean;
}

const mainMenuItems: MenuItem[] = [
    { name: 'Dashboard', icon: LayoutDashboard, href: '/', isActive: true },
    { name: 'Buscar negocios', icon: Search, href: '/buscar' },
    { name: 'Mis prospectos', icon: Users, href: '/prospectos' },
    { name: 'Deals', icon: Briefcase, href: '/deals' },
    { name: 'Historial', icon: History, href: '/historial' },
]

export const Sidebar = () => {
    return (
        <aside className="bg-white w-64 h-screen border-r border-gray-200 flex  flex-col justify-between px-4 py-6">
            <div>
                <div className="flex items-center gap-2 px-2 mb-8">
                    <div className="bg-principal text-white p-1 rounded-md">
                        <AlignStartVertical />
                    </div>
                    <span className='text-xl font-bold text-gray-900'>RepuSense</span>
                </div>

                <div className="flex items-center gap-3 px-3 py-2 mb-6 border-gray-300 border rounded-lg">
                    <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-sm font-semibold text-gray-500">
                        U
                    </div>
                    <div className="flex flex-col">
                        <span className="text-sm font-semibold">Usuario 1</span>
                        <span className="text-xs">Capturista</span>
                    </div>
                </div>

                <div className='mb-4'>
                    <p className='px-2 text-xs font-semibold text-gray-800 mb-2 tracking-wider'>Selecion de menu</p>
                    <nav className='space-y-1'>
                        {mainMenuItems.map((opcion) => {
                            const Icon = opcion.icon;
                            return (
                                <button key={opcion.name} className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors
                                 ${opcion.isActive ? 'bg-hover-activo text-text-activo font-medium' : 'text-gray-700 hover:bg-gray-100 hover:text-gray-800'}`}>
                                    <Icon size={18} />
                                    {opcion.name}
                                </button>
                            )
                        })}
                    </nav>
                </div>
            </div>

            <div className="space-y-1 border-t border-gray-300 pt-4">
                <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm hover:bg-gray-100 hover:text-content-main transition-colors">
                    <Settings size={18} />
                    Settings
                </button>
                <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm hover:bg-gray-100 hover:text-content-main transition-colors">
                    <HelpCircle size={18} />
                    Help center
                </button>
            </div>
        </aside>
    );
}
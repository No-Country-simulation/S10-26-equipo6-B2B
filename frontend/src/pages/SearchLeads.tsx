import { useState } from 'react';
import { Search, MapPin, Briefcase } from 'lucide-react';
import { ProspectosEncontrados } from '../components/ProspectosEncontrados';

export const SearchLeads = () => {
    const [rubro, setRubro] = useState('');
    const [ubicacion, setUbicacion] = useState('');
    const [fuentes, setFuentes] = useState({
        googleMaps: false,
        tripAdvisor: false
    });

    return (
        <div className="flex flex-col min-h-full max-w-7xl mx-auto">

            <div className="mb-6 flex justify-between items-end">
                <div>
                    <h1 className="text-2xl font-bold text-content-main mb-1">Buscar negocios</h1>
                    <p className="text-sm text-content-muted">Define los parámetros para buscar información de negocios con áreas de mejora</p>
                </div>
            </div>

            <div className="bg-layout-surface p-6 rounded-xl border border-gray-200 shadow-sm mb-6">
                <div className="grid grid-cols-1 md:grid-cols-12 gap-6">

                    <div className="col-span-1 md:col-span-4">
                        <label className="block text-xs font-semibold text-content-muted mb-2">Rubro / Nicho</label>
                        <div className="relative">
                            <Briefcase className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                            <input
                                type="text"
                                placeholder="Ej. Restaurantes, Hoteles, Cafeterías.."
                                value={rubro}
                                onChange={(e) => setRubro(e.target.value)}
                                className="w-full pl-9 pr-4 py-2 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-light focus:border-brand transition-all"
                            />
                        </div>
                    </div>

                    <div className="col-span-1 md:col-span-4">
                        <label className="block text-xs font-semibold text-content-muted mb-2">Ubicación</label>
                        <div className="relative">
                            <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                            <input
                                type="text"
                                placeholder="Ej. Mexico, Puebla..."
                                value={ubicacion}
                                onChange={(e) => setUbicacion(e.target.value)}
                                className="w-full pl-9 pr-4 py-2 bg-white border border-gray-200 rounded-lg text-sm appearance-none focus:outline-none focus:ring-2 focus:ring-brand-light focus:border-brand transition-all" />
                        </div>
                    </div>

                    <div className="col-span-1 md:col-span-4">
                        <label className="block text-xs font-semibold text-content-muted mb-2">Fuentes a consultar</label>
                        <div className="flex gap-4 mt-4">
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={fuentes.googleMaps}
                                    onChange={(e) => setFuentes({ ...fuentes, googleMaps: e.target.checked })}
                                    className="w-4.5 h-4.5 text-gray-900 border-gray-300 accent-principal focus:ring-principal cursor-pointer"
                                />
                                <span className="text-sm text-content-main">Google Maps</span>
                            </label>
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={fuentes.tripAdvisor}
                                    onChange={(e) => setFuentes({ ...fuentes, tripAdvisor: e.target.checked })}
                                    className="w-4.5 h-4.5 text-gray-900 border-gray-300 accent-principal cursor-pointer"
                                />
                                <span className="text-sm text-content-main">TripAdvisor</span>
                            </label>
                        </div>
                    </div>
                </div>

                <div className="mt-6 flex">
                    <button className="flex items-center gap-2 px-6 py-2.5 bg-principal text-white text-sm font-medium rounded-lg hover:bg-green-900 transition-colors shadow-sm cursor-pointer">
                        <Search size={16} />
                        Buscar negocios
                    </button>
                </div>
            </div>

            <ProspectosEncontrados />

        </div>
    );
};
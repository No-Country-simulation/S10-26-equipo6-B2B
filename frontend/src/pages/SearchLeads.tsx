import { useState } from 'react';
import { Search, MapPin, Briefcase, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { ProspectosEncontrados } from '../components/ProspectosEncontrados';
import { api } from '../services/api';
import { useLeads } from '../hooks/useLeads';

export const SearchLeads = () => {
    const [rubro, setRubro] = useState('');
    const [ubicacion, setUbicacion] = useState('');
    const [fuentes, setFuentes] = useState({
        googleMaps: true,
        tripAdvisor: false
    });
    const [isSearching, setIsSearching] = useState(false);
    const [searchMessage, setSearchMessage] = useState<string | null>(null);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    const { refreshLeads } = useLeads();

    const handleSearch = async () => {
        if (!rubro.trim() || !ubicacion.trim()) {
            setErrorMessage('Por favor especifica un rubro y una ubicación para prospectar.');
            return;
        }

        setErrorMessage(null);
        setIsSearching(true);
        setSearchMessage('Iniciando prospección en segundo plano...');

        try {
            const busqueda = await api.iniciarBusqueda({
                sector: rubro.trim(),
                city: ubicacion.trim(),
                max_rating: 3.5,
                min_reviews: 10,
            });

            setSearchMessage('Recolectando negocios con áreas de mejora, reseñas y analizando con IA...');

            let intentos = 0;
            const maxIntentos = 15;
            const intervalo = setInterval(async () => {
                intentos++;
                try {
                    const estado = await api.obtenerEstadoBusqueda(busqueda.search_id);
                    if (estado.status === 'COMPLETED' || estado.status === 'FAILED' || intentos >= maxIntentos) {
                        clearInterval(intervalo);
                        setIsSearching(false);
                        if (estado.status === 'COMPLETED') {
                            setSearchMessage(`¡Prospección completada! Se procesaron ${estado.leads_encontrados} leads calificados.`);
                        } else if (estado.status === 'FAILED') {
                            setErrorMessage(`La prospección finalizó con observaciones: ${estado.error_message || 'Verifica la fuente de datos.'}`);
                            setSearchMessage(null);
                        } else {
                            setSearchMessage('Prospección encolada en el worker de segundo plano.');
                        }
                        await refreshLeads();
                    }
                } catch {
                    clearInterval(intervalo);
                    setIsSearching(false);
                    await refreshLeads();
                }
            }, 2000);
        } catch (err: unknown) {
            setIsSearching(false);
            const msg = err instanceof Error ? err.message : 'No se pudo conectar con el servidor de la API.';
            setErrorMessage(msg);
            setSearchMessage(null);
        }
    };

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
                                disabled={isSearching}
                                className="w-full pl-9 pr-4 py-2 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-light focus:border-brand transition-all disabled:bg-gray-50"
                            />
                        </div>
                    </div>

                    <div className="col-span-1 md:col-span-4">
                        <label className="block text-xs font-semibold text-content-muted mb-2">Ubicación</label>
                        <div className="relative">
                            <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                            <input
                                type="text"
                                placeholder="Ej. Mexico, Puebla, Bogotá..."
                                value={ubicacion}
                                onChange={(e) => setUbicacion(e.target.value)}
                                disabled={isSearching}
                                className="w-full pl-9 pr-4 py-2 bg-white border border-gray-200 rounded-lg text-sm appearance-none focus:outline-none focus:ring-2 focus:ring-brand-light focus:border-brand transition-all disabled:bg-gray-50" />
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

                {searchMessage && (
                    <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2 text-sm text-green-800">
                        {isSearching ? <Loader2 size={16} className="animate-spin text-green-600" /> : <CheckCircle2 size={16} className="text-green-600" />}
                        <span>{searchMessage}</span>
                    </div>
                )}

                {errorMessage && (
                    <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-sm text-red-800">
                        <AlertCircle size={16} className="text-red-600" />
                        <span>{errorMessage}</span>
                    </div>
                )}

                <div className="mt-6 flex">
                    <button
                        onClick={handleSearch}
                        disabled={isSearching}
                        className="flex items-center gap-2 px-6 py-2.5 bg-principal text-white text-sm font-medium rounded-lg hover:bg-green-900 transition-colors shadow-sm cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isSearching ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
                        {isSearching ? 'Prospectando...' : 'Buscar negocios'}
                    </button>
                </div>
            </div>

            <ProspectosEncontrados />

        </div>
    );
};

import { useState } from 'react';
import { Search, Mail, Calendar, ExternalLink, RotateCcw, Archive } from 'lucide-react';
import { useLeads } from '../context/ProspectosContext';
import { useNavigate } from 'react-router-dom';

export const Historial = () => {
    const [searchTerm, setSearchTerm] = useState('');
    const navigate = useNavigate();

    // Consumimos leads y la función updateLeadStatus para poder restaurar si hace falta
    const { leads, updateLeadStatus } = useLeads();

    // Filtramos ÚNICAMENTE los leads marcados como 'Descartado'
    const discardedLeads = leads
        .filter((lead) => lead.status === 'Descartado')
        .filter((lead) => {
            const term = searchTerm.toLowerCase();
            const matchCompany = lead.name.toLowerCase().includes(term);
            const matchContact = (lead.contactName || '').toLowerCase().includes(term);
            return matchCompany || matchContact;
        });

    return (
        <div className="flex flex-col min-h-full max-w-7xl mx-auto pb-8">

            {/* Cabecera */}
            <div className="mb-6 flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-content-main mb-1 flex items-center gap-2">
                        <Archive size={24} className="text-content-muted" />
                        Historial de Descartados
                    </h1>
                    <p className="text-sm text-content-muted">
                        Registro de negocios descartados o sin interés comercial. Puedes restaurarlos en cualquier momento.
                    </p>
                </div>
            </div>

            {/* Barra de búsqueda */}
            <div className="bg-layout-surface border border-gray-200 rounded-t-xl p-4 flex flex-col sm:flex-row justify-between items-center gap-4">
                <span className="text-sm font-medium text-content-muted">
                    Total archivados: <strong className="text-content-main">{discardedLeads.length}</strong>
                </span>

                <div className="relative w-full sm:w-64">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                    <input
                        type="text"
                        placeholder="Buscar en el historial..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-9 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-light transition-all"
                    />
                </div>
            </div>

            {/* Tabla */}
            <div className="bg-white border-x border-b border-gray-200 rounded-b-xl shadow-sm overflow-hidden w-full overflow-x-auto">
                <div className="min-w-225">

                    {/* Encabezados */}
                    <div className="grid grid-cols-12 gap-4 px-5 py-3 bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-800 uppercase tracking-wider">
                        <div className="col-span-3">Empresa</div>
                        <div className="col-span-3">Contacto Principal</div>
                        <div className="col-span-2">Estado</div>
                        <div className="col-span-2">Última Actividad</div>
                        <div className="col-span-2 text-center">Acciones</div>
                    </div>

                    {/* Filas dinámicas */}
                    <div className="divide-y divide-gray-100">
                        {discardedLeads.length === 0 ? (
                            <div className="p-8 text-center text-sm text-content-muted">
                                {searchTerm
                                    ? 'No se encontraron registros en el historial con ese nombre.'
                                    : 'No tienes leads descartados en tu historial.'}
                            </div>
                        ) : (
                            discardedLeads.map((prospect) => (
                                <div key={prospect.id} className="grid grid-cols-12 gap-4 px-5 py-4 items-center hover:bg-gray-50 transition-colors">

                                    {/* Empresa */}
                                    <div className="col-span-3 flex items-center gap-3">
                                        <div className="w-8 h-8 rounded bg-gray-100 text-gray-500 flex items-center justify-center font-bold text-xs shrink-0">
                                            {prospect.name.charAt(0)}
                                        </div>
                                        <div className="flex flex-col">
                                            <span className="text-sm font-semibold text-content-main">{prospect.name}</span>
                                            <span className="text-xs text-content-muted">{prospect.category}</span>
                                        </div>
                                    </div>

                                    {/* Contacto */}
                                    <div className="col-span-3 flex flex-col">
                                        <span className="text-sm font-medium text-content-main">
                                            {prospect.contactName || 'Sin contacto asignado'}
                                        </span>
                                        <div className="flex items-center gap-2 mt-0.5">
                                            <Mail size={12} className="text-gray-400 shrink-0" />
                                            <span className="text-xs text-content-muted truncate">
                                                {prospect.email || 'Correo no registrado'}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Estado (Badge Descartado) */}
                                    <div className="col-span-2 flex items-center">
                                        <span className="px-2.5 py-1 text-xs font-medium border rounded-full bg-red-50 text-red-700 border-red-200">
                                            Descartado
                                        </span>
                                    </div>

                                    {/* Última Actividad */}
                                    <div className="col-span-2 flex items-center gap-1.5 text-sm text-content-muted">
                                        <Calendar size={14} />
                                        {prospect.lastActivity || 'Reciente'}
                                    </div>

                                    {/* Acciones: Restaurar o Ver detalle */}
                                    <div className="col-span-2 flex justify-center items-center gap-2">
                                        <button
                                            onClick={() => updateLeadStatus(prospect.id, 'Nuevo')}
                                            className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors cursor-pointer"
                                            title="Devolver a Mis Prospectos"
                                        >
                                            <RotateCcw size={14} />
                                            Restaurar
                                        </button>

                                        <button
                                            onClick={() => navigate(`/lead/${prospect.id}`)}
                                            className="p-1.5 text-gray-400 hover:text-brand hover:bg-brand-light rounded-lg transition-colors cursor-pointer"
                                            title="Ver ficha del negocio"
                                        >
                                            <ExternalLink size={16} />
                                        </button>
                                    </div>

                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Footer de Paginación */}
                <div className="flex items-center justify-between px-5 py-3 border-t border-gray-100 bg-white rounded-b-xl">
                    <span className="text-sm text-content-muted">
                        Mostrando {discardedLeads.length > 0 ? 1 : 0} a {discardedLeads.length} de {discardedLeads.length} resultados
                    </span>
                    <div className="flex gap-2">
                        <button className="px-3 py-1 border border-gray-200 rounded text-sm text-gray-400 cursor-not-allowed">
                            Anterior
                        </button>
                        <button className="px-3 py-1 border border-gray-200 rounded text-sm text-content-main hover:bg-gray-50 cursor-pointer">
                            Siguiente
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
import { useState } from 'react';
import { Search, Mail, Calendar, ExternalLink } from 'lucide-react';
import { type Lead } from '../utils/mockData';
import { useLeads } from '../context/ProspectosContext';
import { useNavigate } from 'react-router-dom';

export const MisProspectos = () => {
    const [searchTerm, setSearchTerm] = useState('');
    const navigate = useNavigate();

    const { leads } = useLeads();


    const filteredProspects = leads
        .filter((lead) => lead.isSaved && lead.status !== 'Descartado')
        .filter((lead) => {
            const term = searchTerm.toLowerCase();
            const matchCompany = lead.name.toLowerCase().includes(term);
            const matchContact = (lead.contactName || '').toLowerCase().includes(term);
            return matchCompany || matchContact;
        });

    const getStatusBadge = (status: Lead['status']) => {
        const styles: Record<string, string> = {
            'Nuevo': 'bg-blue-50 text-blue-700 border-blue-200',
            'Pendiente': 'bg-orange-50 text-orange-700 border-orange-200',
            'Contactado': 'bg-yellow-50 text-yellow-700 border-yellow-200',
            'En Negociación': 'bg-purple-50 text-purple-700 border-purple-200',
            'Cliente Cerrado': 'bg-green-50 text-green-700 border-green-200',
            'Descartado': 'bg-red-50 text-red-700 border-red-200',
        };
        return (
            <span className={`px-2.5 py-1 text-xs font-medium border rounded-full ${styles[status] || styles['Nuevo']}`}>
                {status}
            </span>
        );
    };

    return (
        <div className="flex flex-col min-h-full max-w-7xl mx-auto pb-8">

            <div className="mb-6 flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-content-main mb-1">Mis Prospectos</h1>
                    <p className="text-sm text-content-muted">Gestiona tus negociaciones activas y clientes cerrados.</p>
                </div>
            </div>

            <div className="bg-layout-surface border border-gray-200 rounded-t-xl p-4 flex flex-col sm:flex-row justify-end items-center gap-4">

                <div className="relative w-full sm:w-64">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                    <input
                        type="text"
                        placeholder="Buscar empresa o contacto..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-9 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-light transition-all"
                    />
                </div>
            </div>

            <div className="bg-white border-x border-b border-gray-200 rounded-b-xl shadow-sm overflow-hidden w-full overflow-x-auto">
                <div className="min-w-225">

                    <div className="grid grid-cols-12 gap-4 px-5 py-3 bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-800 uppercase tracking-wider">
                        <div className="col-span-3">Empresa</div>
                        <div className="col-span-3">Contacto Principal</div>
                        <div className="col-span-2">Estado (Pipeline)</div>
                        <div className="col-span-2">Última Actividad</div>
                        <div className="col-span-2 text-center">Acciones</div>
                    </div>

                    {/* Filas dinamicas */}
                    <div className="divide-y divide-gray-100">
                        {/* 5. Estado vacío amigable por si aún no hay prospectos guardados o no hay coincidencias */}
                        {filteredProspects.length === 0 ? (
                            <div className="p-8 text-center text-sm text-content-muted">
                                {searchTerm
                                    ? 'No se encontraron prospectos que coincidan con tu búsqueda.'
                                    : 'Aún no tienes prospectos guardados en tu cartera. Explora negocios y guárdalos para darles seguimiento.'}
                            </div>
                        ) : (
                            filteredProspects.map((prospect) => (
                                <div key={prospect.id} className="grid grid-cols-12 gap-4 px-5 py-4 items-center hover:bg-gray-50 transition-colors">

                                    {/* Empresa */}
                                    <div className="col-span-3 flex items-center gap-3">
                                        <div className="w-8 h-8 rounded bg-brand-light text-brand flex items-center justify-center font-bold text-xs shrink-0">
                                            {prospect.name.charAt(0)}
                                        </div>
                                        <span className="text-sm font-semibold text-content-main">{prospect.name}</span>
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

                                    {/* Estado */}
                                    <div className="col-span-2 flex items-center">
                                        {getStatusBadge(prospect.status)}
                                    </div>

                                    {/* Última Actividad */}
                                    <div className="col-span-2 flex items-center gap-1.5 text-sm text-content-muted">
                                        <Calendar size={14} />
                                        {prospect.lastActivity || 'Reciente'}
                                    </div>

                                    <div className="col-span-2 flex justify-center items-center">
                                        <button
                                            onClick={() => navigate(`/lead/${prospect.id}`)}
                                            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-brand bg-brand-light/60 hover:bg-brand hover:text-white rounded-lg transition-colors cursor-pointer"
                                            title="Ver ficha completa del prospecto"
                                        >
                                            Ver detalle
                                            <ExternalLink size={14} />
                                        </button>
                                    </div>

                                </div>
                            ))
                        )}
                    </div>
                </div>
                <div className="flex items-center justify-between px-5 py-3 border-t border-gray-100 bg-white rounded-b-xl">
                    <span className="text-sm text-content-muted">
                        Mostrando {filteredProspects.length > 0 ? 1 : 0} a {filteredProspects.length} de {filteredProspects.length} resultados
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
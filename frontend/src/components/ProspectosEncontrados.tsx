import { ExternalLink, Download, Clock, CheckCircle2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useLeads } from '../hooks/useLeads';

export const ProspectosEncontrados = () => {
    const navigate = useNavigate();

    const { leads } = useLeads();
    const leadsEnFrio = leads.filter((lead) => !lead.isSaved);

    return (
        <div className="bg-white border border-gray-200 rounded-xl flex flex-col shadow-sm hover:shadow-md transition-shadow">

            <div className="flex justify-between items-center p-5 border-b border-gray-100">
                <div className="flex items-center gap-3">
                    <h3 className="text-content-main text-lg font-semibold">Resultados de búsqueda</h3>
                    {/* 3. Actualizamos el contador con la lista filtrada */}
                    <span className="bg-gray-100 text-gray-600 text-xs font-medium px-2.5 py-0.5 rounded-full">
                        {leadsEnFrio.length}
                    </span>
                </div>
                <button className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-brand hover:bg-brand-light rounded-lg transition-colors cursor-pointer">
                    <Download size={16} />
                    Exportar CSV
                </button>
            </div>

            <div className="w-full overflow-x-auto">
                <div className="min-w-200">
                    <div className="grid grid-cols-12 gap-4 px-5 py-3 bg-gray-50 border-b border-gray-100 text-xs font-semibold text-content-muted uppercase tracking-wider">
                        <div className="col-span-4">Negocio</div>
                        <div className="col-span-2">Calificacion ↓</div>
                        <div className="col-span-2">Reseñas</div>
                        <div className="col-span-2">Estado</div>
                        <div className="col-span-2 text-center">Accion</div>
                    </div>

                    <div className="divide-y divide-gray-100">
                        {leadsEnFrio.length === 0 ? (
                            <div className="p-8 text-center text-sm text-content-muted">
                                Todos los leads encontrados ya fueron guardados en "Mis prospectos".
                            </div>
                        ) : (
                            leadsEnFrio.map((lead) => (
                                <div key={lead.id} className="grid grid-cols-12 gap-4 px-5 py-4 items-center hover:bg-gray-50 transition-colors">

                                    <div className="col-span-4 flex flex-col">
                                        <span className="text-sm font-semibold text-content-main">{lead.name}</span>
                                        <span className="text-xs text-content-muted">{lead.category}</span>
                                    </div>

                                    <div className="col-span-2 flex items-center gap-1 font-medium text-content-main text-sm">
                                        {lead.rating}
                                    </div>

                                    <div className="col-span-2">
                                        <span className="inline-flex items-center px-2 py-0.5 rounded bg-brand-light text-brand text-xs font-medium">
                                            {lead.reviewsCount}
                                        </span>
                                    </div>

                                    {/* Tomando en cuenta si existe algun error en la busqueda se puede poner como estatus si se toma de la API */}
                                    <div className="col-span-2 flex items-center gap-1.5 text-sm">
                                        {lead.status === 'Pendiente' ? (
                                            <>
                                                <Clock size={14} className="text-orange-500" />
                                                <span className="text-orange-600 font-medium">Pendiente</span>
                                            </>
                                        ) : (
                                            <>
                                                <CheckCircle2 size={14} className="text-gray-400" />
                                                <span className="text-content-muted">Conectado</span>
                                            </>
                                        )}
                                    </div>

                                    <div className="col-span-2 flex justify-center items-center">
                                        <button
                                            onClick={() => navigate(`/lead/${lead.id}`)}
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
            </div>

            <div className="flex items-center justify-between px-5 py-3 border-t border-gray-100 bg-white rounded-b-xl">
                <span className="text-sm text-content-muted">
                    Mostrando {leadsEnFrio.length > 0 ? 1 : 0} a {leadsEnFrio.length} de {leadsEnFrio.length} resultados
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
    );
};
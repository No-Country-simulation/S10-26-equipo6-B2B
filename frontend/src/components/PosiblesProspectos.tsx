import { ExternalLink, Lightbulb, Star } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useLeads } from "../hooks/useLeads";

export const PosiblesProspectos = () => {
    const navigate = useNavigate();

    const { leads } = useLeads();

    const posiblesLeads = leads.filter((lead) => !lead.isSaved);

    return (
        <div className="bg-white border border-gray-100 rounded-xl flex flex-col mt-6 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex justify-between items-center p-5 border-b border-gray-200">
                <div>
                    <h3 className="text-gray-800 text-lg font-semibold flex items-center gap-2">
                        <Lightbulb size={20} className="text-principal" /> Posibles Leads
                    </h3>
                    <p className="text-sm text-gray-800 mt-1">
                        Prospectos con calificación crítica y alto volumen de reseñas
                    </p>
                </div>
            </div>

            <div className="w-full">
                <div className="grid grid-cols-12 gap-4 px-5 py-3 bg-gray-100 border-b border-gray-100 text-xs font-semibold text-content-muted uppercase tracking-wider">
                    <div className="col-span-5">Negocio</div>
                    <div className="col-span-2">Rubro</div>
                    <div className="col-span-3">Estado de Reputación</div>
                    <div className="col-span-2 text-center">Acción Sugerida</div>
                </div>

                <div className="divide-y divide-gray-100">
                    {posiblesLeads.length === 0 ? (
                        <div className="p-8 text-center text-sm text-content-muted">
                            ¡Buen trabajo! No tienes oportunidades pendientes por revisar en este momento.
                        </div>
                    ) : (
                        posiblesLeads.map((lead) => (
                            <div key={lead.id} className="grid grid-cols-12 gap-4 px-5 py-4 items-center hover:bg-gray-50 transition-colors">

                                <div className="col-span-5 flex flex-col">
                                    <span className="text-sm font-semibold text-content-main">{lead.name}</span>
                                </div>

                                <div className="col-span-2">
                                    <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-600">
                                        {lead.category}
                                    </span>
                                </div>

                                <div className="col-span-3 flex items-center gap-3">
                                    <div className={`flex items-center gap-1 ${lead.rating >= 3.0 ? 'text-calificaciones' : 'text-red-600'} font-bold text-sm`}>
                                        <Star size={14} className="fill-current" />
                                        {lead.rating}
                                    </div>
                                    <span className="text-xs text-content-muted">
                                        ({lead.reviewsCount} reseñas)
                                    </span>
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
    );
};
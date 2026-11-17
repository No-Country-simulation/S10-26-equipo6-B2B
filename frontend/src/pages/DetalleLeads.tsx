import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useLeads } from '../hooks/useLeads';
import { type Review, type Lead } from '../utils/mockData';
import { api } from '../services/api';

import {
    ArrowLeft,
    Star,
    Store,
    Phone,
    Globe,
    Mail,
    TrendingUp,
    AlertTriangle,
    MessageSquare,
    Copy,
    Check,
    CheckCircle2,
    BookmarkPlus,
    Sparkles,
    Loader2
} from 'lucide-react';

export const DetalleLeads = () => {
    // Se cacha el parámetro :id de la URL para poder acceder a los datos especificos
    const { id } = useParams();
    const navigate = useNavigate();

    // Consumimos el estado global y las funciones
    const { leads, saveLeadToProspects, updateLeadStatus } = useLeads();

    // Buscamos el lead actual en el estado global
    const lead = leads.find((item) => item.id === id) || leads[0];

    const [subject, setSubject] = useState(lead.draftSubject);
    const [body, setBody] = useState(lead.draftBody);
    const [copied, setCopied] = useState(false);
    const [reviews, setReviews] = useState<Review[]>(lead.recentReviews || []);
    const [isRegenerating, setIsRegenerating] = useState(false);

    // Carga de reseñas reales desde la API si están disponibles
    useEffect(() => {
        if (lead?.id) {
            api.obtenerResenasLead(lead.id).then((items) => {
                if (items && items.length > 0) {
                    setReviews(items);
                }
            }).catch(() => {});
        }
    }, [lead?.id]);

    // Sincronizamos el borrador si cambia el lead seleccionado
    const [prevLeadId, setPrevLeadId] = useState(lead.id);
    if (lead.id !== prevLeadId) {
        setPrevLeadId(lead.id);
        setSubject(lead.draftSubject);
        setBody(lead.draftBody);
        setReviews(lead.recentReviews || []);
    }

    // Función para regenerar análisis y cold email con IA
    const handleRegenerateAI = async () => {
        setIsRegenerating(true);
        try {
            const data = await api.generarAnalisisIA(lead.id);
            if (data.email_subject) setSubject(data.email_subject);
            if (data.email_first_paragraph) setBody(data.email_first_paragraph);
        } catch (err) {
            console.warn('No se pudo regenerar con IA:', err);
        } finally {
            setIsRegenerating(false);
        }
    };

    // Función para copiar el correo al portapapeles
    const handleCopyDraft = () => {
        const fullText = `Asunto: ${subject}\n\n${body}`;
        navigator.clipboard.writeText(fullText);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000); // Regresa el botón a su estado normal tras 2 seg
    };

    return (
        <div className="max-w-6xl mx-auto pb-8">
            <button
                onClick={() => navigate(-1)}
                className="flex items-center gap-2 text-sm text-content-muted hover:text-content-main mb-6 transition-colors cursor-pointer"
            >
                <ArrowLeft size={16} />
                Volver al listado
            </button>

            {/* CABECERA DEL NEGOCIO */}
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4 mb-8">
                <div>
                    <span className="inline-block px-3 py-1 bg-gray-100 text-content-muted text-xs font-medium rounded-full mb-2">
                        {lead.category}
                    </span>
                    <h1 className="text-3xl font-bold text-content-main mb-2">
                        {lead.name}
                    </h1>
                    <div className="flex items-center gap-2 text-sm">
                        <span className="font-bold text-content-main">{lead.rating.toString().replace('.', ',')}</span>
                        <div className="flex items-center text-amber-400">
                            {[...Array(5)].map((_, i) => (
                                <Star
                                    key={i}
                                    size={16}
                                    className={i < Math.floor(lead.rating) ? 'fill-current' : 'text-gray-300'}
                                />
                            ))}
                        </div>
                        <span className="text-content-muted">{lead.reviewsCount} reseñas</span>
                    </div>
                </div>

                <div className="w-full sm:w-64 flex flex-col items-start sm:items-end">
                    {!lead.isSaved ? (
                        <div className="w-full">
                            <span className="block text-xs font-medium text-content-muted mb-1.5">
                                Lead sin asignar
                            </span>
                            <button
                                onClick={() => saveLeadToProspects(lead.id)}
                                className="w-full py-2.5 px-4 bg-brand hover:bg-brand-dark text-white text-sm font-medium rounded-lg flex items-center justify-center gap-2 transition-colors shadow-sm cursor-pointer"
                            >
                                <BookmarkPlus size={18} />
                                Guardar Lead
                            </button>
                        </div>
                    ) : (
                        <div className="w-full">
                            <label className="flex items-center justify-between text-xs font-medium text-content-muted mb-1.5">
                                <span>Estado del prospecto</span>
                                <span className="text-brand flex items-center gap-1">
                                    <CheckCircle2 size={12} /> En tu CRM
                                </span>
                            </label>
                            <select
                                value={lead.status}
                                onChange={(e) => updateLeadStatus(lead.id, e.target.value as Lead['status'])}
                                className="w-full px-3.5 py-2.5 bg-layout-surface border border-gray-200 rounded-lg text-sm font-medium text-content-main focus:outline-none focus:ring-2 focus:ring-brand-light focus:border-brand cursor-pointer shadow-sm"
                            >
                                <option value="Nuevo">Nuevo</option>
                                <option value="Contactado">Contactado</option>
                                <option value="En Negociación">En Negociación</option>
                                <option value="Cliente Cerrado">Cliente Cerrado</option>
                                <option value="Descartado">Descartado</option>
                            </select>
                        </div>
                    )}
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                {/* TARJETA 1: Información del negocio */}
                <div className="bg-layout-surface border border-gray-200 rounded-xl p-6 shadow-sm">
                    <div className="flex items-center gap-2.5 mb-6">
                        <Store size={20} className="text-content-muted" />
                        <h2 className="text-lg font-bold text-content-main">Información del negocio</h2>
                    </div>

                    <div className="space-y-4 text-sm">
                        <div className="flex items-center gap-3">
                            <Phone size={18} className="text-gray-400" />
                            <span className={lead.phone ? 'text-content-main' : 'text-content-muted'}>
                                {lead.phone || 'Teléfono no disponible'}
                            </span>
                        </div>

                        <div className="flex items-center gap-3">
                            <Globe size={18} className="text-gray-400" />
                            {lead.website ? (
                                <a
                                    href={`https://${lead.website}`}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-blue-600 hover:underline"
                                >
                                    {lead.website}
                                </a>
                            ) : (
                                <span className="text-content-muted">Sitio web no disponible</span>
                            )}
                        </div>

                        <div className="flex items-center gap-3">
                            <Mail size={18} className="text-gray-400" />
                            <span className={lead.email ? 'text-content-main' : 'text-content-muted'}>
                                {lead.email || 'Correo no encontrado'}
                            </span>
                        </div>
                    </div>
                </div>

                {/* TARJETA 2: Análisis de reputación */}
                <div className="bg-layout-surface border border-gray-200 rounded-xl p-6 shadow-sm">
                    <div className="flex items-center gap-2.5 mb-6">
                        <TrendingUp size={20} className="text-brand" />
                        <h2 className="text-lg font-bold text-content-main">Análisis de reputación</h2>
                    </div>

                    <div className="bg-red-50/80 border border-red-100 rounded-xl p-4 flex items-start gap-3.5 mb-4">
                        <AlertTriangle size={22} className="text-red-500 shrink-0 mt-0.5" />
                        <div>
                            <span className="block text-xs font-medium text-red-600 mb-1">Problema principal</span>
                            <span className="block text-base font-bold text-content-main">{lead.mainProblem}</span>
                        </div>
                    </div>

                    <p className="text-sm text-content-muted">
                        {lead.problemDescription}
                    </p>
                </div>

                {/* TARJETA 3: Últimas reseñas */}
                <div className="bg-layout-surface border border-gray-200 rounded-xl p-6 shadow-sm">
                    <div className="flex items-center gap-2.5 mb-6">
                        <MessageSquare size={20} className="text-content-muted" />
                        <h2 className="text-lg font-bold text-content-main">Últimas reseñas</h2>
                    </div>

                    <div className="space-y-4">
                        {(reviews && reviews.length > 0 ? reviews : lead.recentReviews).map((review) => (
                            <div key={review.id} className="bg-gray-50 border border-gray-100 rounded-xl p-4">
                                <div className="flex justify-between items-center mb-2">
                                    <span className="text-sm font-bold text-content-main">{review.author}</span>
                                    <span className="text-xs text-content-muted">{review.date}</span>
                                </div>
                                <p className="text-sm text-content-muted leading-relaxed">
                                    {review.comment}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>

                {/* TARJETA 4: Borrador de correo */}
                <div className="bg-layout-surface border border-gray-200 rounded-xl p-6 shadow-sm flex flex-col justify-between">
                    <div>
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-2.5">
                                <Mail size={20} className="text-content-muted" />
                                <h2 className="text-lg font-bold text-content-main">Borrador de correo</h2>
                            </div>
                            <button
                                type="button"
                                onClick={handleRegenerateAI}
                                disabled={isRegenerating}
                                className="inline-flex items-center gap-1.5 text-xs font-semibold text-brand hover:text-brand-dark transition-colors cursor-pointer disabled:opacity-50"
                                title="Generar nueva propuesta con IA basada en reseñas"
                            >
                                {isRegenerating ? (
                                    <>
                                        <Loader2 size={14} className="animate-spin" />
                                        <span>Analizando...</span>
                                    </>
                                ) : (
                                    <>
                                        <Sparkles size={14} />
                                        <span>Regenerar con IA</span>
                                    </>
                                )}
                            </button>
                        </div>

                        <div className="space-y-4 mb-5">
                            <div>
                                <label className="block text-xs font-medium text-content-muted mb-1.5">Asunto</label>
                                <input
                                    type="text"
                                    value={subject}
                                    onChange={(e) => setSubject(e.target.value)}
                                    className="w-full px-3.5 py-2 bg-white border border-gray-200 rounded-lg text-sm text-content-main focus:outline-none focus:ring-2 focus:ring-brand-light focus:border-brand"
                                />
                            </div>

                            <div>
                                <textarea
                                    rows={5}
                                    value={body}
                                    onChange={(e) => setBody(e.target.value)}
                                    className="w-full p-3.5 bg-white border border-gray-200 rounded-lg text-sm text-content-main leading-relaxed focus:outline-none focus:ring-2 focus:ring-brand-light focus:border-brand resize-none"
                                />
                            </div>
                        </div>
                    </div>

                    <button
                        onClick={handleCopyDraft}
                        className="w-full py-2.5 px-4 bg-brand hover:bg-brand-dark text-white text-sm font-medium rounded-lg flex items-center justify-center gap-2 transition-colors shadow-sm cursor-pointer"
                    >
                        {copied ? (
                            <>
                                <Check size={18} />
                                ¡Borrador copiado!
                            </>
                        ) : (
                            <>
                                <Copy size={18} />
                                Copiar borrador
                            </>
                        )}
                    </button>
                </div>

            </div>
        </div>
    );
};
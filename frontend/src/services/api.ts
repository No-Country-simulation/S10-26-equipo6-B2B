/**
 * Cliente HTTP para comunicar el Frontend con la API REST de FastAPI (/api/v1).
 */

import { type Lead, type Review } from '../utils/mockData';

const API_BASE = '/api/v1';

export interface ApiLeadResponse {
  business_id: string;
  name: string;
  sector: string | null;
  city: string | null;
  rating: number | null;
  total_reviews: number | null;
  phone_number: string | null;
  website: string | null;
  email: string | null;
  lead_status: string;
  created_at: string;
  ai_analysis?: {
    analysis_id: string;
    category: string;
    pain_points_summary: string | null;
    email_subject: string | null;
    email_first_paragraph: string | null;
    ai_model: string | null;
    generated_at: string;
  } | null;
  contacts?: Array<{
    contact_id: string;
    business_id: string;
    contact_type: string;
    value: string;
    source: string;
    created_at: string;
  }>;
}

export interface PaginatedLeadsResponse {
  items: ApiLeadResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
}

export interface SearchCreatePayload {
  sector: string;
  city: string;
  max_rating?: number;
  min_reviews?: number;
}

export interface SearchResponse {
  search_id: string;
  status: string;
  leads_encontrados: number;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
}

export interface ApiReview {
  review_id: string;
  author: string | null;
  rating: number | null;
  content: string | null;
  reviewed_at: string | null;
}

/** Convierte el DTO del backend al modelo `Lead` utilizado por los componentes de React. */
export function mapApiLeadToFrontend(apiLead: ApiLeadResponse): Lead {
  const isSaved = apiLead.lead_status !== 'NEW';

  let status: Lead['status'] = 'Nuevo';
  if (apiLead.lead_status === 'CONTACTED') status = 'Contactado';
  else if (apiLead.lead_status === 'DISCARDED') status = 'Descartado';

  const defaultProblem = 'Sin clasificar';
  const mainProblem = apiLead.ai_analysis?.category || defaultProblem;
  const problemDescription =
    apiLead.ai_analysis?.pain_points_summary ||
    'Análisis de reputación pendiente o en procesamiento.';

  const draftSubject =
    apiLead.ai_analysis?.email_subject ||
    `Oportunidad de mejora en reputación para ${apiLead.name}`;
  const draftBody =
    apiLead.ai_analysis?.email_first_paragraph ||
    `Hola equipo de ${apiLead.name}, revisamos las opiniones recientes de sus clientes y queremos compartirles una propuesta...`;

  const email =
    apiLead.email ||
    apiLead.contacts?.find((c) => c.contact_type === 'EMAIL')?.value ||
    null;

  return {
    id: apiLead.business_id,
    name: apiLead.name,
    category: apiLead.sector || 'Comercio Local',
    rating: apiLead.rating ?? 0,
    reviewsCount: apiLead.total_reviews ?? 0,
    isSaved,
    status,
    email,
    phone: apiLead.phone_number,
    website: apiLead.website,
    lastActivity: `Detectado ${new Date(apiLead.created_at).toLocaleDateString()}`,
    mainProblem,
    problemDescription,
    recentReviews: [],
    draftSubject,
    draftBody,
  };
}

export const api = {
  /** Lanza una nueva prospección asíncrona (POST /api/v1/busquedas). */
  async iniciarBusqueda(datos: SearchCreatePayload): Promise<SearchResponse> {
    const res = await fetch(`${API_BASE}/busquedas`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(datos),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Error ${res.status} al iniciar búsqueda`);
    }
    return res.json();
  },

  /** Consulta el progreso o estado de una búsqueda (GET /api/v1/busquedas/{id}). */
  async obtenerEstadoBusqueda(searchId: string): Promise<SearchResponse> {
    const res = await fetch(`${API_BASE}/busquedas/${searchId}`);
    if (!res.ok) throw new Error(`Error ${res.status} al consultar búsqueda`);
    return res.json();
  },

  /** Obtiene la lista de prospectos paginados y filtrados (GET /api/v1/leads). */
  async listarLeads(filtros?: {
    search_id?: string;
    city?: string;
    sector?: string;
    status?: string;
    page?: number;
    limit?: number;
  }): Promise<PaginatedLeadsResponse> {
    const params = new URLSearchParams();
    if (filtros?.search_id) params.set('search_id', filtros.search_id);
    if (filtros?.city) params.set('city', filtros.city);
    if (filtros?.sector) params.set('sector', filtros.sector);
    if (filtros?.status) params.set('status', filtros.status);
    if (filtros?.page) params.set('page', String(filtros.page));
    if (filtros?.limit) params.set('limit', String(filtros.limit));

    const url = `${API_BASE}/leads?${params.toString()}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Error ${res.status} al obtener leads`);
    return res.json();
  },

  /** Obtiene el detalle de un lead específico (GET /api/v1/leads/{id}). */
  async obtenerLead(leadId: string): Promise<ApiLeadResponse> {
    const res = await fetch(`${API_BASE}/leads/${leadId}`);
    if (!res.ok) throw new Error(`Error ${res.status} al obtener lead`);
    return res.json();
  },

  /** Obtiene las reseñas negativas de un lead (GET /api/v1/leads/{id}/reviews). */
  async obtenerResenasLead(leadId: string): Promise<Review[]> {
    const res = await fetch(`${API_BASE}/leads/${leadId}/reviews`);
    if (!res.ok) return [];
    const items: ApiReview[] = await res.json();
    return items.map((r) => ({
      id: r.review_id,
      author: r.author || 'Cliente anónimo',
      date: r.reviewed_at ? new Date(r.reviewed_at).toLocaleDateString() : 'Reciente',
      comment: r.content || 'Sin comentario textual',
    }));
  },

  /** Cambia el estado comercial del lead (PATCH /api/v1/leads/{id}/status). */
  async actualizarEstadoLead(leadId: string, nuevoEstado: string): Promise<ApiLeadResponse> {
    let apiStatus = 'NEW';
    const statusUpper = nuevoEstado.toUpperCase();
    if (statusUpper.includes('CONTACT') || statusUpper.includes('NEGOC') || statusUpper.includes('CERRAD')) {
      apiStatus = 'CONTACTED';
    } else if (statusUpper.includes('DESCART')) {
      apiStatus = 'DISCARDED';
    }

    const res = await fetch(`${API_BASE}/leads/${leadId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lead_status: apiStatus }),
    });
    if (!res.ok) throw new Error(`Error ${res.status} al actualizar estado`);
    return res.json();
  },

  /** Genera o regenera el análisis de IA bajo demanda (POST /api/v1/leads/{id}/ai-analysis). */
  async generarAnalisisIA(leadId: string) {
    const res = await fetch(`${API_BASE}/leads/${leadId}/ai-analysis`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(`Error ${res.status} al generar análisis de IA`);
    return res.json();
  },

  /** Ejecuta el rastreo web secundario para enriquecer contactos (POST /api/v1/leads/{id}/enrich-contacts). */
  async enriquecerContactos(leadId: string) {
    const res = await fetch(`${API_BASE}/leads/${leadId}/enrich-contacts`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(`Error ${res.status} al enriquecer contactos`);
    return res.json();
  },
};

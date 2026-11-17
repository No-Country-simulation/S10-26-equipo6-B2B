import { useState, useEffect, useCallback, type ReactNode } from 'react';
import { ALL_MOCK_LEADS, type Lead } from '../utils/mockData';
import { ProspectosContext } from '../hooks/useLeads';
import { api, mapApiLeadToFrontend } from '../services/api';

export const LeadsProvider = ({ children }: { children: ReactNode }) => {
    const [leads, setLeads] = useState<Lead[]>(ALL_MOCK_LEADS);
    const [isLoading, setIsLoading] = useState<boolean>(false);

    const refreshLeads = useCallback(async () => {
        setIsLoading(true);
        try {
            const data = await api.listarLeads({ limit: 100 });
            if (data.items && data.items.length > 0) {
                const apiLeads = data.items.map(mapApiLeadToFrontend);
                setLeads(apiLeads);
            }
        } catch (error) {
            console.warn('API no disponible o sin conexión; utilizando catálogo mock de respaldo:', error);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        let isMounted = true;
        api.listarLeads({ limit: 100 })
            .then((data) => {
                if (isMounted && data.items && data.items.length > 0) {
                    setLeads(data.items.map(mapApiLeadToFrontend));
                }
            })
            .catch((error) => {
                console.warn('API no disponible o sin conexión; utilizando catálogo mock de respaldo:', error);
            });
        return () => {
            isMounted = false;
        };
    }, []);

    // Acción 1: Pasar un lead en frío a "Mis prospectos" (status CONTACTED en backend)
    const saveLeadToProspects = (id: string) => {
        setLeads((prevLeads) =>
            prevLeads.map((lead) =>
                lead.id === id
                    ? { ...lead, isSaved: true, status: 'Nuevo', lastActivity: 'Guardado hoy' }
                    : lead
            )
        );
        api.actualizarEstadoLead(id, 'CONTACTED').catch((err) =>
            console.debug('No se pudo sincronizar estado con backend:', err)
        );
    };

    // Acción 2: Cambiar el estatus del pipeline (solo para leads guardados)
    const updateLeadStatus = (id: string, newStatus: Lead['status']) => {
        setLeads((prevLeads) =>
            prevLeads.map((lead) =>
                lead.id === id
                    ? { ...lead, status: newStatus, lastActivity: 'Actualizado hoy' }
                    : lead
            )
        );
        api.actualizarEstadoLead(id, newStatus).catch((err) =>
            console.debug('No se pudo sincronizar estado con backend:', err)
        );
    };

    // Acción 3: Exportar prospectos a formato CSV (RF5)
    const exportToCsv = () => {
        if (!leads || leads.length === 0) return;

        const headers = ['Nombre', 'Rubro', 'Calificación', 'Reseñas', 'Teléfono', 'Email', 'Web', 'Problema', 'Estado', 'Asunto'];
        const rows = leads.map((l) => [
            `"${(l.name || '').replace(/"/g, '""')}"`,
            `"${(l.category || '').replace(/"/g, '""')}"`,
            l.rating,
            l.reviewsCount,
            `"${(l.phone || '').replace(/"/g, '""')}"`,
            `"${(l.email || '').replace(/"/g, '""')}"`,
            `"${(l.website || '').replace(/"/g, '""')}"`,
            `"${(l.mainProblem || '').replace(/"/g, '""')}"`,
            `"${l.status}"`,
            `"${(l.draftSubject || '').replace(/"/g, '""')}"`,
        ]);

        const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
        const blob = new Blob([`\uFEFF${csvContent}`], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.setAttribute('href', url);
        link.setAttribute('download', `repusense_leads_${new Date().toISOString().slice(0, 10)}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    return (
        <ProspectosContext.Provider
            value={{
                leads,
                isLoading,
                saveLeadToProspects,
                updateLeadStatus,
                refreshLeads,
                exportToCsv,
            }}
        >
            {children}
        </ProspectosContext.Provider>
    );
};

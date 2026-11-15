import { createContext, useContext, useState, type ReactNode } from 'react';
import { ALL_MOCK_LEADS } from '../utils/mockData';
import { type Lead } from '../utils/mockData';

interface LeadsContextType {
    leads: Lead[];
    saveLeadToProspects: (id: string) => void;
    updateLeadStatus: (id: string, newStatus: Lead['status']) => void;
}

const ProspectosContext = createContext<LeadsContextType | undefined>(undefined);

export const LeadsProvider = ({ children }: { children: ReactNode }) => {
    const [leads, setLeads] = useState<Lead[]>(ALL_MOCK_LEADS);

    // Acción 1: Pasar un lead en frío a "Mis prospectos"
    const saveLeadToProspects = (id: string) => {
        setLeads((prevLeads) =>
            prevLeads.map((lead) =>
                lead.id === id
                    ? { ...lead, isSaved: true, status: 'Nuevo', lastActivity: 'Guardado hoy' }
                    : lead
            )
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
    };

    return (
        <ProspectosContext.Provider value={{ leads, saveLeadToProspects, updateLeadStatus }}>
            {children}
        </ProspectosContext.Provider>
    );
};

// Hook personalizado para consumir el contexto fácilmente
export const useLeads = () => {
    const context = useContext(ProspectosContext);
    if (!context) {
        throw new Error('useLeads debe usarse dentro de un LeadsProvider');
    }
    return context;
};
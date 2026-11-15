import { createContext, useContext } from 'react';
import { type Lead } from '../utils/mockData';

export interface LeadsContextType {
    leads: Lead[];
    saveLeadToProspects: (id: string) => void;
    updateLeadStatus: (id: string, newStatus: Lead['status']) => void;
}

// 1. Creamos y exportamos el contexto aquí
export const ProspectosContext = createContext<LeadsContextType | undefined>(undefined);

// 2. Exportamos el hook personalizado
export const useLeads = () => {
    const context = useContext(ProspectosContext);
    if (!context) {
        throw new Error('useLeads debe usarse dentro de un LeadsProvider');
    }
    return context;
};
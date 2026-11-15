import { Info, ArrowUpRight, ArrowDownRight } from 'lucide-react';

interface StatCardProps {
    title: string;
    value: string | number;
    trendValue?: string; // Opcional, ej: "+4"
    trendText?: string;  // Opcional, ej: "vs. last week"
    isPositive?: boolean; // Opcional, para saber si la flecha va arriba (verde) o abajo (rojo)
}

export const Card = ({
    title,
    value,
    trendValue,
    trendText,
    isPositive = true
}: StatCardProps) => {
    return (

        <div className="bg-white border border-gray-100 rounded-xl p-5 h-full shadow-sm hover:shadow-md transition-shadow">

            <div className="flex justify-between items-start mb-4">
                <h3 className="text-gray-600 text-sm font-medium">{title}</h3>
                <button className="text-gray-400 hover:text-gray-600 transition-colors">
                    <Info size={16} />
                </button>
            </div>

            <div>
                <p className="text-4xl font-bold text-gray-900 mb-4">{value}</p>

                {/* Renderizado condicional: Solo mostramos esta sección si existe 'trendValue' */}
                {trendValue && (
                    <div className="flex items-center text-xs">
                        <span className={`flex items-center font-semibold ${isPositive ? 'text-brand' : 'text-red-500'}`}>
                            {isPositive ? <ArrowUpRight size={15} className="mr-1 text-principal" /> : <ArrowDownRight size={14} className="mr-1" />}
                            {trendValue}
                        </span>
                        {trendText && (
                            <span className="text-content-muted ml-1.5">{trendText}</span>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};
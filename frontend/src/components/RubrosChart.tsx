import { Info } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { useLeads } from '../hooks/useLeads';// 1. Importamos nuestro contexto global

interface RubroData {
    name: string;
    value: number;
}

export const RubrosChart = () => {
    // Consumimos los leads en tiempo real desde el estado global
    const { leads } = useLeads();

    // Agrupamos los leads por su propiedad 'category' y contamos cuántos hay de cada uno
    const conteoPorRubro = leads.reduce((acc, lead) => {
        const categoria = lead.category || 'Otros';
        acc[categoria] = (acc[categoria] || 0) + 1;
        return acc;
    }, {} as Record<string, number>);

    // Transformamos el objeto agrupado al formato exacto que espera Recharts ({ name, value })
    // Además se ordena de mayor a menor para que las barras más altas salgan primero
    const dynamicData: RubroData[] = Object.entries(conteoPorRubro)
        .map(([name, value]) => ({ name, value }))
        .sort((a, b) => b.value - a.value);

    return (
        <div className="bg-white border border-gray-200 rounded-xl p-5 h-full flex flex-col shadow-sm hover:shadow-md transition-shadow">

            <div className="flex justify-between items-start mb-6">
                <h3 className="text-gray-600 text-lg font-semibold">Rubros</h3>
                <button
                    className="text-gray-400 hover:text-gray-600 transition-colors cursor-pointer"
                    title="Distribución de negocios detectados por categoría"
                >
                    <Info size={16} />
                </button>
            </div>

            <div className="flex-1 w-full min-h-62">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                        data={dynamicData}
                        margin={{ top: 10, right: 10, left: -20, bottom: 5 }}
                    >
                        <XAxis
                            dataKey="name"
                            axisLine={false}
                            tickLine={false}
                            tick={{ fill: '#6B7280', fontSize: 12 }}
                            dy={10}
                        />

                        {/* allowDecimals={false} evita que el eje Y muestre números como 1.5 negocios */}
                        <YAxis
                            allowDecimals={false}
                            axisLine={false}
                            tickLine={false}
                            tick={{ fill: '#6B7280', fontSize: 12 }}
                        />

                        {/* Hover que muestra el dato al pasar el mouse */}
                        <Tooltip
                            cursor={{ fill: '#f3f4f6', radius: 10 }}
                            contentStyle={{
                                borderRadius: '8px',
                                border: 'none',
                                boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                            }}
                            formatter={(value) => [`${value} negocios`, 'Cantidad']}
                        />

                        <Bar
                            dataKey="value"
                            fill="#10b981"
                            radius={[4, 4, 0, 0]}
                            barSize={40}
                        />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};
import { Card } from '../components/Card';
import { RubrosChart } from '../components/RubrosChart';
import { PosiblesProspectos } from '../components/PosiblesProspectos';
import { useLeads } from '../context/ProspectosContext';

export const Dashboard = () => {

    const { leads } = useLeads();
    const fecha = new Date().toLocaleDateString('es-ES');

    // Total de leads en el sistema
    const totalConsultados = leads.length;

    // Leads que ya están en seguimiento activo (guardados y fuera de 'Nuevo'/'Pendiente'/'Descartado')
    const totalContactados = leads.filter(
        (lead) =>
            lead.isSaved &&
            ['Contactado', 'En Negociación', 'Cliente Cerrado'].includes(lead.status)
    ).length;

    // Suma total de todas las reseñas analizadas en los negocios
    const totalResenas = leads.reduce((acumulador, lead) => acumulador + lead.reviewsCount, 0);

    // Cálculo del rubro dominante (la categoría con mayor cantidad de leads)
    const conteoPorRubro = leads.reduce((acc, lead) => {
        acc[lead.category] = (acc[lead.category] || 0) + 1;
        return acc;
    }, {} as Record<string, number>);

    const rubroDominante = Object.entries(conteoPorRubro).sort((a, b) => b[1] - a[1])[0]?.[0] || 'Sin datos';

    // arreglo dinámico respetando las props del componente <Card />
    const dynamicStats = [
        {
            title: "Total leads consultados",
            value: totalConsultados,
            trendValue: `+${leads.filter((l) => !l.isSaved).length}`,
            trendText: "disponibles en frío",
            isPositive: true
        },
        {
            title: "Total leads contactados",
            value: totalContactados,
            trendValue: `${leads.filter((l) => l.isSaved && l.status !== 'Descartado').length}`,
            trendText: "en prospectos",
            isPositive: true
        },
        {
            title: "Total reseñas encontradas",
            value: totalResenas,
            trendValue: `~${totalConsultados > 0 ? Math.round(totalResenas / totalConsultados) : 0}`,
            trendText: "promedio por negocio",
            isPositive: true
        },
        {
            title: "Rubro dominante",
            value: rubroDominante
        }
    ];

    return (
        <>
            <div className="mb-6 flex justify-between items-end">
                <div>
                    <h1 className="text-2xl font-bold text-content-main mb-1">Estadística general</h1>
                    <p className="text-sm text-content-muted">Última actualización {fecha}</p>
                </div>
            </div>

            <div className='grid grid-cols-1 lg:grid-cols-4 gap-6'>
                <div className='lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4'>
                    {dynamicStats.map((stat, index) => (
                        <Card
                            key={index}
                            title={stat.title}
                            value={stat.value}
                            trendValue={stat.trendValue}
                            trendText={stat.trendText}
                            isPositive={stat.isPositive}
                        />
                    ))}
                </div>
                <div className="lg:col-span-2 h-85">
                    <RubrosChart />
                </div>
            </div>

            <div>
                <PosiblesProspectos />
            </div>
        </>
    );
};
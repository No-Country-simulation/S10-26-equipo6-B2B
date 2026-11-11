import './App.css'
import { Sidebar } from './components/Sidebar'
import { Navbar } from './components/Navbar';
import { Card } from './components/Card';

const mockStats = [
  { title: "Total leads consultados", value: "+200", trendValue: "+4", trendText: "vs. ultima semana", isPositive: true },
  { title: "Total leads contactados", value: "+45", trendValue: "+6", trendText: "vs. ultima semana", isPositive: true },
  { title: "Total reseñas encontradas", value: "+500", trendValue: "+6", trendText: "reseñas encontradas", isPositive: true },
  { title: "Rubro dominante", value: "Hoteles" }
];

function App() {

  return (
    <>
      <div className="flex h-screen bg-gray-50">
        <Sidebar />
        <div className='flex-1 flex flex-col min-w-0'>
          <Navbar />

          <main className="flex-1 p-8 overflow-y-auto ">
            <div className="mb-6 flex justify-between items-end">
              <div>
                <h1 className="text-2xl font-bold text-content-main mb-1">Estadística general</h1>
                <p className="text-sm text-content-muted">Última actualización 10/11/2026</p>
              </div>
            </div>
            <div className='grid grid-cols-1 lg:grid-cols-4 gap-6'>
              <div className='lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4'>
                {mockStats.map((stat, index) => (
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
              <div className="lg:col-span-2 bg-layout-surface border border-gray-200 rounded-xl p-5 flex items-center justify-center text-gray-400 h-85">
                Grafica
              </div>
            </div>

          </main>
        </div>
      </div>
    </>
  )
}

export default App

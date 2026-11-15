import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './App.css'
import { DashboardLayout } from './layouts/DashboardLayout'
import { Dashboard } from './pages/Dashboard'
import { SearchLeads } from './pages/SearchLeads'
import { MisProspectos } from './pages/MisProspectos'
import { DetalleLeads } from './pages/DetalleLeads'
import { LeadsProvider } from './context/ProspectosContext'
import { Historial } from './pages/historial'


function App() {

  return (
    <LeadsProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<DashboardLayout />}>
            <Route path='/' element={<Dashboard />} />
            <Route path='/buscar' element={<SearchLeads />} />
            <Route path='/prospectos' element={<MisProspectos />} />
            <Route path='/lead/:id' element={<DetalleLeads />} />
            <Route path='/historial' element={<Historial />} />
            <Route path='*' element={<Navigate to='/' replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </LeadsProvider>
  )
}

export default App

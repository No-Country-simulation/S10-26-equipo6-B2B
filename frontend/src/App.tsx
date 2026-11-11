import { useState } from 'react'
import './App.css'
import { Sidebar } from './components/Sidebar'
import { Navbar } from './components/Navbar';

function App() {

  return (
    <>
      <div className="flex h-screen bg-white">
        <Sidebar />
        <div className='flex-1 flex flex-col min-w-0'>
          <Navbar />

          <main className="flex-1 p-8 overflow-y-auto">
            <div className="mb-6 flex justify-between items-end">
              <div>
                <h1 className="text-2xl font-bold text-content-main mb-1">Estadística general</h1>
                <p className="text-sm text-content-muted">Última actualización 10/11/2026</p>
              </div>
            </div>

            <div className="border-4 border-dashed border-gray-200 rounded-lg h-96 flex items-center justify-center text-gray-400">
              Dashboard
            </div>
          </main>
        </div>
      </div>
    </>
  )
}

export default App

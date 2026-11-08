import { useState } from 'react'
import './App.css'

function App() {
  const [count, setCount] = useState(0)

  return (
    <>
      <div className="flex flex-col h-screen items-center justify-center bg-gray-100 gap-2">
        <h1 className="text-4xl font-bold text-green-600">
          ¡Tailwind funciona en RepuSense!
        </h1>
        <button onClick={() => setCount(count => count + 1)} className='bg-fuchsia-600 px-5 py-2.5 rounded-md text-zinc-100'>
          El count tiene un valor de {count};
        </button>
      </div>
    </>
  )
}

export default App

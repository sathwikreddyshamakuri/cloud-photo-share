import { useState } from 'react';
import reactLogo from './assets/react.svg';
import viteLogo from '/vite.svg';
// ⬇️ remove the old CSS import
// import './App.css';

function App() {
  const [count, setCount] = useState(0);

  return (
    <div className="grid min-h-screen place-items-center bg-slate-900">
      <header className="space-y-6 text-center">
        <div className="flex justify-center gap-8">
          <a href="https://vite.dev" target="_blank">
            <img src={viteLogo} className="w-24 hover:rotate-12 transition" />
          </a>
          <a href="https://react.dev" target="_blank">
            <img src={reactLogo} className="w-24 animate-spin-slow" />
          </a>
        </div>

        <h1 className="text-4xl font-bold text-emerald-400">
          Vite + React + Tailwind
        </h1>

        <button
          className="rounded bg-emerald-600 px-4 py-2 font-semibold text-white hover:bg-emerald-500"
          onClick={() => setCount(c => c + 1)}
        >
          Count is&nbsp;{count}
        </button>
      </header>
    </div>
  );
}

export default App;

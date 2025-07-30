// src/components/ThemeToggle.tsx
import { useEffect, useState } from 'react';

export default function ThemeToggle() {
  const [dark, setDark] = useState(
    () => localStorage.getItem('theme') === 'dark'
  );

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    localStorage.setItem('theme', dark ? 'dark' : 'light');
  }, [dark]);

  return (
    <button
      onClick={() => setDark(!dark)}
      className="text-xl px-2 focus:outline-none"
      title="Toggle dark mode"
    >
      {dark ? '🌙' : '☀️'}
    </button>
  );
}

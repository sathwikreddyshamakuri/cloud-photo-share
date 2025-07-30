// src/pages/Dashboard.tsx
import { useEffect, useState } from 'react';
import { useNavigate }        from 'react-router-dom';
import api                    from '../lib/api';

interface Stats {
  album_count:  number;
  photo_count:  number;
  storage_mb:   number;
}

export default function Dashboard() {
  const navigate    = useNavigate();
  const [stats, setStats] = useState<Stats | null>(null);
  const [err,   setErr]   = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get<Stats>('/users/me/stats');
        setStats(data);
      } catch (e: any) {
        if (e.response?.status === 401) {
          // Token really invalid → kick out
          localStorage.removeItem('token');
          navigate('/login', { replace: true });
        } else {
          setErr('Failed to load stats');
        }
      }
    })();
  }, [navigate]);

  if (err)    return <p className="p-8 text-red-600">{err}</p>;
  if (!stats) return <p className="p-8">Loading…</p>;

  return (
    <div className="p-8 space-y-8 max-w-md mx-auto">
      <h1 className="text-3xl font-bold text-center mb-6">Usage dashboard</h1>

      <div className="grid gap-4 sm:grid-cols-2">
        <StatCard label="Albums"  value={stats.album_count}  />
        <StatCard label="Photos"  value={stats.photo_count}  />
        <StatCard label="Storage" value={`${stats.storage_mb.toFixed(1)} MB`} />
      </div>

      <button
        onClick={() => navigate('/albums')}
        className="mt-6 rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-500 block mx-auto"
      >
        ← Back to albums
      </button>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg bg-white dark:bg-slate-700 shadow p-6 text-center">
      <p className="text-4xl font-bold mb-1">{value}</p>
      <p className="text-gray-600 dark:text-slate-300 uppercase tracking-wide text-sm">{label}</p>
    </div>
  );
}

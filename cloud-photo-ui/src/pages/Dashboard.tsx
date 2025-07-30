// cloud-photo-ui/src/pages/Dashboard.tsx
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../lib/api';

export default function Dashboard() {
  const nav = useNavigate();
  const [data,set] = useState<{albums:number;photos:number;bytes:number}|null>(null);

  useEffect(()=>{
    api.get('/stats/')
      .then(r=>set(r.data))
      .catch(()=>{ localStorage.removeItem('token'); nav('/login'); });
  },[nav]);

  if(!data) return <p className="p-8">Loading…</p>;

  return (
    <div className="p-8 max-w-md mx-auto text-center space-y-6">
      <h1 className="text-3xl font-bold mb-4">Usage</h1>
      <div className="grid grid-cols-3 gap-4">
        <Stat n={data.albums} label="Albums"/>
        <Stat n={data.photos} label="Photos"/>
        <Stat n={(data.bytes/1_048_576).toFixed(1)} label="MB"/>
      </div>
      <Link to="/albums" className="btn-flat mt-6 inline-block">← Back</Link>
    </div>
  );
}
function Stat({n,label}:{n:number|string,label:string}) {
  return (
    <div className="bg-white dark:bg-slate-700 rounded shadow p-4">
      <div className="text-2xl font-semibold">{n}</div>
      <div className="text-sm opacity-70">{label}</div>
    </div>
  );
}

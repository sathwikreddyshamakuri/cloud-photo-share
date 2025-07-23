import { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import api from '../lib/api';

export default function VerifyEmailPage() {
  const [sp] = useSearchParams();
  const token = sp.get('token') ?? '';
  const [msg, setMsg] = useState('Verifying…');

  useEffect(() => {
    api.post('/auth/verify', { token })
      .then(() => setMsg('Email verified! You can now log in.'))
      .catch(e => setMsg(e.response?.data?.detail || 'Invalid/expired link'));
  }, [token]);

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-gray-100 space-y-4">
      <h1 className="text-xl font-semibold">{msg}</h1>
      <Link to="/login" className="text-blue-600 hover:underline">Go to login</Link>
    </div>
  );
}

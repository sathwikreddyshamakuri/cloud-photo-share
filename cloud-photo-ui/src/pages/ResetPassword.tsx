import { useState } from 'react';
import type { FormEvent } from 'react';
import { useSearchParams, Link, useNavigate } from 'react-router-dom';
import api from '../lib/api';
import logo from '../assets/nuagevault-logo.png';


export default function ResetPasswordPage() {
  const [sp] = useSearchParams();
  const token = sp.get('token') ?? '';
  const navigate = useNavigate();

  const [pwd, setPwd] = useState('');
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setMsg(null);
    setErr(null);
    try {
      await api.post('/auth/reset', { token, new_password: pwd });
      setMsg('Password updated. Redirecting to login…');
      setTimeout(() => navigate('/login'), 1200);
    } catch (e: any) {
      setErr(e.response?.data?.detail || 'Failed to reset');
    }
  }

  if (!token) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p>Missing token</p>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center h-screen bg-gray-100">
      <form onSubmit={submit} className="bg-white p-6 rounded shadow-md w-80">
        <div className="flex flex-col items-center mb-6">
            <img src={logo} alt="NuageVault" className="h-12 w-auto" />
            <h2 className="text-xl font-semibold mt-2">Login to your vault</h2>
        </div>

        {msg && <p className="text-green-600 mb-2">{msg}</p>}
        {err && <p className="text-red-600 mb-2">{err}</p>}
        <label className="block mb-4">
          New password
          <input
            type="password"
            className="w-full border p-2 rounded mt-1"
            value={pwd}
            onChange={e => setPwd(e.target.value)}
            required
            minLength={6}
          />
        </label>
        <button className="w-full bg-blue-500 text-white p-2 rounded hover:bg-blue-600">
          Update
        </button>
        <p className="text-center text-sm mt-3">
          <Link to="/login" className="text-blue-600 hover:underline">Back to login</Link>
        </p>
      </form>
    </div>
  );
}

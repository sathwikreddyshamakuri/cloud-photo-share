import { useState } from 'react';
import type { FormEvent } from 'react';
import api from '../lib/api';
import logo from '../assets/nuagevault-logo.png';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setMsg(null);
    setErr(null);
    try {
      await api.post('/auth/forgot', { email });
      setMsg('If that email exists, a reset link was sent.');
    } catch (e: any) {
      setErr(e.response?.data?.detail || 'Something went wrong');
    }
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
          Email
          <input
            type="email"
            className="w-full border p-2 rounded mt-1"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
          />
        </label>
        <button className="w-full bg-blue-500 text-white p-2 rounded hover:bg-blue-600">
          Send link
        </button>
      </form>
    </div>
  );
}

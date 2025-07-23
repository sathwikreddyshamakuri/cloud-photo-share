import { useState } from 'react';
import type { FormEvent } from 'react';
import api from '../lib/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [msg, setMsg] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setMsg(null);
    await api.post('/auth/forgot', { email });
    setMsg('If that email exists, a reset link was sent.');
  }

  return (
    <div className="flex items-center justify-center h-screen bg-gray-100">
      <form onSubmit={submit} className="bg-white p-6 rounded shadow-md w-80">
        <h2 className="text-xl font-semibold mb-4">Forgot Password</h2>
        {msg && <p className="text-green-600 mb-2">{msg}</p>}
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

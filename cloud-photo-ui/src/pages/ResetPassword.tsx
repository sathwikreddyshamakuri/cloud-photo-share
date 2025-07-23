import { useState } from 'react';
import type { FormEvent } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import api from '../lib/api';

export default function ResetPasswordPage() {
  const [sp] = useSearchParams();
  const token = sp.get('token') ?? '';

  const [pwd, setPwd] = useState('');
  const [msg, setMsg] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setMsg(null);
    try {
      await api.post('/auth/reset', { token, new_password: pwd });
      setMsg('Password updated. You can now log in.');
    } catch (err: any) {
      setMsg(err.response?.data?.detail || 'Failed to reset');
    }
  }

  return (
    <div className="flex items-center justify-center h-screen bg-gray-100">
      <form onSubmit={submit} className="bg-white p-6 rounded shadow-md w-80">
        <h2 className="text-xl font-semibold mb-4">Reset Password</h2>
        {msg && <p className="mb-2">{msg}</p>}
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

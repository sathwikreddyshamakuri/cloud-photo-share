// cloud-photo-ui/src/pages/ProfilePage.tsx
import { useEffect, useState } from 'react';
import type { FormEvent, ChangeEvent } from 'react';   // ← type‑only
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';

type Me = {
  user_id: string;
  email: string;
  display_name: string;
  bio: string;
  avatar_url: string | null;
};

export default function ProfilePage() {
  const navigate = useNavigate();

  const [me,       setMe]       = useState<Me | null>(null);
  const [name,     setName]     = useState('');
  const [bio,      setBio]      = useState('');
  const [pwdCur,   setPwdCur]   = useState('');
  const [pwdNew,   setPwdNew]   = useState('');
  const [pwdMsg,   setPwdMsg]   = useState<string | null>(null);
  const [saving,   setSaving]   = useState(false);
  const [uploading,setUploading]= useState(false);

  useEffect(() => {
    api.get<Me>('/users/me')
      .then(r => {
        setMe(r.data);
        setName(r.data.display_name);
        setBio(r.data.bio);
      })
      .catch(() => {
        localStorage.removeItem('token');
        navigate('/login', { replace: true });
      });
  }, [navigate]);

  async function saveProfile(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    await api.put('/users/me', { display_name: name, bio })
      .then(() => setMe(m => m ? { ...m, display_name: name, bio } : m))
      .finally(() => setSaving(false));
  }

  async function changePwd(e: FormEvent) {
    e.preventDefault();
    setPwdMsg(null);
    await api.put('/auth/password', { current_password: pwdCur, new_password: pwdNew })
      .then(() => setPwdMsg('Password changed. Log in again next time.'))
      .catch(err => setPwdMsg(err.response?.data?.detail || 'Failed to change password'))
      .finally(() => { setPwdCur(''); setPwdNew(''); });
  }

  async function onAvatar(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const fd = new FormData();
    fd.append('file', file);
    await api.put('/users/me/avatar', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
      .then(r => setMe(m => m ? { ...m, avatar_url: r.data.avatar_url } : m))
      .finally(() => setUploading(false));
  }

  async function deleteAccount() {
    if (!confirm('This will permanently delete your account, albums and photos. Continue?')) return;
    if (prompt('Type DELETE to confirm:') !== 'DELETE') return;
    try {
      await api.delete('/users/me');
      localStorage.removeItem('token');
      window.location.replace('/signup');
    } catch (err: any) {
      alert('Delete failed: ' + (err.response?.data?.detail ?? ''));
    }
  }

  if (!me) return <p className="p-8">Loading…</p>;
  const initial = (me.display_name || me.email)[0].toUpperCase();

  return (
    <div className="p-8 max-w-xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold">Profile</h1>

      {/* avatar */}
      <section className="space-y-3">
        <div className="flex items-center space-x-4">
          {me.avatar_url
            ? <img src={me.avatar_url} alt="avatar" className="h-20 w-20 rounded-full object-cover border" />
            : <div className="h-20 w-20 rounded-full bg-gray-300 flex items-center justify-center text-xl">
                {initial}
              </div>}
          <label className="cursor-pointer text-blue-600 hover:underline">
            {uploading ? 'Uploading…' : 'Change photo'}
            <input type="file" accept="image/*" className="hidden" onChange={onAvatar} />
          </label>
        </div>
      </section>

      {/* name + bio */}
      <form onSubmit={saveProfile} className="space-y-4">
        <input className="w-full border rounded p-2"
               value={name} onChange={e => setName(e.target.value)}
               maxLength={40} required placeholder="Display name" />
        <textarea className="w-full border rounded p-2" rows={3}
                  value={bio} onChange={e => setBio(e.target.value)}
                  maxLength={200} placeholder="Bio" />
        <button disabled={saving}
                className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-500 disabled:opacity-50">
          {saving ? 'Saving…' : 'Save'}
        </button>
      </form>

      {/* password */}
      <form onSubmit={changePwd} className="space-y-4 border-t pt-6">
        <h2 className="text-lg font-semibold">Change password</h2>
        <input type="password" className="w-full border rounded p-2"
               placeholder="Current password" value={pwdCur}
               onChange={e => setPwdCur(e.target.value)} required />
        <input type="password" className="w-full border rounded p-2"
               placeholder="New password" value={pwdNew}
               onChange={e => setPwdNew(e.target.value)} minLength={6} required />
        <button className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-500">Update</button>
        {pwdMsg && <p className="text-sm mt-2">{pwdMsg}</p>}
      </form>

      {/* danger zone */}
      <div className="border-t pt-6">
        <h2 className="text-lg font-semibold text-red-600 mb-3">Danger zone</h2>
        <button onClick={deleteAccount}
                className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-500">
          Delete my account
        </button>
      </div>
    </div>
  );
}

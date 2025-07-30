// src/pages/Albums.tsx
import { useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { ClipboardDocumentIcon } from '@heroicons/react/24/solid';
import ThemeToggle from '../components/ThemeToggle';
import api from '../lib/api';

interface Album {
  album_id:   string;
  owner:      string;
  title:      string;
  created_at: number;
  cover_url?: string | null;
}

export default function AlbumsPage() {
  const navigate = useNavigate();

  const [albums,      setAlbums]     = useState<Album[]>([]);
  const [filtered,    setFiltered]   = useState<Album[]>([]);
  const [loading,     setLoading]    = useState(true);
  const [error,       setError]      = useState<string | null>(null);

  const [searchTerm,  setSearchTerm] = useState('');
  const [creating,    setCreating]   = useState(false);
  const [newTitle,    setNewTitle]   = useState('');

  const [renamingId,  setRenaming]   = useState<string | null>(null);
  const [renameTitle, setRename]     = useState('');

  /* ─── initial load ─── */
  useEffect(() => {
    if (!localStorage.getItem('token')) {
      navigate('/login', { replace: true });
      return;
    }
    fetchAlbums();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function fetchAlbums() {
    setLoading(true);
    try {
      const { data } = await api.get<{ items: Album[] }>('/albums/');
      setAlbums(data.items);
      setFiltered(data.items);
    } catch (e: any) {
      if (e.response?.status === 401) {
        localStorage.removeItem('token');
        navigate('/login', { replace: true });
      } else {
        setError('Failed to load albums');
      }
    } finally {
      setLoading(false);
    }
  }

  /* ─── search filter ─── */
  useEffect(() => {
    const term = searchTerm.trim().toLowerCase();
    setFiltered(albums.filter(a => a.title.toLowerCase().includes(term)));
  }, [searchTerm, albums]);

  /* ─── create ─── */
  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    const title = newTitle.trim();
    if (!title) return;
    try {
      const { data } = await api.post<Album>('/albums/', null, { params: { title } });
      const upd = [data, ...albums];
      setAlbums(upd);
      setFiltered(upd);
      setNewTitle('');
      setCreating(false);
      toast.success('Album created');
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Create failed');
    }
  }

  /* ─── rename ─── */
  async function handleRename(e: FormEvent) {
    e.preventDefault();
    if (!renamingId) return;
    const title = renameTitle.trim();
    if (!title) return;
    try {
      await api.put(`/albums/${renamingId}`, { title });
      const upd = albums.map(a => (a.album_id === renamingId ? { ...a, title } : a));
      setAlbums(upd);
      setFiltered(upd);
      setRenaming(null);
      toast.success('Renamed');
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Rename failed');
    }
  }

  /* ─── delete ─── */
  async function handleDelete(id: string) {
    if (!confirm('Delete this album?')) return;
    try {
      await api.delete(`/albums/${id}`);
      const upd = albums.filter(a => a.album_id !== id);
      setAlbums(upd);
      setFiltered(upd);
      toast.success('Album deleted');
    } catch {
      toast.error('Delete failed');
    }
  }

  /* ─── render guards ─── */
  if (loading) return <p className="p-8">Loading albums…</p>;
  if (error)   return <p className="p-8 text-red-600">{error}</p>;

  /* ─── UI ─── */
  return (
    <div className="p-8 bg-slate-50 dark:bg-slate-800 min-h-screen text-slate-900 dark:text-slate-100">
      {/* top bar */}
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center space-x-2">
          <ThemeToggle />
          <button
            onClick={() => navigate('/profile')}
            className="rounded bg-gray-200 px-3 py-1 hover:bg-gray-300"
          >
            Profile
          </button>
          <button
            onClick={() => { localStorage.removeItem('token'); navigate('/login', { replace:true }); }}
            className="rounded bg-red-500 px-3 py-1 text-white hover:bg-red-400"
          >
            Logout
          </button>
        </div>

        <h1 className="text-3xl font-bold text-center">Your Albums</h1>

        <button
          onClick={() => setCreating(true)}
          className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-500"
        >
          + New Album
        </button>
      </div>

      {/* search */}
      <input
        type="text"
        placeholder="Search albums…"
        value={searchTerm}
        onChange={e => setSearchTerm(e.target.value)}
        className="mb-6 rounded border p-2 w-full max-w-sm"
      />

      {/* grid */}
      <div className="grid gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        {filtered.map(alb => (
          <div key={alb.album_id} className="relative bg-white rounded shadow hover:shadow-lg transition">
            <Link to={`/albums/${alb.album_id}`}>
              {alb.cover_url ? (
                <img src={alb.cover_url} alt={alb.title}
                     className="w-full aspect-[4/3] object-cover rounded-t" />
              ) : (
                <div className="w-full aspect-[4/3] bg-gray-200 flex items-center justify-center rounded-t">
                  <span className="text-gray-500">No preview</span>
                </div>
              )}
              <div className="p-4">
                <h2 className="text-lg font-medium">{alb.title}</h2>
              </div>
            </Link>

            {/* action buttons */}
            <div className="absolute top-2 right-2 flex space-x-1">
              <button
                onClick={() => {
                  const url = `${window.location.origin}/albums/${alb.album_id}`;
                  navigator.clipboard.writeText(url)
                    .then(() => toast.success('Link copied!'));
                }}
                className="rounded bg-white p-1 text-blue-600 hover:bg-blue-100"
                title="Copy share link"
              >
                <ClipboardDocumentIcon className="h-4 w-4" />
              </button>

              <button
                onClick={() => { setRenaming(alb.album_id); setRename(alb.title); }}
                className="rounded bg-white p-1 text-gray-600 hover:bg-gray-100"
              >
                ✏️
              </button>
              <button
                onClick={() => handleDelete(alb.album_id)}
                className="rounded bg-white p-1 text-red-600 hover:bg-red-100"
              >
                🗑️
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* ── create modal ── */}
      {creating && (
        <div
          className="fixed inset-0 flex items-center justify-center bg-black/50"
          onClick={() => setCreating(false)}
        >
          <form
            onSubmit={handleCreate}
            className="bg-white p-6 rounded shadow-lg w-80"
            onClick={e => e.stopPropagation()}
          >
            <h2 className="text-xl font-semibold mb-4">New Album</h2>
            <input
              value={newTitle}
              onChange={e => setNewTitle(e.target.value)}
              placeholder="Album title"
              required
              className="w-full border p-2 rounded mb-4"
            />
            <div className="flex justify-end space-x-2">
              <button type="button" onClick={() => setCreating(false)} className="px-4 py-2">Cancel</button>
              <button type="submit" className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-500">Create</button>
            </div>
          </form>
        </div>
      )}

      {/* ── rename modal ── */}
      {renamingId && (
        <div
          className="fixed inset-0 flex items-center justify-center bg-black/50"
          onClick={() => setRenaming(null)}
        >
          <form
            onSubmit={handleRename}
            className="bg-white p-6 rounded shadow-lg w-80"
            onClick={e => e.stopPropagation()}
          >
            <h2 className="text-xl font-semibold mb-4">Rename Album</h2>
            <input
              value={renameTitle}
              onChange={e => setRename(e.target.value)}
              required
              className="w-full border p-2 rounded mb-4"
            />
            <div className="flex justify-end space-x-2">
              <button type="button" onClick={() => setRenaming(null)} className="px-4 py-2">Cancel</button>
              <button type="submit" className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-500">Save</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

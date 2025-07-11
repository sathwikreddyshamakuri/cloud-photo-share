import { useEffect, useState, FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../lib/api';

interface Album {
  owner:      string;
  album_id:   string;
  title:      string;
  created_at: number;
  cover_url:  string | null;
}

export default function Albums() {
  const navigate = useNavigate();

  // app state
  const [albums, setAlbums]         = useState<Album[]>([]);
  const [filtered, setFiltered]     = useState<Album[]>([]);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  // create-album modal
  const [creating, setCreating]       = useState(false);
  const [newTitle, setNewTitle]       = useState('');

  // rename modal
  const [renaming, setRenaming]       = useState(false);
  const [renameId, setRenameId]       = useState('');
  const [renameTitle, setRenameTitle] = useState('');

  // on mount: fetch & auth
  useEffect(() => {
    if (!localStorage.getItem('jwt')) {
      navigate('/login');
      return;
    }
    fetchAlbums();
  }, [navigate]);

  // fetch albums from API
  function fetchAlbums() {
    setLoading(true);
    api.get('/albums/')
      .then(res => {
        const data = (res.data as any).albums as Album[];
        setAlbums(data);
        setFiltered(data);
      })
      .catch(() => setError('Failed to load albums'))
      .finally(() => setLoading(false));
  }

  // filter when searchTerm or albums change
  useEffect(() => {
    const term = searchTerm.toLowerCase();
    setFiltered(
      albums.filter(a => a.title.toLowerCase().includes(term))
    );
  }, [searchTerm, albums]);

  // logout
  const handleLogout = () => {
    localStorage.removeItem('jwt');
    navigate('/login');
  };

  // create
  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const res = await api.post<Album>('/albums/', { title: newTitle });
      setAlbums([res.data, ...albums]);
      setNewTitle('');
      setCreating(false);
    } catch {
      alert('Could not create album');
    }
  };

  // rename
  const startRename = (alb: Album) => {
    setRenameId(alb.album_id);
    setRenameTitle(alb.title);
    setRenaming(true);
  };
  const handleRename = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api.put(`/albums/${renameId}`, { title: renameTitle });
      setAlbums(albums.map(a =>
        a.album_id === renameId ? { ...a, title: renameTitle } : a
      ));
      setRenaming(false);
    } catch {
      alert('Rename failed');
    }
  };

  // delete
  const handleDelete = async (id: string) => {
    if (!confirm('Delete this album?')) return;
    try {
      await api.delete(`/albums/${id}`);
      setAlbums(albums.filter(a => a.album_id !== id));
    } catch {
      alert('Delete failed');
    }
  };

  if (loading) return <p className="p-8">Loading albums…</p>;
  if (error)   return <p className="p-8 text-red-600">{error}</p>;

  return (
    <div className="p-8 bg-slate-50 min-h-screen">
      {/* header */}
      <div className="mb-6 flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-4 sm:space-y-0">
        <div className="flex items-center space-x-4">
          <button
            onClick={handleLogout}
            className="rounded bg-red-500 px-3 py-1 text-white hover:bg-red-400"
          >
            Logout
          </button>
          <h1 className="text-3xl font-bold">Your Albums</h1>
        </div>
        <div className="flex items-center space-x-2">
          <input
            type="text"
            placeholder="Search albums..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="rounded border p-2"
          />
          <button
            onClick={() => setCreating(true)}
            className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-500"
          >
            + New Album
          </button>
        </div>
      </div>

      {/* album grid or “no results” */}
      {filtered.length === 0 ? (
        <p>No albums found.</p>
      ) : (
        <div className="grid gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          {filtered.map(alb => (
            <div key={alb.album_id} className="relative">
              <Link
                to={`/album/${alb.album_id}`}
                className="block overflow-hidden rounded-lg bg-white shadow hover:shadow-lg transition"
              >
                {alb.cover_url ? (
                  <img
                    src={alb.cover_url}
                    alt={alb.title}
                    className="h-48 w-full object-cover"
                  />
                ) : (
                  <div className="flex h-48 w-full items-center justify-center bg-gray-200">
                    <span className="text-gray-500">No preview</span>
                  </div>
                )}
                <div className="p-4">
                  <h2 className="text-lg font-medium">{alb.title}</h2>
                </div>
              </Link>
              {/* edit/delete */}
              <div className="absolute top-2 right-2 flex space-x-1">
                <button
                  onClick={() => startRename(alb)}
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
      )}

      {/* Create Modal */}
      {creating && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
          onClick={() => setCreating(false)}
        >
          <form
            onSubmit={handleCreate}
            className="bg-white rounded-lg p-6 shadow-lg w-80"
            onClick={e => e.stopPropagation()}
          >
            <h2 className="mb-4 text-xl font-semibold">New Album</h2>
            <input
              type="text"
              className="w-full rounded border p-2"
              placeholder="Album title"
              value={newTitle}
              onChange={e => setNewTitle(e.target.value)}
              required
            />
            <div className="mt-4 flex justify-end space-x-2">
              <button
                type="button"
                onClick={() => setCreating(false)}
                className="px-4 py-2"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-500"
              >
                Create
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Rename Modal */}
      {renaming && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
          onClick={() => setRenaming(false)}
        >
          <form
            onSubmit={handleRename}
            className="bg-white rounded-lg p-6 shadow-lg w-80"
            onClick={e => e.stopPropagation()}
          >
            <h2 className="mb-4 text-xl font-semibold">Rename Album</h2>
            <input
              type="text"
              className="w-full rounded border p-2"
              value={renameTitle}
              onChange={e => setRenameTitle(e.target.value)}
              required
            />
            <div className="mt-4 flex justify-end space-x-2">
              <button
                type="button"
                onClick={() => setRenaming(false)}
                className="px-4 py-2"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-500"
              >
                Save
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

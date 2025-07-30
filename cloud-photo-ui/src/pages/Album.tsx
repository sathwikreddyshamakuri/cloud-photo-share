import { useState, useEffect, useRef, type ChangeEvent, type FormEvent } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import api from '../lib/api';

interface PhotoMeta {
  photo_id: string;
  album_id: string;
  s3_key:   string;
  uploaded_at: number;
  url: string;
}

export default function AlbumPage() {
  const { id: albumId } = useParams<{ id: string }>();
  const navigate        = useNavigate();

  const [photos,   setPhotos]   = useState<PhotoMeta[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState<string | null>(null);

  const [file,      setFile]      = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress,  setProgress]  = useState(0);

  const [selected,  setSelected]  = useState<Set<string>>(new Set());
  const lastClicked = useRef<number | null>(null);

  /* ── load photos ───────────────────────────────────────────── */
  useEffect(() => { fetchPhotos(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [albumId]);

  async function fetchPhotos() {
    setLoading(true);
    try {
      const { data } = await api.get<{ items: PhotoMeta[] }>('/photos/', {
        params: { album_id: albumId, limit: 500 },
      });
      setPhotos(data.items);
    } catch (e: any) {
      if (e.response?.status === 401) {
        localStorage.removeItem('token'); navigate('/login');
      } else { setError('Failed to load photos'); }
    } finally { setLoading(false); }
  }

  /* ── upload ─────────────────────────────────────────────────── */
  const onSelect = (e: ChangeEvent<HTMLInputElement>) =>
    setFile(e.target.files?.[0] ?? null);

  async function onUpload(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setUploading(true); setProgress(0);

    const data = new FormData(); data.append('file', file);
    try {
      await api.post('/photos/', data, {
        params:  { album_id: albumId },
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: ev =>
          setProgress(Math.round((ev.loaded / (ev.total ?? 1)) * 100)),
      });
      setFile(null); fetchPhotos(); toast.success('Uploaded');
    } catch { toast.error('Upload failed'); }
    finally { setUploading(false); }
  }

  /* ── delete (single or batch) ───────────────────────────────── */
  async function deletePhoto(photo_id: string) {
    if (!confirm('Delete this photo?')) return;
    try { await api.delete(`/photos/${photo_id}`); setPhotos(p => p.filter(ph => ph.photo_id !== photo_id)); }
    catch { toast.error('Delete failed'); }
  }

  async function deleteSelected() {
    if (selected.size === 0) return;
    if (!confirm(`Delete ${selected.size} photo(s)?`)) return;
    for (const id of selected) await api.delete(`/photos/${id}`).catch(() => {});
    setPhotos(p => p.filter(ph => !selected.has(ph.photo_id)));
    setSelected(new Set()); toast.success('Deleted');
  }

  /* ── selection helpers ─────────────────────────────────────── */
  function toggleSelect(idx: number, multiKey: boolean, shiftKey: boolean) {
    setSelected(sel => {
      const newSel = new Set(sel);
      const id = photos[idx].photo_id;

      if (shiftKey && lastClicked.current !== null) {
        // range selection
        const [a, b] = [idx, lastClicked.current].sort((x, y) => x - y);
        for (let i = a; i <= b; i++) newSel.add(photos[i].photo_id);
      } else if (multiKey) {
        newSel.has(id) ? newSel.delete(id) : newSel.add(id);
      } else {
        newSel.clear(); newSel.add(id);
      }
      lastClicked.current = idx;
      return newSel;
    });
  }

  /* ── guards ─────────────────────────────────────────────────── */
  if (loading) return <p className="p-8">Loading photos…</p>;
  if (error)   return <p className="p-8 text-red-600">{error}</p>;

  /* ── UI ─────────────────────────────────────────────────────── */
  return (
    <div className="p-8 bg-slate-50 min-h-screen">
      <h1 className="mb-4 text-2xl font-bold">Album Photos</h1>
      <Link to="/albums" className="text-blue-500 hover:underline">← Back to albums</Link>

      {/* upload */}
      <form onSubmit={onUpload} className="my-4 flex items-center space-x-2">
        <input type="file" onChange={onSelect} className="border rounded p-1" />
        <button type="submit"
                disabled={!file || uploading}
                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-500 disabled:opacity-50">
          {uploading ? 'Uploading…' : 'Upload'}
        </button>
        {uploading && <span className="ml-4">{progress}%</span>}
      </form>

      {/* bulk toolbar */}
      {selected.size > 0 && (
        <div className="mb-4 flex items-center space-x-3">
          <span>{selected.size} selected</span>
          <button onClick={deleteSelected}
                  className="bg-red-600 text-white px-3 py-1 rounded hover:bg-red-500">
            Delete selected
          </button>
        </div>
      )}

      {/* grid */}
      <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        {photos.map((p, i) => {
          const checked = selected.has(p.photo_id);
          return (
            <label key={p.photo_id}
                   className={`relative block cursor-pointer ${checked ? 'ring-4 ring-blue-500' : ''}`}
                   onClick={e =>
                     toggleSelect(i,
                       e.metaKey || e.ctrlKey,
                       e.shiftKey)}
            >
              <img src={p.url} alt=""
                   className="h-48 w-full object-cover rounded-lg shadow" />
              {/* checkbox */}
              <input type="checkbox"
                     checked={checked}
                     readOnly
                     className="absolute top-2 left-2 h-4 w-4 accent-blue-500" />
              {/* single delete button */}
              <button type="button"
                      onClick={e => { e.stopPropagation(); deletePhoto(p.photo_id); }}
                      className="absolute top-2 right-2 bg-white p-1 rounded text-red-600 hover:bg-red-100">
                🗑️
              </button>
            </label>
          );
        })}
      </div>
    </div>
  );
}

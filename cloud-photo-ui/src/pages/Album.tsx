// src/pages/Album.tsx
import {
  useState, useEffect,
  type ChangeEvent, type FormEvent
} from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import * as JSZip           from 'jszip';            // ← namespace import = no esModuleInterop needed
import { saveAs }           from 'file-saver';
import toast                from 'react-hot-toast';
import api                  from '../lib/api';

interface PhotoMeta {
  photo_id: string;
  album_id: string;
  s3_key:   string;
  uploaded_at: number;
  url: string;
}

/* keyboard helper -------------------------------------------------------- */
function useKey(key: string, fn: () => void, deps: any[]) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === key) fn(); };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}
/* ----------------------------------------------------------------------- */
export default function AlbumPage() {
  const { id: albumId } = useParams<{ id: string }>();
  const navigate        = useNavigate();

  const [photos,  setPhotos]  = useState<PhotoMeta[]>([]);
  const [selected, setSel]    = useState<Set<string>>(new Set());
  const [lastIdx,  setLast]   = useState<number | null>(null);

  const [file, setFile]       = useState<File | null>(null);
  const [uploading, setUp]    = useState(false);
  const [progress,  setProg]  = useState(0);
  const [loading,   setLoad]  = useState(true);
  const [error,     setErr]   = useState<string | null>(null);

  /* ------------ load photos --------------- */
  useEffect(() => {
    if (!localStorage.getItem('token')) { navigate('/login'); return; }
    fetchPhotos();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [albumId]);

  async function fetchPhotos() {
    setLoad(true);
    try {
      const { data } = await api.get<{ items: PhotoMeta[] }>('/photos/', {
        params: { album_id: albumId, limit: 500 },
      });
      setPhotos(data.items);
    } catch (e: any) {
      setErr('Failed to load photos');
      if (e.response?.status === 401) {
        localStorage.removeItem('token'); navigate('/login');
      }
    } finally { setLoad(false); }
  }

  /* ------------ upload -------------------- */
  const onSelect = (e: ChangeEvent<HTMLInputElement>) =>
    setFile(e.target.files?.[0] ?? null);

  async function onUpload(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    const data = new FormData();
    data.append('file', file);
    setUp(true); setProg(0);
    try {
      await api.post('/photos/', data, {
        params:  { album_id: albumId },
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: ev =>
          setProg(Math.round((ev.loaded / (ev.total ?? 1)) * 100)),
      });
      setFile(null); fetchPhotos(); toast.success('Uploaded');
    } catch { toast.error('Upload failed'); }
    finally { setUp(false); }
  }

  /* ------------ delete single / batch ----- */
  async function deleteOne(id: string) {
    if (!confirm('Delete this photo?')) return;
    await api.delete(`/photos/${id}`);
    setPhotos(p => p.filter(ph => ph.photo_id !== id));
    setSel(s => { s.delete(id); return new Set(s); });
  }

  async function deleteSelected() {
    if (selected.size === 0) return;
    if (!confirm(`Delete ${selected.size} photos?`)) return;
    await Promise.all([...selected].map(id => api.delete(`/photos/${id}`)));
    setPhotos(p => p.filter(ph => !selected.has(ph.photo_id)));
    setSel(new Set());
    toast.success('Deleted');
  }

  /* ------------ download ------------------ */
  async function downloadSelected() {
    if (selected.size === 0) return;
    const zip = new JSZip();
    toast.loading('Preparing download…', { id: 'dl' });

    await Promise.all(
      photos.filter(p => selected.has(p.photo_id)).map(async p => {
        const res  = await fetch(p.url);
        const blob = await res.blob();
        const ext  = p.url.split('.').pop() || 'jpg';
        zip.file(`${p.photo_id}.${ext}`, blob);
      })
    );

    const blob = await zip.generateAsync({ type: 'blob' });
    saveAs(blob, `album-${albumId}.zip`);
    toast.success('Downloaded', { id: 'dl' });
  }

  /* ------------ selection  ---------------- */
  function toggle(idx: number, e: React.MouseEvent) {
    setSel(sel => {
      const s = new Set(sel);
      const id = photos[idx].photo_id;

      if (e.shiftKey && lastIdx !== null) {
        const [a, b] = [lastIdx, idx].sort((x, y) => x - y);
        for (let i = a; i <= b; i++) s.add(photos[i].photo_id);
      } else if (e.metaKey || e.ctrlKey) {
        s.has(id) ? s.delete(id) : s.add(id);
      } else { s.clear(); s.add(id); }
      setLast(idx);
      return s;
    });
  }
  useKey('Escape', () => setSel(new Set()), [selected]);

  /* ------------ ui guards ----------------- */
  if (loading) return <p className="p-8">Loading photos…</p>;
  if (error)   return <p className="p-8 text-red-600">{error}</p>;

  return (
    <div className="p-8 space-y-6 bg-slate-50 dark:bg-slate-800 min-h-screen">

      <div className="flex items-center justify-between flex-wrap gap-3">
        <Link to="/albums" className="text-blue-600 hover:underline">← All albums</Link>

        {selected.size > 0 && (
          <div className="flex gap-2">
            <button
              onClick={deleteSelected}
              className="rounded bg-red-600 px-3 py-1 text-white hover:bg-red-500"
            >
              Delete {selected.size}
            </button>
            <button
              onClick={downloadSelected}
              className="rounded bg-indigo-600 px-3 py-1 text-white hover:bg-indigo-500"
            >
              Download {selected.size}
            </button>
          </div>
        )}
      </div>

      {/* upload */}
      <form onSubmit={onUpload} className="flex items-center gap-2">
        <input type="file" onChange={onSelect}
               className="rounded border p-1 dark:bg-slate-700 dark:border-slate-600"/>
        <button
          type="submit"
          disabled={!file || uploading}
          className="rounded bg-green-600 px-4 py-1 text-white hover:bg-green-500 disabled:opacity-50"
        >
          {uploading ? `Uploading ${progress}%` : 'Upload'}
        </button>
      </form>

      {/* grid */}
      <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        {photos.map((p, idx) => (
          <div key={p.photo_id} className="relative group">
            <img
              src={p.url}
              alt=""
              className={
                `w-full aspect-[4/3] object-cover rounded-lg shadow cursor-pointer
                 ${selected.has(p.photo_id) ? 'ring-4 ring-blue-500' : ''}`
              }
              onClick={(e) => toggle(idx, e)}
            />
            <button
              onClick={() => deleteOne(p.photo_id)}
              className="absolute top-1 right-1 bg-white dark:bg-slate-800 p-1 rounded text-red-600 hover:bg-red-100 dark:hover:bg-slate-700 opacity-0 group-hover:opacity-100 transition"
              title="Delete photo"
            >
              🗑️
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

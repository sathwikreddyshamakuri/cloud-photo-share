// cloud-photo-ui/src/pages/Album.tsx
import { useState, useEffect, useCallback, useRef } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useSwipeable } from 'react-swipeable';
import api from '../lib/api';

interface PhotoMeta {
  photo_id: string;
  album_id: string;
  s3_key: string;
  uploaded_at: number;
  url: string;
}

/* ─────────── custom hook (hoisted) ─────────── */
function useAutoFocus(enabled: boolean) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (enabled) ref.current?.focus();
  }, [enabled]);
  return ref;
}

export default function AlbumPage() {
  const { id: albumId } = useParams<{ id: string }>();
  const navigate = useNavigate();

  /* state */
  const [photos, setPhotos] = useState<PhotoMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const [isOpen, setIsOpen] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const overlayRef = useAutoFocus(isOpen);               // ⬅ gets focus for Arrow keys

  /* helpers for light‑box nav */
  const prev = useCallback(
    () => setCurrentIndex(i => (i === 0 ? photos.length - 1 : i - 1)),
    [photos.length],
  );
  const next = useCallback(
    () => setCurrentIndex(i => (i === photos.length - 1 ? 0 : i + 1)),
    [photos.length],
  );

  /* finger‑tracking for “raw” touch events */
  const touchX = useRef<number | null>(null);

  /* react‑swipeable (covers touch‑pads & mouse‑drag) */
  const swipeHandlers = useSwipeable({
    onSwipedLeft: next,
    onSwipedRight: prev,
    trackMouse: true,
  });

  /* initial load */
  useEffect(() => {
    if (!localStorage.getItem('token')) {
      navigate('/login');
      return;
    }
    fetchPhotos();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [albumId]);

  async function fetchPhotos() {
    setLoading(true);
    try {
      const r = await api.get<{ items: PhotoMeta[] }>('/photos/', {
        params: { album_id: albumId, limit: 100 },
      });
      setPhotos(r.data.items);
    } catch (e: any) {
      setError('Failed to load photos');
      if (e.response?.status === 401) {
        localStorage.removeItem('token');
        navigate('/login');
      }
    } finally {
      setLoading(false);
    }
  }

  /* upload */
  const onSelect = (e: ChangeEvent<HTMLInputElement>) =>
    setFile(e.target.files?.[0] ?? null);

  async function onUpload(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    const data = new FormData();
    data.append('file', file);

    setUploading(true);
    setProgress(0);
    try {
      await api.post('/photos/', data, {
        params: { album_id: albumId },
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: ev =>
          setProgress(Math.round((ev.loaded / (ev.total ?? 1)) * 100)),
      });
      setFile(null);
      fetchPhotos();
    } catch {
      alert('Upload failed');
    } finally {
      setUploading(false);
    }
  }

  /* delete */
  async function deletePhoto(photo_id: string) {
    if (!confirm('Delete this photo?')) return;
    try {
      await api.delete(`/photos/${photo_id}`);
      fetchPhotos();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Delete failed');
      if (e.response?.status === 401) {
        localStorage.removeItem('token');
        navigate('/login');
      }
    }
  }

  /* UI */
  if (loading) return <p className="p-8">Loading photos…</p>;
  if (error) return <p className="p-8 text-red-600">{error}</p>;

  return (
    <div className="p-8 bg-slate-50 min-h-screen">
      <h1 className="mb-4 text-2xl font-bold">Album Photos</h1>
      <Link to="/albums" className="text-blue-500 hover:underline">
        ← Back to albums
      </Link>

      {/* upload */}
      <form onSubmit={onUpload} className="my-4 flex items-center space-x-2">
        <input type="file" onChange={onSelect} className="border rounded p-1" />
        <button
          type="submit"
          disabled={!file || uploading}
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-500 disabled:opacity-50"
        >
          {uploading ? 'Uploading…' : 'Upload'}
        </button>
        {uploading && <span className="ml-4">{progress}%</span>}
      </form>

      {/* grid */}
      <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        {photos.map((p, i) => (
          <div key={p.photo_id} className="relative">
            <img
              src={p.url}
              alt=""
              className="h-48 w-full object-cover rounded-lg shadow cursor-pointer"
              onClick={() => {
                setCurrentIndex(i);
                setIsOpen(true);
              }}
            />
            <button
              onClick={() => deletePhoto(p.photo_id)}
              className="absolute top-1 right-1 bg-white text-red-600 rounded p-1 hover:bg-red-100"
            >
              🗑️
            </button>
          </div>
        ))}
      </div>

      {/* light‑box */}
      {isOpen && (
        <div
          ref={overlayRef}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 outline-none"
          onClick={() => setIsOpen(false)}
          tabIndex={0}
          onKeyDown={e => {
            if (e.key === 'ArrowLeft') prev();
            if (e.key === 'ArrowRight') next();
            if (e.key === 'Escape') setIsOpen(false);
          }}
          onTouchStart={e => (touchX.current = e.touches[0].clientX)}
          onTouchEnd={e => {
            const dx = e.changedTouches[0].clientX - (touchX.current ?? 0);
            if (Math.abs(dx) > 40) (dx > 0 ? prev() : next());
          }}
          {...swipeHandlers}
        >
          <img
            src={photos[currentIndex].url}
            alt={`Photo ${currentIndex + 1}`}
            className="max-h-full max-w-full rounded-lg shadow-lg"
            onClick={e => e.stopPropagation()} /* don’t close on img tap */
          />
        </div>
      )}
    </div>
  );
}

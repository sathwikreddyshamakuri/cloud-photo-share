import { useEffect, useState, ChangeEvent, FormEvent } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../lib/api';

interface PhotoMeta {
  photo_id: string;
  album_id: string;
  s3_key: string;
  uploaded_at: number;
  url: string;
}

export default function Album() {
  const { id: albumId } = useParams<{ id: string }>();
  const [photos, setPhotos]     = useState<PhotoMeta[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState('');
  const [isOpen, setIsOpen]     = useState(false);
  const [index, setIndex]       = useState(0);

  // Upload state
  const [file, setFile]         = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress]   = useState(0);

  // Fetch photos
  const fetchPhotos = () => {
    setLoading(true);
    api.get('/photos/')
      .then(res => {
        const all = (res.data as any).photos as PhotoMeta[];
        setPhotos(all.filter(p => p.album_id === albumId));
      })
      .catch(() => setError('Failed to load photos'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchPhotos();
  }, [albumId]);

  // File selection
  const onSelect = (e: ChangeEvent<HTMLInputElement>) => {
    setFile(e.target.files?.[0] ?? null);
  };

  // Upload handler
  const onUpload = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) return;

    const data = new FormData();
    data.append('album_id', albumId!);
    data.append('file', file);

    setUploading(true);
    setProgress(0);

    try {
      await api.post('/photos/', data, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: ev => {
          setProgress(Math.round((ev.loaded / ev.total!) * 100));
        },
      });
      setFile(null);
      fetchPhotos();
    } catch {
      alert('Upload failed');
    } finally {
      setUploading(false);
    }
  };

  if (loading) return <p className="p-8">Loading photos…</p>;
  if (error)   return <p className="p-8 text-red-600">{error}</p>;

  return (
    <div className="p-8 bg-slate-50 min-h-screen">
      <h1 className="mb-6 text-2xl font-bold">Album Photos</h1>
      <Link to="/albums" className="text-blue-500 hover:underline">
        ← Back to albums
      </Link>

      {/* Upload form */}
      <form onSubmit={onUpload} className="my-4 flex items-center space-x-2">
        <input
          type="file"
          onChange={onSelect}
          className="rounded border p-1"
        />
        <button
          type="submit"
          disabled={!file || uploading}
          className="rounded bg-green-600 px-4 py-2 text-white hover:bg-green-500 disabled:opacity-50"
        >
          {uploading ? 'Uploading…' : 'Upload'}
        </button>
        {uploading && (
          <span className="ml-4">{progress}%</span>
        )}
      </form>

      {/* Photo grid */}
      <div className="mt-4 grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        {photos.map((photo, i) => (
          <div key={photo.photo_id} className="relative">
            <img
              src={photo.url}
              alt={`Photo ${i + 1}`}
              className="h-48 w-full object-cover cursor-pointer rounded-lg shadow"
              onClick={() => {
                setIndex(i);
                setIsOpen(true);
              }}
            />
            {/* 🗑️ delete button */}
            <button
              onClick={async () => {
                if (!confirm('Delete this photo?')) return;
                try {
                  await api.delete(`/photos/${photo.photo_id}`);
                  setPhotos(photos.filter(p => p.photo_id !== photo.photo_id));
                } catch {
                  alert('Delete failed');
                }
              }}
              className="absolute top-1 right-1 rounded bg-white p-1 text-red-600 hover:bg-red-100"
            >
              🗑️
            </button>
          </div>
        ))}
      </div>

      {/* Full-screen overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-80 p-4"
          onClick={() => setIsOpen(false)}
        >
          <img
            src={photos[index].url}
            alt={`Photo ${index + 1}`}
            className="max-h-full max-w-full rounded-lg shadow-lg"
          />
        </div>
      )}
    </div>
  );
}

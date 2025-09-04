// cloud-photo-ui/src/pages/Album.tsx
import {
  useState, useEffect, useCallback, useRef,
  type ChangeEvent, type FormEvent
} from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import api from '../lib/api';
import { putToS3 } from '../lib/s3';

interface PhotoMeta {
  photo_id: string;
  album_id: string;
  s3_key: string;
  uploaded_at: number;
  url: string;
}

/* focus helper so the light-box receives Arrow-key events */
function useAutoFocus(enabled: boolean) {
  const r = useRef<HTMLDivElement>(null);
  useEffect(() => { if (enabled) r.current?.focus(); }, [enabled]);
  return r;
}

export default function AlbumPage() {
  const { id: albumId } = useParams<{ id: string }>();
  const nav             = useNavigate();

  /*  state  */
  const [photos,   setPhotos]   = useState<PhotoMeta[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState<string|null>(null);

  const [file,     setFile]     = useState<File|null>(null);
  const [uploading,setUploading]= useState(false);
  const [prog,     setProg]     = useState(0);

  /* light-box */
  const [open,     setOpen]     = useState(false);
  const [idx,      setIdx]      = useState(0);
  const lbRef = useAutoFocus(open);

  /* selection mode */
  const [selecting, setSelecting]    = useState(false);
  const [selected , setSelected]     = useState<Set<string>>(new Set());

  /*  helpers  */
  const prev = () => setIdx(i => (i ? i - 1 : photos.length - 1));
  const next = () => setIdx(i => (i === photos.length - 1 ? 0 : i + 1));

  const fetchPhotos = useCallback(async () => {
    if (!albumId) return;
    setLoading(true);
    try {
      const { data } = await api.get<{items: PhotoMeta[]}>('/photos/', {
        params: { album_id: albumId, limit: 500 }
      });
      setPhotos(data.items);
      setError(null);
    } catch (e:any) {
      if (e.response?.status === 401) {
        localStorage.removeItem('token');
        window.dispatchEvent(new Event('token-change'));
        nav('/login', { replace: true });
      } else {
        setError(e?.response?.data?.detail || 'Failed to load photos');
      }
    } finally { setLoading(false); }
  }, [albumId, nav]);

  /* load once */
  useEffect(() => {
    fetchPhotos();
  }, [fetchPhotos]);

  /* upload via presigned PUT */
  const onSelect = (e:ChangeEvent<HTMLInputElement>) =>
    setFile(e.target.files?.[0] ?? null);

  async function onUpload(e:FormEvent) {
    e.preventDefault();
    if (!file || !albumId) return;

    // Always take the exact MIME you'll send to S3
    const mime = file.type || 'application/octet-stream';

    setUploading(true);
    setProg(0);

    try {
      // 1) Ask API for a presigned PUT URL
      const { data } = await api.post('/photos/', {
        album_id: albumId,
        filename: file.name,
        mime
      });

      const putUrl: string | undefined = data?.put_url;
      const photoId: string | undefined = data?.photo_id;
      const finalizeRequired: boolean | undefined = data?.finalize_required;

      if (!putUrl) {
        throw new Error('Server did not return a presigned URL');
      }

      // 2) Upload bytes directly to S3 (no cookies)
      await putToS3(putUrl, file, mime, ev => {
        if (ev?.total) setProg(Math.round((ev.loaded / ev.total) * 100));
      });

      // 3) (optional) finalize if your API requires it
      if (finalizeRequired && photoId) {
        try { await api.post(`/photos/${photoId}/finalize`); } catch { /* ignore */ }
      }

      setFile(null);
      await fetchPhotos();
      toast.success('Uploaded');
    } catch (err:any) {
      const msg = err?.response?.data?.detail || err?.message || 'Upload failed';
      toast.error(msg);
    } finally {
      setUploading(false);
    }
  }

  /*  delete one / many  */
  async function deleteOne(id:string) {
    if (!confirm('Delete this photo?')) return;
    await api.delete(`/photos/${id}/`); // keep trailing slash for consistency
    setPhotos(p=>p.filter(x=>x.photo_id!==id));
  }

  async function deleteSelected() {
    if (!selected.size) return;
    if (!confirm(`Delete ${selected.size} selected photo(s)?`)) return;
    await Promise.all([...selected].map(id => api.delete(`/photos/${id}/`).catch(()=>{})));
    setPhotos(p=>p.filter(x=>!selected.has(x.photo_id)));
    setSelected(new Set()); setSelecting(false);
    toast.success('Deleted');
  }

  /*  download  */
  function downloadSelected() {
    selected.forEach(id=>{
      const p = photos.find(ph=>ph.photo_id===id); if (!p) return;
      const link = document.createElement('a');
      link.href = p.url; link.download = `photo-${id}.jpg`;
      document.body.appendChild(link); link.click(); link.remove();
    });
    toast.success('Downloading…');
  }

  /*  guard  */
  if (loading) return <p className="p-8">Loading…</p>;
  if (error)   return <p className="p-8 text-red-600">{error}</p>;

  /* UI  */
  return (
    <div className="p-8 bg-slate-50 dark:bg-slate-800 min-h-screen">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Album</h1>
        <div className="space-x-2">
          {!selecting && (
            <button
              onClick={() => setSelecting(true)}
              className="rounded bg-indigo-600 px-3 py-1 text-white hover:bg-indigo-500"
            >Select</button>
          )}
          {selecting && (
            <>
              <button
                onClick={downloadSelected}
                className="rounded bg-green-600 px-3 py-1 text-white disabled:opacity-40"
                disabled={!selected.size}
              >Download</button>
              <button
                onClick={deleteSelected}
                className="rounded bg-red-600 px-3 py-1 text-white disabled:opacity-40"
                disabled={!selected.size}
              >Delete</button>
              <button
                onClick={() => { setSelecting(false); setSelected(new Set()); }}
                className="rounded bg-gray-200 px-3 py-1 hover:bg-gray-300"
              >Done</button>
            </>
          )}
          <Link to="/albums" className="ml-2 text-blue-600 hover:underline">← Back</Link>
        </div>
      </div>

      {/* upload */}
      <form onSubmit={onUpload} className="my-4 flex items-center space-x-2">
        <input type="file" onChange={onSelect} className="border rounded p-1"/>
        <button
          type="submit" disabled={!file||uploading}
          className="bg-green-600 text-white rounded px-4 py-1 disabled:opacity-40"
        >{uploading?`Uploading ${prog}%`:'Upload'}</button>
      </form>

      {/* grid */}
      <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        {photos.map((p,i)=>(
          <div key={p.photo_id} className="relative group">
            {selecting && (
              <input
                type="checkbox"
                checked={selected.has(p.photo_id)}
                onChange={(e)=>{
                  const s=new Set(selected);
                  e.target.checked? s.add(p.photo_id):s.delete(p.photo_id);
                  setSelected(s);
                }}
                className="absolute z-10 m-2 h-5 w-5"
              />
            )}
            <img
              src={p.url}
              alt=""
              loading="lazy"
              className="h-48 w-full object-cover rounded-lg shadow cursor-pointer"
              onClick={()=>{
                if(selecting){
                  const s=new Set(selected);
                  s.has(p.photo_id)?s.delete(p.photo_id):s.add(p.photo_id);
                  setSelected(s);
                }else{
                  setIdx(i); setOpen(true);
                }
              }}
            />
            {!selecting && (
              <button
                onClick={()=>deleteOne(p.photo_id)}
                className="absolute top-1 right-1 bg-white text-red-600 rounded p-1 opacity-0 group-hover:opacity-100"
              >🗑️</button>
            )}
          </div>
        ))}
      </div>

      {/* light-box */}
      {open && (
        <div
          ref={lbRef}
          className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 outline-none"
          tabIndex={0}
          onKeyDown={e=>{
            if(e.key==='ArrowLeft') prev();
            if(e.key==='ArrowRight') next();
            if(e.key==='Escape') setOpen(false);
          }}
          onClick={()=>setOpen(false)}
        >
          <img
            src={photos[idx].url}
            className="max-h-full max-w-full rounded-lg"
            onClick={e=>e.stopPropagation()}
          />
        </div>
      )}
    </div>
  );
}

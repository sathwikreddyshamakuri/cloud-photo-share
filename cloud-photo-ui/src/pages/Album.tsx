import { useState, useEffect, useCallback, useRef } from 'react'   // 
import type { ChangeEvent, FormEvent } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useSwipeable } from 'react-swipeable'
import api from '../lib/api'

interface PhotoMeta {
  photo_id:    string
  album_id:    string
  s3_key:      string
  uploaded_at: number
  url:         string
}

export default function AlbumPage() {
  const { id: albumId } = useParams<{ id: string }>()
  const navigate        = useNavigate()

  /* state */
  const [photos,  setPhotos]  = useState<PhotoMeta[]>([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)

  const [file,      setFile]      = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [progress,  setProgress]  = useState(0)

  const [isOpen,       setIsOpen]       = useState(false)
  const [currentIndex, setCurrentIndex] = useState(0)

  /* helpers reused by keys + swipe */
  const prev = useCallback(
    () => setCurrentIndex(i => (i === 0 ? photos.length - 1 : i - 1)),
    [photos.length],
  )
  const next = useCallback(
    () => setCurrentIndex(i => (i === photos.length - 1 ? 0 : i + 1)),
    [photos.length],
  )

  /* track finger x‑coord for vanilla touch events */
  const touchX = useRef<number | null>(null)

  /* swipe‑library hook for desktop touchpads / mobile */
  const swipeHandlers = useSwipeable({
    onSwipedLeft : next,
    onSwipedRight: prev,
    trackMouse   : true,
  })

  /* load photos once album id available */
  useEffect(() => {
    if (!localStorage.getItem('token')) { navigate('/login'); return }
    fetchPhotos()
  }, [albumId])

  async function fetchPhotos() {
    setLoading(true)
    try {
      const r = await api.get<{ items: PhotoMeta[] }>('/photos/', {
        params: { album_id: albumId, limit: 100 },
      })
      setPhotos(r.data.items)
    } catch (e: any) {
      setError('Failed to load photos')
      if (e.response?.status === 401) {
        localStorage.removeItem('token')
        navigate('/login')
      }
    } finally {
      setLoading(false)
    }
  }

  /* …  upload / delete code unchanged … */

  /* ─────── UI ─────── */
  if (loading) return <p className="p-8">Loading photos…</p>
  if (error)   return <p className="p-8 text-red-600">{error}</p>

  return (
    <div className="p-8 bg-slate-50 min-h-screen">
      <h1 className="mb-4 text-2xl font-bold">Album Photos</h1>
      <Link to="/albums" className="text-blue-500 hover:underline">← Back to albums</Link>

      {/* upload form – unchanged */}
      {/* photo grid – unchanged */}

      {/* light‑box */}
      {isOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
          onClick={() => setIsOpen(false)}
          tabIndex={0}                                // receive key events
          onKeyDown={e => {
            if (e.key === 'ArrowLeft')  prev()
            if (e.key === 'ArrowRight') next()
            if (e.key === 'Escape')     setIsOpen(false)
          }}
          onTouchStart={e => (touchX.current = e.touches[0].clientX)}
          onTouchEnd={e => {
            const dx = e.changedTouches[0].clientX - (touchX.current ?? 0)
            if (Math.abs(dx) > 40) (dx > 0 ? prev() : next())
          }}
          {...swipeHandlers}                          // 📱/🖱️ swipe
        >
          <img
            src={photos[currentIndex].url}
            alt={`Photo ${currentIndex + 1}`}
            className="max-h-full max-w-full rounded-lg shadow-lg"
            onClick={e => e.stopPropagation()}        // don’t close on image tap
          />
        </div>
      )}
    </div>
  )
}

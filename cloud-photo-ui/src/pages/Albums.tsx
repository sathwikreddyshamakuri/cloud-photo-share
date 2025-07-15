// File: src/pages/Albums.tsx

import { useState, useEffect } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import api from '../lib/api'

interface Album {
  album_id: string
  owner: string
  title: string
  created_at: number
  cover_url?: string | null
}

export default function AlbumsPage() {
  const [albums, setAlbums] = useState<Album[]>([])
  const [filtered, setFiltered] = useState<Album[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [creating, setCreating] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [renamingId, setRenamingId] = useState<string | null>(null)
  const [renameTitle, setRenameTitle] = useState('')

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      window.location.href = '/login'
      return
    }
    fetchAlbums()
  }, [])

  async function fetchAlbums() {
    setLoading(true)
    setError(null)
    try {
      const res = await api.get<Album[]>('/albums/')
      setAlbums(res.data)
      setFiltered(res.data)
    } catch (e: any) {
      console.error('Failed to load albums', e)
      if (e.response?.status === 401) {
        localStorage.removeItem('token')
        window.location.href = '/login'
        return
      }
      setError('Failed to load albums')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setFiltered(
      albums.filter(a =>
        a.title.toLowerCase().includes(searchTerm.toLowerCase())
      )
    )
  }, [searchTerm, albums])

  function handleLogout() {
    localStorage.removeItem('token')
    window.location.href = '/login'
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault()
    try {
      const res = await api.post<Album>('/albums/', { title: newTitle })
      const updated = [res.data, ...albums]
      setAlbums(updated)
      setFiltered(updated)
      setNewTitle('')
      setCreating(false)
    } catch (e) {
      console.error('Create failed', e)
      alert('Could not create album')
    }
  }

  function startRename(alb: Album) {
    setRenamingId(alb.album_id)
    setRenameTitle(alb.title)
  }

  async function handleRename(e: FormEvent) {
    e.preventDefault()
    if (!renamingId) return
    try {
      await api.put<Album>(`/albums/${renamingId}`, { title: renameTitle })
      const updated = albums.map(a =>
        a.album_id === renamingId ? { ...a, title: renameTitle } : a
      )
      setAlbums(updated)
      setFiltered(updated)
      setRenamingId(null)
    } catch (e) {
      console.error('Rename failed', e)
      alert('Rename failed')
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this album?')) return
    try {
      await api.delete(`/albums/${id}`)
      const updated = albums.filter(a => a.album_id !== id)
      setAlbums(updated)
      setFiltered(updated)
    } catch (e) {
      console.error('Delete failed', e)
      alert('Delete failed')
    }
  }

  if (loading) return <p className="p-8">Loading albums…</p>
  if (error)   return <p className="p-8 text-red-600">{error}</p>

  return (
    <div className="p-8 bg-slate-50 min-h-screen">
      <div className="flex justify-between items-center mb-6">
        <button
          onClick={handleLogout}
          className="rounded bg-red-500 px-3 py-1 text-white hover:bg-red-400"
        >
          Logout
        </button>
        <h1 className="text-3xl font-bold">Your Albums</h1>
        <button
          onClick={() => setCreating(true)}
          className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-500"
        >
          + New Album
        </button>
      </div>

      <div className="mb-4">
        <input
          type="text"
          placeholder="Search albums..."
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          className="rounded border p-2 w-full max-w-sm"
        />
      </div>

      <div className="grid gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        {filtered.map(alb => (
          <div
            key={alb.album_id}
            className="relative bg-white rounded shadow hover:shadow-lg transition"
          >
            <Link to={`/albums/${alb.album_id}`}>
              {alb.cover_url ? (
                <img
                  src={alb.cover_url}
                  alt={alb.title}
                  className="h-48 w-full object-cover rounded-t"
                />
              ) : (
                <div className="h-48 w-full bg-gray-200 flex items-center justify-center rounded-t">
                  <span className="text-gray-500">No preview</span>
                </div>
              )}
              <div className="p-4">
                <h2 className="text-lg font-medium">{alb.title}</h2>
              </div>
            </Link>
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

      {/* Create Modal */}
      {creating && (
        <div
          className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50"
          onClick={() => setCreating(false)}
        >
          <form
            onSubmit={handleCreate}
            className="bg-white p-6 rounded shadow-lg w-80"
            onClick={e => e.stopPropagation()}
          >
            <h2 className="text-xl font-semibold mb-4">New Album</h2>
            <input
              type="text"
              value={newTitle}
              onChange={e => setNewTitle(e.target.value)}
              placeholder="Album title"
              required
              className="w-full border p-2 rounded mb-4"
            />
            <div className="flex justify-end space-x-2">
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
      {renamingId && (
        <div
          className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50"
          onClick={() => setRenamingId(null)}
        >
          <form
            onSubmit={handleRename}
            className="bg-white p-6 rounded shadow-lg w-80"
            onClick={e => e.stopPropagation()}
          >
            <h2 className="text-xl font-semibold mb-4">Rename Album</h2>
            <input
              type="text"
              value={renameTitle}
              onChange={e => setRenameTitle(e.target.value)}
              required
              className="w-full border p-2 rounded mb-4"
            />
            <div className="flex justify-end space-x-2">
              <button
                type="button"
                onClick={() => setRenamingId(null)}
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
  )
}

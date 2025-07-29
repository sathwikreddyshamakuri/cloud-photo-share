// cloud-photo-ui/src/pages/ProfilePage.tsx
import { useEffect, useState } from 'react'
import type { FormEvent, ChangeEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import Swal  from 'sweetalert2'

import api from '../lib/api'

type Me = {
  user_id: string
  email: string
  display_name: string
  bio: string
  avatar_url: string | null
}

export default function ProfilePage() {
  const navigate = useNavigate()

  const [me, setMe]         = useState<Me | null>(null)
  const [name, setName]     = useState('')
  const [bio,  setBio]      = useState('')

  const [pwdCur, setPwdCur] = useState('')
  const [pwdNew, setPwdNew] = useState('')
  const [pwdMsg, setPwdMsg] = useState<string | null>(null)

  const [saving,    setSaving]    = useState(false)
  const [dirty,     setDirty]     = useState(false)
  const [uploading, setUploading] = useState(false)

  /* load current user */
  useEffect(() => {
    api.get<Me>('/users/me')
      .then(r => {
        setMe(r.data)
        setName(r.data.display_name)
        setBio(r.data.bio)
      })
      .catch(() => { localStorage.removeItem('token'); navigate('/login', { replace:true }) })
  }, [navigate])

  /* save profile */
  async function saveProfile(e: FormEvent) {
    e.preventDefault()
    if (!dirty) return
    setSaving(true)
    try {
      await api.put('/users/me', { display_name: name, bio })
      setMe(m => m ? { ...m, display_name: name, bio } : m)
      setDirty(false)
      toast.success('Profile saved')
    } finally { setSaving(false) }
  }

  /* change pwd */
  async function changePwd(e: FormEvent) {
    e.preventDefault()
    setPwdMsg(null)
    try {
      await api.put('/users/me/password', { current_password: pwdCur, new_password: pwdNew })
      setPwdCur(''); setPwdNew('')
      toast.success('Password updated')
    } catch (err: any) {
      setPwdMsg(err.response?.data?.detail || 'Failed')
    }
  }

  /* avatar */
  async function onAvatar(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]; if (!f) return
    setUploading(true)
    const fd = new FormData(); fd.append('file', f)
    try {
      const r = await api.put('/users/me/avatar', fd, { headers:{ 'Content-Type':'multipart/form-data' } })
      setMe(m => m ? { ...m, avatar_url: r.data.avatar_url } : m)
      toast.success('Avatar updated')
    } finally { setUploading(false) }
  }

  /* delete account */
  async function deleteAccount() {
    const { isConfirmed } = await Swal.fire({
      title:'Delete account?',
      text:'All albums & photos will be removed.',
      icon:'warning', showCancelButton:true, confirmButtonColor:'#d33'
    })
    if (!isConfirmed) return
    try {
      await api.delete('/users/me')
      toast.success('Account deleted')
      localStorage.removeItem('token')
      window.location.replace('/signup')
    } catch (e:any) {
      Swal.fire('Error', e.response?.data?.detail || 'Delete failed', 'error')
    }
  }

  /* ui ----------------------------------------------------------- */
  if (!me) return <p className="p-8">Loading…</p>
  const initial = (me.display_name || me.email)[0].toUpperCase()

  return (
    <div className="p-8 max-w-xl mx-auto space-y-8">
      {/* header */}
      <div className="flex items-center mb-4">
        <button onClick={() => navigate(-1)} className="mr-3 text-blue-600 hover:underline">← Back</button>
        <h1 className="text-2xl font-bold">Profile</h1>
      </div>

      {/* avatar */}
      <section className="space-y-3">
        <div className="flex items-center space-x-4">
          {me.avatar_url
            ? <img src={me.avatar_url} alt="avatar" className="h-20 w-20 rounded-full object-cover border" />
            : <div className="h-20 w-20 rounded-full bg-gray-300 flex items-center justify-center text-xl">{initial}</div>
          }
          <label className="cursor-pointer text-blue-600 hover:underline">
            {uploading ? 'Uploading…' : 'Change photo'}
            <input type="file" className="hidden" onChange={onAvatar} accept="image/*" />
          </label>
        </div>
      </section>

      {/* name + bio */}
      <form onSubmit={saveProfile} className="space-y-4">
        <div>
          <label className="block text-sm mb-1">Display name</label>
          <input className="w-full border rounded p-2" value={name}
                 onChange={e => { setName(e.target.value); setDirty(true) }}
                 required maxLength={40} />
        </div>
        <div>
          <label className="block text-sm mb-1">Bio</label>
          <textarea className="w-full border rounded p-2" value={bio}
                    onChange={e => { setBio(e.target.value); setDirty(true) }}
                    rows={3} maxLength={200} />
        </div>
        <button type="submit" disabled={saving || !dirty}
                className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-500 disabled:opacity-50">
          {saving ? 'Saving…' : 'Save'}
        </button>
      </form>

      {/* password */}
      <form onSubmit={changePwd} className="space-y-4 border-t pt-6">
        <h2 className="text-lg font-semibold">Change password</h2>
        <input type="password" placeholder="Current password" className="w-full border rounded p-2"
               value={pwdCur} onChange={e => setPwdCur(e.target.value)} required />
        <input type="password" placeholder="New password" className="w-full border rounded p-2"
               value={pwdNew} onChange={e => setPwdNew(e.target.value)} required minLength={6} />
        <button className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-500">Update password</button>
        {pwdMsg && <p className="text-sm mt-2">{pwdMsg}</p>}
      </form>

      {/* delete */}
      <div className="border-t pt-6 sm:text-right">
        <button onClick={deleteAccount}
                className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-500">
          Delete my account
        </button>
      </div>
    </div>
  )
}

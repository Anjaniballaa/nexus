import { useState, useEffect } from 'react'
import { useAuth } from '../store/auth'
import api from '../utils/api'
import toast from 'react-hot-toast'

export default function ProfilePage() {
  const { user, refreshUser } = useAuth()
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  const [phone, setPhone] = useState(user?.phone || '')
  const [saving, setSaving] = useState(false)
  const [disconnecting, setDisconnecting] = useState(null)

  const connections = user?.github_connections || []

  const saveProfile = async () => {
    setSaving(true)
    try {
      await api.patch('/me', { phone })
      await refreshUser()
      toast.success('Profile saved')
    } catch {
      toast.error('Save failed')
    } finally { setSaving(false) }
  }

  const disconnect = async (connId) => {
    setDisconnecting(connId)
    try {
      await api.delete(`/github/connections/${connId}`)
      await refreshUser()
      toast.success('GitHub account disconnected')
    } catch {
      toast.error('Disconnect failed')
    } finally { setDisconnecting(null) }
  }

  return (
    <div style={{ padding: '24px 32px', maxWidth: 620, margin: '0 auto' }}>
      <h1 style={{ color: '#e2e8f0', fontSize: 22, fontWeight: 700, margin: '0 0 24px' }}>Profile</h1>

      {/* Avatar + basic info */}
      <div style={{
        background: '#0a0f1e', border: '1px solid #1e293b', borderRadius: 12,
        padding: 24, marginBottom: 16,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
          {user?.photo_url ? (
            <img src={user.photo_url} alt="" style={{ width: 64, height: 64, borderRadius: '50%', border: '2px solid #1e293b' }} />
          ) : (
            <div style={{
              width: 64, height: 64, borderRadius: '50%',
              background: 'linear-gradient(135deg, #312e81, #1e1b4b)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#818cf8', fontSize: 24, fontWeight: 700,
            }}>
              {user?.name?.[0]?.toUpperCase()}
            </div>
          )}
          <div>
            <div style={{ color: '#e2e8f0', fontSize: 16, fontWeight: 700 }}>{user?.name}</div>
            <div style={{ color: '#475569', fontSize: 13, marginTop: 2 }}>{user?.email}</div>
            <div style={{ color: '#334155', fontSize: 11, marginTop: 2 }}>
              Signed in with {user?.auth_provider === 'google' ? 'Google' : 'GitHub'}
            </div>
          </div>
        </div>

        {/* Phone */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ color: '#64748b', fontSize: 11, fontWeight: 600, letterSpacing: '0.05em', display: 'block', marginBottom: 6 }}>
            PHONE (optional)
          </label>
          <input
            value={phone}
            onChange={e => setPhone(e.target.value)}
            placeholder="+1 234 567 8900"
            style={{
              width: '100%', padding: '10px 12px', borderRadius: 8,
              background: '#0f172a', border: '1px solid #1e293b', color: '#e2e8f0',
              fontSize: 13, outline: 'none', boxSizing: 'border-box',
            }}
            onFocus={e => e.target.style.borderColor = '#6366f1'}
            onBlur={e => e.target.style.borderColor = '#1e293b'}
          />
        </div>

        <button
          onClick={saveProfile}
          disabled={saving}
          style={{
            padding: '9px 20px', borderRadius: 8,
            background: 'rgba(99,102,241,0.15)', border: '1px solid #6366f1',
            color: '#818cf8', fontSize: 13, fontWeight: 600, cursor: 'pointer',
          }}
        >
          {saving ? 'Saving...' : 'Save changes'}
        </button>
      </div>

      {/* GitHub connections */}
      <div style={{ background: '#0a0f1e', border: '1px solid #1e293b', borderRadius: 12, padding: 24 }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16,
        }}>
          <div style={{ color: '#94a3b8', fontSize: 12, fontWeight: 600, letterSpacing: '0.05em' }}>
            CONNECTED GITHUB ACCOUNTS
          </div>
          <a
            onClick={() => {
  window.location.href = `${apiUrl}/auth/github/connect`
}}
            style={{
              padding: '6px 14px', borderRadius: 7, border: '1px solid #334155',
              background: '#161b22', color: '#e2e8f0',
              textDecoration: 'none', fontSize: 12, fontWeight: 500,
            }}
          >
            + Connect account
          </a>
        </div>

        {connections.length === 0 ? (
          <div style={{ color: '#475569', fontSize: 13, padding: '12px 0' }}>
            No GitHub accounts connected. Connect one to analyse private repos and commit changes.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {connections.map(c => (
              <div key={c.id} style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '10px 12px', borderRadius: 8, background: '#0f172a', border: '1px solid #1e293b',
              }}>
                {c.avatar_url ? (
                  <img src={c.avatar_url} alt="" style={{ width: 28, height: 28, borderRadius: '50%' }} />
                ) : (
                  <div style={{ width: 28, height: 28, borderRadius: '50%', background: '#1e293b', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b', fontSize: 12 }}>
                    GH
                  </div>
                )}
                <div style={{ flex: 1 }}>
                  <div style={{ color: '#e2e8f0', fontSize: 13, fontWeight: 500 }}>{c.github_username}</div>
                  <div style={{ color: '#475569', fontSize: 11 }}>
                    Connected {new Date(c.connected_at).toLocaleDateString()}
                    {c.is_primary && <span style={{ marginLeft: 6, color: '#6366f1', fontWeight: 600 }}>Primary</span>}
                  </div>
                </div>
                <button
                  onClick={() => disconnect(c.id)}
                  disabled={disconnecting === c.id}
                  style={{
                    padding: '5px 12px', borderRadius: 6, border: '1px solid #334155',
                    background: 'transparent', color: '#ef4444', fontSize: 11, cursor: 'pointer',
                  }}
                >
                  {disconnecting === c.id ? '...' : 'Disconnect'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
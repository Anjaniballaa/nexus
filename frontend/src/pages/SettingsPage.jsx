import { useState } from 'react'
import { useAuth } from '../store/auth'
import api from '../utils/api'
import toast from 'react-hot-toast'

function Toggle({ value, onChange }) {
  return (
    <div
      onClick={() => onChange(!value)}
      style={{
        width: 44, height: 24, borderRadius: 12, cursor: 'pointer',
        background: value ? '#6366f1' : '#1e293b',
        border: `1px solid ${value ? '#818cf8' : '#334155'}`,
        position: 'relative', transition: 'all 0.2s', flexShrink: 0,
      }}
    >
      <div style={{
        width: 16, height: 16, borderRadius: '50%', background: '#fff',
        position: 'absolute', top: 3,
        left: value ? 23 : 3,
        transition: 'left 0.2s',
      }} />
    </div>
  )
}

export default function SettingsPage() {
  const { user, refreshUser } = useAuth()
  const [emailReports, setEmailReports] = useState(user?.email_reports ?? true)
  const [riskThreshold, setRiskThreshold] = useState(user?.risk_threshold || 'MEDIUM')
  const [saving, setSaving] = useState(false)

  const save = async () => {
  setSaving(true)
  try{
    await api.patch('/me/settings', { email_reports: emailReports, risk_threshold: riskThreshold })
    document.documentElement.setAttribute('data-theme', theme)
    await refreshUser()
    toast.success('Settings saved')
  } catch {
    toast.error('Save failed')
  } finally { setSaving(false) }
}

  return (
    <div style={{ padding: '24px 32px', maxWidth: 560, margin: '0 auto' }}>
      <h1 style={{ color: '#e2e8f0', fontSize: 22, fontWeight: 700, margin: '0 0 24px' }}>Settings</h1>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

        {/* Email reports */}
        <div style={{ background: '#0a0f1e', border: '1px solid #1e293b', borderRadius: 10, padding: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ color: '#e2e8f0', fontSize: 14, fontWeight: 500 }}>Email reports</div>
              <div style={{ color: '#475569', fontSize: 12, marginTop: 2 }}>
                Send HTML report to <span style={{ color: '#6366f1' }}>{user?.email}</span> after each analysis
              </div>
            </div>
            <Toggle value={emailReports} onChange={setEmailReports} />
          </div>
        </div>

        {/* Risk threshold */}
        <div style={{ background: '#0a0f1e', border: '1px solid #1e293b', borderRadius: 10, padding: 20 }}>
          <div style={{ color: '#e2e8f0', fontSize: 14, fontWeight: 500, marginBottom: 4 }}>
            Risk threshold for alerts
          </div>
          <div style={{ color: '#475569', fontSize: 12, marginBottom: 12 }}>
            Only flag changes at or above this risk level for your attention
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {['LOW', 'MEDIUM', 'HIGH'].map(r => (
              <button
                key={r}
                onClick={() => setRiskThreshold(r)}
                style={{
                  padding: '7px 16px', borderRadius: 7, cursor: 'pointer', fontSize: 12, fontWeight: 600,
                  border: `1px solid ${riskThreshold === r ? (r === 'LOW' ? '#10b981' : r === 'MEDIUM' ? '#f59e0b' : '#ef4444') : '#1e293b'}`,
                  background: riskThreshold === r
                    ? (r === 'LOW' ? 'rgba(16,185,129,0.12)' : r === 'MEDIUM' ? 'rgba(245,158,11,0.12)' : 'rgba(239,68,68,0.12)')
                    : 'transparent',
                  color: riskThreshold === r
                    ? (r === 'LOW' ? '#10b981' : r === 'MEDIUM' ? '#f59e0b' : '#ef4444')
                    : '#475569',
                }}
              >{r}</button>
            ))}
          </div>
        </div>

        {/* Danger zone */}
        <div style={{ background: '#0a0f1e', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 10, padding: 20 }}>
          <div style={{ color: '#ef4444', fontSize: 12, fontWeight: 600, letterSpacing: '0.05em', marginBottom: 8 }}>
            ACCOUNT
          </div>
          <div style={{ color: '#475569', fontSize: 12, marginBottom: 12 }}>
            Analysis data is stored on our servers. Your API keys are never stored.
          </div>
          <div style={{ color: '#334155', fontSize: 11 }}>
            To delete your account and all data, contact support.
          </div>
        </div>

        <button
          onClick={save}
          disabled={saving}
          style={{
            padding: '11px 24px', borderRadius: 9,
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            color: '#fff', border: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer',
            alignSelf: 'flex-start',
          }}
        >
          {saving ? 'Saving...' : 'Save settings'}
        </button>
      </div>
    </div>
  )
}
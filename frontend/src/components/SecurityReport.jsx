const SEV_COLORS = {
  HIGH:   { bg: 'rgba(239,68,68,0.12)',  color: '#ef4444' },
  MEDIUM: { bg: 'rgba(245,158,11,0.12)', color: '#f59e0b' },
  LOW:    { bg: 'rgba(99,102,241,0.12)', color: '#818cf8' },
}

export default function SecurityReport({ findings }) {
  if (!findings || findings.length === 0) {
    return (
      <div style={{
        background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)',
        borderRadius: 10, padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <span style={{ color: '#10b981', fontSize: 16 }}>✓</span>
        <span style={{ color: '#10b981', fontSize: 13 }}>No security issues found</span>
      </div>
    )
  }

  const high = findings.filter(f => f.severity === 'HIGH').length
  const med  = findings.filter(f => f.severity === 'MEDIUM').length

  return (
    <div style={{ background: '#0a0f1e', border: '1px solid #1e293b', borderRadius: 10, overflow: 'hidden' }}>
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #1e293b',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <span style={{ color: '#ef4444', fontSize: 14 }}>⚠</span>
        <span style={{ color: '#94a3b8', fontSize: 12, fontWeight: 600 }}>SECURITY FINDINGS</span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
          {high > 0 && <span style={{ ...SEV_COLORS.HIGH, padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700 }}>{high} HIGH</span>}
          {med > 0 && <span style={{ ...SEV_COLORS.MEDIUM, padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700 }}>{med} MED</span>}
        </div>
      </div>

      {findings.map((f, i) => {
        const sev = SEV_COLORS[f.severity] || SEV_COLORS.LOW
        return (
          <div key={i} style={{
            padding: '12px 16px', borderBottom: i < findings.length - 1 ? '1px solid #0f172a' : 'none',
          }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
              <span style={{
                ...sev, padding: '2px 8px', borderRadius: 4, fontSize: 10,
                fontWeight: 700, flexShrink: 0, marginTop: 1,
              }}>{f.severity}</span>
              <div>
                <div style={{ color: '#e2e8f0', fontSize: 13, fontWeight: 500 }}>{f.message}</div>
                {f.file_path && (
                  <div style={{ color: '#475569', fontSize: 11, marginTop: 3 }}>
                    {f.file_path}{f.line ? `:${f.line}` : ''}
                    {f.test_id && <span style={{ marginLeft: 6, color: '#334155' }}>[{f.test_id}]</span>}
                  </div>
                )}
                {f.fix_suggestion && (
                  <div style={{ color: '#6366f1', fontSize: 11, marginTop: 3 }}>
                    Suggestion: {f.fix_suggestion}
                  </div>
                )}
              </div>
            </div>
          </div>
        )
      })}

      {high > 0 && (
        <div style={{
          padding: '10px 16px', background: 'rgba(239,68,68,0.06)',
          borderTop: '1px solid rgba(239,68,68,0.2)',
          color: '#ef4444', fontSize: 11, display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <span>⚠</span>
          HIGH severity issues block PR merge. Fix manually before committing.
        </div>
      )}
    </div>
  )
}
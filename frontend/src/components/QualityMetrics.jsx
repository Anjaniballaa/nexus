export default function QualityMetrics({ analysis }) {
  if (!analysis) return null

  const {
    complexity_before, complexity_after,
    estimated_hours_saved, confidence_score,
    minimality_score, tests_passed, test_count,
    total_issues, security_issues,
  } = analysis

  const cards = [
    complexity_before != null && {
      label: 'Complexity',
      before: typeof complexity_before === 'number' ? complexity_before.toFixed(1) : complexity_before,
      after: complexity_after != null ? (typeof complexity_after === 'number' ? complexity_after.toFixed(1) : complexity_after) : null,
      improved: complexity_after != null && complexity_after < complexity_before,
    },
    estimated_hours_saved != null && {
      label: 'Time Saved',
      // estimated_hours_saved is already a number like 2.5
      value: `~${typeof estimated_hours_saved === 'number' ? estimated_hours_saved.toFixed(1) : estimated_hours_saved}h`,
      sub: 'manual effort avoided',
      color: '#10b981',
    },
    confidence_score != null && {
      label: 'Confidence',
      // FIX: confidence_score is already 0-100 integer from backend — do NOT multiply by 100
      value: `${Math.round(Number(confidence_score))}%`,
      sub: 'modernization accuracy',
      color: '#6366f1',
    },
    minimality_score != null && {
      label: 'Minimality',
      // FIX: minimality_score is already 0-100 from diff engine — do NOT multiply by 100
      value: `${Math.round(Number(minimality_score))}%`,
      sub: 'file unchanged',
      color: '#8b5cf6',
    },
    tests_passed != null && {
      label: 'Tests',
      value: tests_passed ? 'PASS' : 'FAIL',
      sub: test_count != null ? `${test_count} passed` : 'regression check',
      color: tests_passed ? '#10b981' : '#ef4444',
    },
    {
      label: 'Issues Found',
      value: total_issues || 0,
      sub: `${security_issues || 0} security`,
      color: (security_issues || 0) > 0 ? '#ef4444' : '#64748b',
    },
  ].filter(Boolean)

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 10 }}>
      {cards.map((card, i) => (
        <div key={i} style={{
          background: '#0a0f1e', border: '1px solid #1e293b', borderRadius: 10, padding: '14px 16px',
        }}>
          <div style={{ color: '#475569', fontSize: 10, fontWeight: 600, letterSpacing: '0.05em', marginBottom: 6 }}>
            {card.label.toUpperCase()}
          </div>
          {card.before != null ? (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ color: '#64748b', fontSize: 18, fontWeight: 700 }}>{card.before}</span>
                <span style={{ color: '#334155', fontSize: 12 }}>→</span>
                {card.after != null ? (
                  <span style={{
                    fontSize: 18, fontWeight: 700,
                    color: card.improved ? '#10b981' : '#ef4444',
                  }}>{card.after}</span>
                ) : (
                  <span style={{ color: '#475569', fontSize: 12 }}>—</span>
                )}
              </div>
              {card.after != null && (
                <div style={{ color: '#334155', fontSize: 10, marginTop: 2 }}>
                  {card.improved ? '↓ improved' : '— unchanged'}
                </div>
              )}
            </div>
          ) : (
            <div>
              <div style={{ color: card.color || '#e2e8f0', fontSize: 22, fontWeight: 700 }}>{card.value}</div>
              {card.sub && <div style={{ color: '#475569', fontSize: 10, marginTop: 2 }}>{card.sub}</div>}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
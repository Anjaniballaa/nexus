export default function QualityMetrics({ analysis }) {
  if (!analysis) return null

  const {
    complexity_before, complexity_after,
    estimated_hours_saved, confidence_score,
    minimality_score, tests_passed,
    total_issues, security_issues,
  } = analysis

  const cards = [
    complexity_before != null && complexity_after != null && {
      label: 'Complexity Score',
      before: complexity_before?.toFixed(1),
      after: complexity_after?.toFixed(1),
      improved: complexity_after < complexity_before,
      unit: '',
    },
    estimated_hours_saved != null && {
      label: 'Time Saved',
      value: `~${estimated_hours_saved.toFixed(1)}h`,
      sub: 'manual effort avoided',
      color: '#10b981',
    },
    confidence_score != null && {
      label: 'Confidence',
      value: `${Math.round(confidence_score * 100)}%`,
      sub: 'modernization accuracy',
      color: '#6366f1',
    },
    minimality_score != null && {
      label: 'Minimality',
      value: `${Math.round(minimality_score * 100)}%`,
      sub: 'surgical changes only',
      color: '#8b5cf6',
    },
    tests_passed != null && {
      label: 'Tests',
      value: tests_passed ? 'PASS' : 'FAIL',
      sub: 'regression check',
      color: tests_passed ? '#10b981' : '#ef4444',
    },
    {
      label: 'Issues Found',
      value: total_issues || 0,
      sub: `${security_issues || 0} security`,
      color: security_issues > 0 ? '#ef4444' : '#64748b',
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
                <span style={{
                  fontSize: 18, fontWeight: 700,
                  color: card.improved ? '#10b981' : '#ef4444',
                }}>{card.after}</span>
              </div>
              <div style={{ color: '#334155', fontSize: 10, marginTop: 2 }}>
                {card.improved ? '↓ improved' : '↑ no change'}
              </div>
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
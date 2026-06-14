import ReactDiffViewer from 'react-diff-viewer-continued'

const RISK_COLORS = {
  LOW:    { bg: 'rgba(16,185,129,0.12)', color: '#10b981', border: 'rgba(16,185,129,0.3)' },
  MEDIUM: { bg: 'rgba(245,158,11,0.12)', color: '#f59e0b', border: 'rgba(245,158,11,0.3)' },
  HIGH:   { bg: 'rgba(239,68,68,0.12)',  color: '#ef4444', border: 'rgba(239,68,68,0.3)' },
}

export default function DiffViewer({ change, index, onAccept, onSkip }) {
  const risk = RISK_COLORS[change.risk_level] || RISK_COLORS.MEDIUM
  const isSkipped = change.status === 'skipped'
  const isAccepted = change.status === 'accepted'

  return (
    <div style={{
      border: `1px solid ${risk.border}`,
      borderRadius: 10,
      overflow: 'hidden',
      marginBottom: 20,
      opacity: isSkipped ? 0.5 : 1,
      transition: 'opacity 0.2s',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px',
        background: '#0a0f1e',
        display: 'flex',
        alignItems: 'flex-start',
        gap: 12,
        flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
          <span style={{ color: '#475569', fontSize: 11 }}>#{index + 1}</span>
          <span style={{ color: '#e2e8f0', fontSize: 13, fontWeight: 600 }}>{change.file_path}</span>
          <span style={{ color: '#64748b', fontSize: 11 }}>
            L{change.line_start}–{change.line_end}
          </span>
        </div>

        {/* Risk badge */}
        <div style={{
          padding: '3px 10px',
          borderRadius: 6,
          background: risk.bg,
          color: risk.color,
          fontSize: 11,
          fontWeight: 700,
          border: `1px solid ${risk.border}`,
          letterSpacing: '0.05em',
        }}>
          {change.risk_level}
        </div>
      </div>

      {/* Description */}
      <div style={{ padding: '8px 16px', background: '#0d1526', borderBottom: '1px solid #1e293b' }}>
        <div style={{ color: '#94a3b8', fontSize: 12 }}>
          <strong style={{ color: '#64748b' }}>Issue:</strong> {change.description}
        </div>
        {change.risk_reason && (
          <div style={{ color: '#64748b', fontSize: 11, marginTop: 4 }}>
            <strong>Risk:</strong> {change.risk_reason}
          </div>
        )}
        {change.confidence && (
          <div style={{ color: '#475569', fontSize: 11, marginTop: 2 }}>
            Confidence: {Math.round(change.confidence * 100)}%
          </div>
        )}
      </div>

      {/* Diff */}
      <div style={{ fontSize: 12 }}>
        <ReactDiffViewer
          oldValue={change.old_code}
          newValue={change.new_code}
          splitView={false}
          useDarkTheme={true}
          hideLineNumbers={false}
          showDiffOnly={false}
          styles={{
            variables: {
              dark: {
                diffViewerBackground: '#0d1526',
                diffViewerColor: '#e2e8f0',
                addedBackground: 'rgba(16,185,129,0.08)',
                addedColor: '#e2e8f0',
                removedBackground: 'rgba(239,68,68,0.08)',
                removedColor: '#e2e8f0',
                wordAddedBackground: 'rgba(16,185,129,0.25)',
                wordRemovedBackground: 'rgba(239,68,68,0.25)',
                gutterBackground: '#0a0f1e',
                gutterColor: '#334155',
              }
            }
          }}
        />
      </div>

      {/* Actions */}
      {!isSkipped && !isAccepted && onAccept && onSkip && (
        <div style={{
          padding: '10px 16px',
          background: '#0a0f1e',
          borderTop: '1px solid #1e293b',
          display: 'flex', gap: 8,
        }}>
          <button onClick={() => onAccept(change.id)} style={{
            padding: '6px 16px', borderRadius: 6, border: '1px solid #10b981',
            background: 'rgba(16,185,129,0.1)', color: '#10b981',
            fontSize: 12, fontWeight: 600, cursor: 'pointer',
          }}>
            ✓ Accept
          </button>
          <button onClick={() => onSkip(change.id)} style={{
            padding: '6px 16px', borderRadius: 6, border: '1px solid #334155',
            background: 'transparent', color: '#64748b',
            fontSize: 12, cursor: 'pointer',
          }}>
            ✕ Skip
          </button>
        </div>
      )}

      {(isAccepted || isSkipped) && (
        <div style={{
          padding: '8px 16px', background: '#0a0f1e', borderTop: '1px solid #1e293b',
          color: isAccepted ? '#10b981' : '#64748b', fontSize: 12, fontWeight: 600,
        }}>
          {isAccepted ? '✓ Accepted' : '✕ Skipped'}
        </div>
      )}
    </div>
  )
}
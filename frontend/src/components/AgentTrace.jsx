import { useEffect, useRef, useState } from 'react'

const LAYER_LABELS = {
  language_detect: { label: 'Language Detection', color: '#6366f1' },
  ast_parse:       { label: 'AST Parsing',         color: '#8b5cf6' },
  security_scan:   { label: 'Security Scan',        color: '#ef4444' },
  reader:          { label: 'Reader Agent',          color: '#f59e0b' },
  modernizer:      { label: 'Modernizer Agent',      color: '#f59e0b' },
  diff:            { label: 'Diff Engine',           color: '#3b82f6' },
  validator:       { label: 'Chunk Validator',       color: '#3b82f6' },
  test_runner:     { label: 'Test Runner',           color: '#10b981' },
  risk_scorer:     { label: 'Risk Scorer Agent',     color: '#f59e0b' },
  documenter:      { label: 'Documenter Agent',      color: '#f59e0b' },
  evaluation:      { label: 'Evaluation Engine',     color: '#6366f1' },
  complete:        { label: 'Complete',              color: '#10b981' },
}

export default function AgentTrace({ analysisId }) {
  const [traces, setTraces] = useState([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    if (!analysisId) return
    const wsUrl = `${import.meta.env.VITE_API_URL?.replace('http', 'ws') || 'ws://localhost:8000'}/ws/${analysisId}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        setTraces(prev => [...prev, { ...msg, ts: Date.now() }])
      } catch (_) {}
    }

    return () => { ws.close() }
  }, [analysisId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [traces])

  const statusDot = connected
    ? { background: '#10b981', boxShadow: '0 0 0 3px rgba(16,185,129,0.2)' }
    : { background: '#475569' }

  return (
    <div style={{
      background: '#0a0f1e', border: '1px solid #1e293b', borderRadius: 12,
      overflow: 'hidden', fontFamily: 'monospace',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #1e293b',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <div style={{ width: 8, height: 8, borderRadius: '50%', transition: 'all 0.3s', ...statusDot }} />
        <span style={{ color: '#94a3b8', fontSize: 12, fontWeight: 600, letterSpacing: '0.05em' }}>
          AGENT TRACE
        </span>
        <span style={{ color: '#334155', fontSize: 11, marginLeft: 'auto' }}>
          {traces.length} events
        </span>
      </div>

      {/* Trace log */}
      <div style={{ height: 280, overflowY: 'auto', padding: 12 }}>
        {traces.length === 0 ? (
          <div style={{ color: '#334155', fontSize: 12, padding: '8px 0' }}>
            {connected ? 'Waiting for pipeline events...' : 'Connecting...'}
          </div>
        ) : (
          traces.map((t, i) => {
            const meta = LAYER_LABELS[t.layer] || { label: t.layer, color: '#64748b' }
            return (
              <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 6, alignItems: 'flex-start' }}>
                <span style={{
                  fontSize: 10, color: '#334155', flexShrink: 0, paddingTop: 2, fontVariantNumeric: 'tabular-nums',
                }}>
                  {new Date(t.ts).toLocaleTimeString('en', { hour12: false })}
                </span>
                <span style={{
                  fontSize: 10, fontWeight: 700, color: meta.color, flexShrink: 0, paddingTop: 2,
                  minWidth: 160,
                }}>
                  [{meta.label}]
                </span>
                <span style={{ fontSize: 11, color: '#94a3b8', lineHeight: 1.4 }}>
                  {t.message}
                  {t.data && typeof t.data === 'object' && (
                    <span style={{ color: '#475569', marginLeft: 6 }}>
                      {Object.entries(t.data).slice(0, 3).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(' ')}
                    </span>
                  )}
                </span>
              </div>
            )
          })
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
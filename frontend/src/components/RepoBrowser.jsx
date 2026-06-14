import { useState, useEffect } from 'react'
import api from '../utils/api'
import toast from 'react-hot-toast'

function FileNode({ file, selected, onToggle }) {
  return (
    <div
      onClick={() => onToggle(file.path)}
      style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '5px 10px', cursor: 'pointer', borderRadius: 6,
        background: selected.has(file.path) ? 'rgba(99,102,241,0.1)' : 'transparent',
        transition: 'background 0.1s',
      }}
      onMouseEnter={e => e.currentTarget.style.background = selected.has(file.path) ? 'rgba(99,102,241,0.1)' : 'rgba(255,255,255,0.04)'}
      onMouseLeave={e => e.currentTarget.style.background = selected.has(file.path) ? 'rgba(99,102,241,0.1)' : 'transparent'}
    >
      <input
        type="checkbox"
        checked={selected.has(file.path)}
        onChange={() => onToggle(file.path)}
        onClick={e => e.stopPropagation()}
        style={{ width: 13, height: 13, accentColor: '#6366f1', flexShrink: 0 }}
      />
      <span style={{ fontSize: 12 }}>📄</span>
      <span style={{
        color: selected.has(file.path) ? '#818cf8' : '#94a3b8',
        fontSize: 12, flex: 1,
        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
      }}>
        {file.path}
      </span>
      {file.size && (
        <span style={{ color: '#334155', fontSize: 10, flexShrink: 0 }}>
          {(file.size / 1024).toFixed(1)}KB
        </span>
      )}
    </div>
  )
}

export default function RepoBrowser({ repo, connectionId, onAnalyse }) {
  const [tree, setTree] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(new Set())

  useEffect(() => {
    if (!repo || !connectionId) return
    setLoading(true)
    const [owner, repoName] = repo.split('/')
api.get(`/github/repos/${owner}/${repoName}/tree?connection_id=${connectionId}`)
      .then(r => setTree(r.data.files || r.data.tree || []))
      .catch(() => toast.error('Failed to load repo tree'))
      .finally(() => setLoading(false))
  }, [repo, connectionId])

  const toggle = (path) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(path)) next.delete(path)
      else next.add(path)
      return next
    })
  }

  const selectAll = () => {
    const allFiles = []
    const walk = (nodes) => nodes?.forEach(n => {
      if (n.type === 'file') allFiles.push(n.path)
      else walk(n.children)
    })
    walk(tree)
    setSelected(new Set(allFiles))
  }

  if (loading) return <div style={{ color: '#475569', fontSize: 13, padding: 16 }}>Loading file tree...</div>
  if (!tree) return null

  return (
    <div style={{ background: '#0a0f1e', border: '1px solid #1e293b', borderRadius: 10, overflow: 'hidden' }}>
      <div style={{
        padding: '10px 12px', borderBottom: '1px solid #1e293b',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <span style={{ color: '#94a3b8', fontSize: 12, fontWeight: 600 }}>FILES</span>
        <span style={{ color: '#475569', fontSize: 11 }}>{selected.size} selected</span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
          <button onClick={selectAll} style={{
            padding: '4px 10px', borderRadius: 5, border: '1px solid #334155',
            background: 'transparent', color: '#64748b', fontSize: 11, cursor: 'pointer',
          }}>Select all</button>
          <button
            disabled={selected.size === 0}
            onClick={() => onAnalyse([...selected])}
            style={{
              padding: '4px 12px', borderRadius: 5,
              border: '1px solid #6366f1',
              background: selected.size > 0 ? 'rgba(99,102,241,0.15)' : 'transparent',
              color: selected.size > 0 ? '#818cf8' : '#334155',
              fontSize: 11, cursor: selected.size > 0 ? 'pointer' : 'default',
              fontWeight: 600,
            }}
          >
            Analyse {selected.size > 0 ? `(${selected.size})` : ''}
          </button>
        </div>
      </div>
      <div style={{ maxHeight: 360, overflowY: 'auto', padding: 6 }}>
        {tree.map(file => (
  <FileNode key={file.path} file={file} selected={selected} onToggle={toggle} />
))}
      </div>
    </div>
  )
}
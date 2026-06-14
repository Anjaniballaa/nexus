import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'

const COLORS = ['#6366f1', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#f97316']

export default function LanguageChart({ data }) {
  if (!data || Object.keys(data).length === 0) return null

  const chartData = Object.entries(data).map(([name, value]) => ({ name, value }))

  return (
    <div style={{ background: '#0a0f1e', borderRadius: 10, border: '1px solid #1e293b', padding: 16 }}>
      <div style={{ color: '#94a3b8', fontSize: 12, fontWeight: 600, marginBottom: 12, letterSpacing: '0.05em' }}>
        LANGUAGE BREAKDOWN
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={55}
            outerRadius={80}
            paddingAngle={3}
            dataKey="value"
          >
            {chartData.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: '#0f172a', border: '1px solid #1e293b',
              borderRadius: 8, color: '#e2e8f0', fontSize: 12,
            }}
            formatter={(v) => [`${v}%`, '']}
          />
          <Legend
            formatter={(v) => <span style={{ color: '#94a3b8', fontSize: 11 }}>{v}</span>}
            iconSize={8}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
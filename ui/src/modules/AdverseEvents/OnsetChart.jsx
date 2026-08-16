import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend
} from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--paper-raised)',
      border: '1px solid var(--rule)',
      borderRadius: '5px',
      padding: '8px 12px',
      fontSize: '.78rem',
      boxShadow: 'var(--shadow-md)',
    }}>
      <div style={{ fontFamily: 'var(--f-mono)', color: 'var(--ink-3)', fontSize: '.65rem', marginBottom: 4 }}>
        Day {label} post-vaccination
      </div>
      {payload.map(p => (
        <div key={p.dataKey} style={{ color: p.color, fontVariantNumeric: 'tabular-nums' }}>
          {p.name}: {p.value?.toLocaleString()}
        </div>
      ))}
    </div>
  )
}

export default function OnsetChart({ data }) {
  if (!data?.length) {
    return (
      <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--ink-3)', fontSize: '.82rem' }}>
        No onset data loaded
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <ComposedChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
        <CartesianGrid stroke="var(--rule)" strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="onset_day"
          tick={{ fontSize: 10, fill: 'var(--ink-3)', fontFamily: 'var(--f-mono)' }}
          axisLine={false}
          tickLine={false}
          label={{ value: 'Days post-vaccination', position: 'insideBottomRight', offset: -4, fontSize: 10, fill: 'var(--ink-3)' }}
        />
        <YAxis
          tick={{ fontSize: 10, fill: 'var(--ink-3)', fontFamily: 'var(--f-mono)' }}
          axisLine={false}
          tickLine={false}
          width={36}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="count" name="All reports" fill="var(--teal-dim)" radius={[2,2,0,0]} />
        <Bar dataKey="serious_count" name="Serious" fill="var(--coral)" radius={[2,2,0,0]} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}

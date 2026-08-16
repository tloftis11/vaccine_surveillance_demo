import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer, Legend
} from 'recharts'

const HP2030 = {
  MMR: 95, DTaP: 90, VAR: 90, HepB: 90, PCV: 90,
  Hib: 90, Flu: 70, HPV: 80, MenACWY: 80, Tdap: 80
}

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
        {label}
      </div>
      {payload.map(p => (
        <div key={p.dataKey} style={{ color: p.color, fontVariantNumeric: 'tabular-nums', fontWeight: 600 }}>
          {p.value?.toFixed(1)}%
        </div>
      ))}
    </div>
  )
}

export default function CoverageTrend({ data, vaccine, selectedState }) {
  const target = HP2030[vaccine]

  if (!data?.length) {
    return (
      <div style={{ height: 240, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--ink-3)', fontSize: '.85rem' }}>
        No trend data loaded
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
        <CartesianGrid stroke="var(--rule)" strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="year"
          tick={{ fontSize: 11, fill: 'var(--ink-3)', fontFamily: 'var(--f-mono)' }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          domain={[60, 100]}
          tick={{ fontSize: 11, fill: 'var(--ink-3)', fontFamily: 'var(--f-mono)' }}
          axisLine={false}
          tickLine={false}
          tickFormatter={v => `${v}%`}
          width={40}
        />
        {target && (
          <ReferenceLine
            y={target}
            stroke="var(--amber)"
            strokeDasharray="5 3"
            label={{
              value: `HP2030 ${target}%`,
              position: 'insideTopRight',
              fontSize: 10,
              fill: 'var(--amber)',
              fontFamily: 'var(--f-mono)',
            }}
          />
        )}
        <Tooltip content={<CustomTooltip />} />
        <Line
          type="monotone"
          dataKey="coverage_rate"
          name={selectedState === 'US' ? 'National' : selectedState}
          stroke="var(--teal)"
          strokeWidth={2.5}
          dot={{ r: 3, fill: 'var(--teal)', strokeWidth: 0 }}
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

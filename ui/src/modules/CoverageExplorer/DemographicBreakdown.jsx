import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer, Cell
} from 'recharts'

const HP2030 = {
  MMR: 95, DTaP: 90, VAR: 90, HepB: 90, PCV: 90,
  Hib: 90, Flu: 70, HPV: 80, MenACWY: 80, Tdap: 80
}

const CATEGORY_LABELS = {
  race_ethnicity: 'By Race / Ethnicity',
  poverty_level:  'By Poverty Level',
  insurance_type: 'By Insurance Type',
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  const d = payload[0]
  return (
    <div style={{
      background: 'var(--paper-raised)',
      border: '1px solid var(--rule)',
      borderRadius: '5px',
      padding: '8px 12px',
      fontSize: '.78rem',
      boxShadow: 'var(--shadow-md)',
    }}>
      <div style={{ color: 'var(--ink-2)', marginBottom: 4 }}>{label}</div>
      <div style={{ color: d.color, fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>
        {d.value?.toFixed(1)}%
      </div>
      {d.payload?.ci_lower != null && (
        <div style={{ color: 'var(--ink-3)', fontSize: '.65rem', fontFamily: 'var(--f-mono)' }}>
          CI: {d.payload.ci_lower.toFixed(1)}–{d.payload.ci_upper.toFixed(1)}
        </div>
      )}
    </div>
  )
}

export default function DemographicBreakdown({ data, vaccine, category }) {
  const target = HP2030[vaccine]

  if (!data?.length) {
    return (
      <div style={{ height: 240, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--ink-3)', fontSize: '.85rem' }}>
        No demographic data loaded
      </div>
    )
  }

  return (
    <div>
      <div style={{ fontSize: '.7rem', fontFamily: 'var(--f-mono)', color: 'var(--ink-3)', letterSpacing: '.06em', textTransform: 'uppercase', marginBottom: 8 }}>
        {CATEGORY_LABELS[category] || category}
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 0, right: 24, bottom: 0, left: 100 }}
        >
          <CartesianGrid stroke="var(--rule)" strokeDasharray="3 3" horizontal={false} />
          <XAxis
            type="number"
            domain={[50, 100]}
            tick={{ fontSize: 10, fill: 'var(--ink-3)', fontFamily: 'var(--f-mono)' }}
            axisLine={false}
            tickLine={false}
            tickFormatter={v => `${v}%`}
          />
          <YAxis
            type="category"
            dataKey="demographic_value"
            tick={{ fontSize: 11, fill: 'var(--ink-2)' }}
            axisLine={false}
            tickLine={false}
            width={96}
          />
          {target && (
            <ReferenceLine
              x={target}
              stroke="var(--amber)"
              strokeDasharray="4 3"
            />
          )}
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="coverage_rate" radius={[0, 3, 3, 0]} maxBarSize={20}>
            {data.map((entry, i) => (
              <Cell
                key={i}
                fill={entry.coverage_rate >= (target || 90) ? 'var(--sage)' :
                      entry.coverage_rate >= (target || 90) - 5 ? 'var(--amber)' : 'var(--coral)'}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

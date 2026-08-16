import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, LabelList
} from 'recharts'

const CATEGORY_LABELS = {
  insurance_type:  'By Insurance Type',
  race_ethnicity:  'By Race / Ethnicity',
  poverty_level:   'By Poverty Level',
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
      <div style={{ color: 'var(--ink-2)', marginBottom: 4 }}>{label}</div>
      <div style={{ fontWeight: 700, fontVariantNumeric: 'tabular-nums', color: 'var(--teal)' }}>
        {payload[0]?.value?.toFixed(1)}% completed
      </div>
    </div>
  )
}

export default function DemographicCompletion({ data, category }) {
  if (!data?.length) {
    return (
      <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--ink-3)', fontSize: '.85rem' }}>
        No demographic data loaded
      </div>
    )
  }

  return (
    <div>
      <div style={{ fontSize: '.7rem', fontFamily: 'var(--f-mono)', color: 'var(--ink-3)', letterSpacing: '.06em', textTransform: 'uppercase', marginBottom: 12 }}>
        {CATEGORY_LABELS[category] || category}
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 0, right: 48, bottom: 0, left: 100 }}
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
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="completion_rate" radius={[0, 3, 3, 0]} maxBarSize={18}>
            <LabelList
              dataKey="completion_rate"
              position="right"
              formatter={v => `${v?.toFixed(1)}%`}
              style={{ fontSize: 10, fontFamily: 'var(--f-mono)', fill: 'var(--ink-2)' }}
            />
            {data.map((entry, i) => (
              <Cell
                key={i}
                fill={entry.completion_rate >= 85 ? 'var(--sage)' :
                      entry.completion_rate >= 75 ? 'var(--amber)' : 'var(--coral)'}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

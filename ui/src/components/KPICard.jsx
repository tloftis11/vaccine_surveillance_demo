import './KPICard.css'

export default function KPICard({ label, value, sub, delta, deltaDir, accent, loading }) {
  const accentClass = accent ? `kpi-card--${accent}` : ''
  const deltaClass = deltaDir === 'up' ? 'kpi-delta--up'
    : deltaDir === 'down' ? 'kpi-delta--down'
    : 'kpi-delta--flat'

  return (
    <div className={`kpi-card ${accentClass}`}>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value-row">
        {loading ? (
          <div className="kpi-skeleton" />
        ) : (
          <span className="kpi-value">{value ?? '—'}</span>
        )}
        {delta && !loading && (
          <span className={`kpi-delta ${deltaClass}`}>{delta}</span>
        )}
      </div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  )
}

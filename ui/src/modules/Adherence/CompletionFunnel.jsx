const DOSE_LABELS = {
  1: 'Dose 1',
  2: 'Dose 2',
  3: 'Dose 3',
  4: 'Dose 4',
  5: 'Dose 5',
}

export default function CompletionFunnel({ data, series }) {
  if (!data?.length) {
    return (
      <div style={{ padding: 'var(--sp-8)', textAlign: 'center', color: 'var(--ink-3)', fontSize: '.85rem' }}>
        No adherence data loaded — run the NIS pipeline to populate.
      </div>
    )
  }

  const sorted = [...data].sort((a, b) => a.dose_number - b.dose_number)
  const maxRate = sorted[0]?.completion_rate || 100

  return (
    <div>
      <div className="funnel-legend">
        <div className="legend-item">
          <div className="legend-swatch" style={{ background: 'var(--sage)' }} />
          On-time completion
        </div>
        <div className="legend-item">
          <div className="legend-swatch" style={{ background: 'var(--amber)', opacity: .7 }} />
          Delayed completion
        </div>
        <div className="legend-item">
          <div className="legend-swatch" style={{ background: 'var(--paper-dim)', border: '1px solid var(--rule)' }} />
          Incomplete
        </div>
      </div>

      <div className="funnel-rows">
        {sorted.map((dose, i) => {
          const total = dose.completion_rate ?? 0
          const onTime = dose.on_time_rate ?? total * 0.88
          const delayed = total - onTime
          const dropoff = i > 0 ? sorted[i - 1].completion_rate - total : null

          const onTimePct  = (onTime / 100) * 100
          const delayedPct = (delayed / 100) * 100

          return (
            <div key={dose.dose_number} className="funnel-row">
              <div className="funnel-dose-label">
                <span className="funnel-dose-name">{DOSE_LABELS[dose.dose_number] || `Dose ${dose.dose_number}`}</span>
                <span className="funnel-rate">{total.toFixed(1)}%</span>
              </div>
              <div className="funnel-track">
                <div style={{ display: 'flex', height: '100%', width: `${total}%`, transition: 'width .5s ease' }}>
                  <div style={{ flex: onTimePct, background: 'var(--sage)', borderRadius: delayedPct > 0 ? '4px 0 0 4px' : 'var(--r-sm)' }} />
                  {delayedPct > 0 && (
                    <div style={{ flex: delayedPct, background: 'var(--amber)', opacity: .75 }} />
                  )}
                </div>
              </div>
              {dropoff != null && dropoff > 0 && (
                <div className="funnel-dropoff">
                  <span className="funnel-dropoff-arrow">↓</span>
                  <span>{dropoff.toFixed(1)}pp drop-off from previous dose</span>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

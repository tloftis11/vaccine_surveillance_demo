import { useState, useMemo } from 'react'

const SEVERITY_THRESHOLD = 0.10

function getSeverity(row) {
  if (!row.serious_count || !row.report_count) return 'mild'
  const pct = row.serious_count / row.report_count
  if (pct >= SEVERITY_THRESHOLD) return 'serious'
  if (pct >= 0.03) return 'moderate'
  return 'mild'
}

export default function EventTable({ events, maxCount }) {
  const [sortKey, setSortKey]   = useState('report_count')
  const [sortDir, setSortDir]   = useState('desc')

  const sorted = useMemo(() => {
    if (!events?.length) return []
    return [...events].sort((a, b) => {
      const av = a[sortKey] ?? 0
      const bv = b[sortKey] ?? 0
      return sortDir === 'desc' ? bv - av : av - bv
    })
  }, [events, sortKey, sortDir])

  function handleSort(key) {
    if (sortKey === key) setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    else { setSortKey(key); setSortDir('desc') }
  }

  const SortIndicator = ({ k }) => {
    if (sortKey !== k) return <span style={{ opacity: .3 }}> ↕</span>
    return <span>{sortDir === 'desc' ? ' ↓' : ' ↑'}</span>
  }

  if (!sorted.length) {
    return (
      <div style={{ padding: 'var(--sp-8)', textAlign: 'center', color: 'var(--ink-3)', fontSize: '.85rem' }}>
        No adverse event data loaded — run the VAERS pipeline to populate.
      </div>
    )
  }

  return (
    <div className="table-scroll">
      <table className="event-table">
        <thead>
          <tr>
            <th onClick={() => handleSort('symptom')}>Event (MedDRA)<SortIndicator k="symptom"/></th>
            <th onClick={() => handleSort('report_count')}>Reports<SortIndicator k="report_count"/></th>
            <th onClick={() => handleSort('rate_per_million')}>Rate / M Doses<SortIndicator k="rate_per_million"/></th>
            <th onClick={() => handleSort('serious_count')}>Serious<SortIndicator k="serious_count"/></th>
            <th onClick={() => handleSort('prr')}>PRR<SortIndicator k="prr"/></th>
            <th>Signal</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => {
            const sev = getSeverity(row)
            const barWidth = maxCount ? (row.report_count / maxCount) * 100 : 0
            const isSignal = row.signal_flag || (row.prr > 2 && row.chi_squared > 4)

            return (
              <tr key={i}>
                <td className="symptom-cell">{row.symptom}</td>
                <td>
                  <div className="count-bar-wrap">
                    <span>{row.report_count?.toLocaleString()}</span>
                    <div className="count-bar-track">
                      <div className="count-bar-fill" style={{ width: `${barWidth}%` }} />
                    </div>
                  </div>
                </td>
                <td>{row.rate_per_million != null ? row.rate_per_million.toFixed(2) : '—'}</td>
                <td>
                  {row.serious_count > 0 ? (
                    <span className={`sev-badge sev-badge--${sev}`}>
                      {row.serious_count?.toLocaleString()}
                    </span>
                  ) : <span style={{ color: 'var(--ink-3)' }}>—</span>}
                </td>
                <td className={`signal-cell ${isSignal ? 'signal-cell--active' : 'signal-cell--none'}`}>
                  {row.prr != null ? row.prr.toFixed(2) : '—'}
                </td>
                <td>
                  {isSignal ? (
                    <span className="sev-badge sev-badge--serious">↑ Signal</span>
                  ) : (
                    <span style={{ color: 'var(--ink-3)', fontSize: '.65rem', fontFamily: 'var(--f-mono)' }}>—</span>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

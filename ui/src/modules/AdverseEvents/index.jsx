import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { adverseEventsApi } from '../../api/client'
import KPICard from '../../components/KPICard'
import EventTable from './EventTable'
import OnsetChart from './OnsetChart'
import './styles.css'

const VACCINES = ['FLU','COVID','MMR','HPV','DTaP','HepB','PCV','Varicella','MenACWY']
const YEARS = [2023,2022,2021,2020,2019,2018,2017]
const SEVERITY_OPTS = [
  { value: 'all',        label: 'All' },
  { value: 'serious',    label: 'Serious' },
  { value: 'non-serious',label: 'Non-serious' },
]

export default function AdverseEvents() {
  const [vaxType,  setVaxType]  = useState('FLU')
  const [year,     setYear]     = useState(2023)
  const [severity, setSeverity] = useState('all')

  const { data: summary, isLoading: sumLoading } = useQuery({
    queryKey: ['ae-summary', vaxType, year],
    queryFn: () => adverseEventsApi.summary(vaxType, year),
  })

  const { data: events = [] } = useQuery({
    queryKey: ['ae-events', vaxType, year, severity],
    queryFn: () => adverseEventsApi.events(vaxType, year, severity, 100),
  })

  const { data: onset = [] } = useQuery({
    queryKey: ['ae-onset', vaxType, year],
    queryFn: () => adverseEventsApi.onset(vaxType, year),
  })

  const maxCount = useMemo(() =>
    events.length ? Math.max(...events.map(e => e.report_count)) : 1,
    [events]
  )

  const topSignal = summary?.top_signal

  return (
    <div className="ae-layout">
      <div className="ae-header">
        <h1>Adverse Event Explorer</h1>
        <p>VAERS-based signal detection and adverse event frequency analysis. Reports do not imply causation; this is a passive surveillance system subject to reporting bias.</p>
      </div>

      <div className="vaers-caveat">
        <strong>Surveillance limitation:</strong> VAERS accepts reports from anyone — healthcare providers, patients, and manufacturers. A report does not mean the vaccine caused the event. Proportional Reporting Ratios (PRR) are screening tools, not causal measures. Always interpret signals alongside clinical and epidemiological evidence.
      </div>

      {/* Filters */}
      <div className="filter-strip">
        <div className="filter-group">
          <label className="filter-label">Vaccine</label>
          <select className="filter-select" value={vaxType} onChange={e => setVaxType(e.target.value)}>
            {VACCINES.map(v => <option key={v} value={v}>{v}</option>)}
          </select>
        </div>
        <div className="filter-group">
          <label className="filter-label">Year</label>
          <select className="filter-select" value={year} onChange={e => setYear(+e.target.value)}>
            {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
          </select>
        </div>
        <div className="filter-group">
          <label className="filter-label">Severity</label>
          <div className="severity-tabs">
            {SEVERITY_OPTS.map(o => (
              <button
                key={o.value}
                className={`severity-tab ${severity === o.value ? 'severity-tab--active' : ''}`}
                onClick={() => setSeverity(o.value)}
              >
                {o.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* KPI row */}
      <div className="kpi-row" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--sp-4)' }}>
        <KPICard
          label="Total Reports"
          value={summary?.total_reports?.toLocaleString() ?? null}
          sub={`${vaxType} · ${year}`}
          loading={sumLoading}
        />
        <KPICard
          label="Serious Reports"
          value={summary?.serious_count?.toLocaleString() ?? null}
          sub={summary?.serious_pct != null ? `${summary.serious_pct.toFixed(1)}% of total` : '—'}
          accent="coral"
          loading={sumLoading}
        />
        <KPICard
          label="Reports / M Doses"
          value={summary?.rate_per_million_doses?.toFixed(1) ?? null}
          sub="Estimated administered doses denominator"
          accent="amber"
          loading={sumLoading}
        />
        <KPICard
          label="Top Signal (PRR)"
          value={topSignal ? topSignal.prr?.toFixed(2) : '—'}
          sub={topSignal ? topSignal.symptom : 'No active signals'}
          accent={topSignal ? 'coral' : null}
          loading={sumLoading}
        />
      </div>

      {/* Active signal banner */}
      {topSignal && (
        <div className="signal-banner">
          <div className="signal-dot" />
          <div className="signal-text">
            <strong>Active Signal:</strong> {topSignal.symptom} — PRR {topSignal.prr?.toFixed(2)}, χ² {topSignal.chi_squared?.toFixed(1)} for {vaxType} · {year}
          </div>
        </div>
      )}

      {/* Main: table + onset chart */}
      <div className="ae-main">
        <div className="event-table-panel">
          <div style={{ padding: 'var(--sp-3) var(--sp-4)', borderBottom: '1px solid var(--rule)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '.85rem', fontWeight: 700, color: 'var(--ink)' }}>
              Adverse Events · {vaxType} · {year}
            </span>
            <span style={{ fontFamily: 'var(--f-mono)', fontSize: '.65rem', color: 'var(--ink-3)' }}>
              {events.length} events · click column header to sort
            </span>
          </div>
          <EventTable events={events} maxCount={maxCount} />
        </div>

        <div className="onset-panel">
          <h3>Time to Onset (Days 0–30)</h3>
          <OnsetChart data={onset} />
          {summary?.median_onset_days != null && (
            <div style={{ marginTop: 'var(--sp-3)', fontFamily: 'var(--f-mono)', fontSize: '.72rem', color: 'var(--ink-3)' }}>
              Median onset: <strong style={{ color: 'var(--ink-2)' }}>{summary.median_onset_days?.toFixed(1)} days</strong>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

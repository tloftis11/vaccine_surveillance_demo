import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { adherenceApi } from '../../api/client'
import KPICard from '../../components/KPICard'
import CompletionFunnel from './CompletionFunnel'
import DemographicCompletion from './DemographicCompletion'
import './styles.css'

const SERIES = ['DTaP','HepB','HPV','PCV','MMR','Varicella','Flu']
const YEARS  = [2023,2022,2021,2020,2019,2018]
const DEMO_CATS = [
  { value: 'insurance_type',  label: 'Insurance' },
  { value: 'race_ethnicity',  label: 'Race / Ethnicity' },
  { value: 'poverty_level',   label: 'Poverty Level' },
]

const MAX_DOSES = { DTaP: 5, HepB: 3, HPV: 2, PCV: 4, MMR: 2, Varicella: 2, Flu: 1 }

export default function Adherence() {
  const [series,  setSeries]  = useState('DTaP')
  const [year,    setYear]    = useState(2023)
  const [demoCat, setDemoCat] = useState('insurance_type')

  const { data: seriesData = [], isLoading: seriesLoading } = useQuery({
    queryKey: ['adherence-series', series, year],
    queryFn: () => adherenceApi.series(series, year),
  })

  const { data: demoData = [] } = useQuery({
    queryKey: ['adherence-demo', series, year, demoCat],
    queryFn: () => adherenceApi.demographics(series, year, demoCat),
  })

  const dose1 = seriesData.find(d => d.dose_number === 1)
  const lastDose = seriesData.length ? seriesData[seriesData.length - 1] : null
  const totalDropoff = dose1 && lastDose
    ? (dose1.completion_rate - lastDose.completion_rate).toFixed(1)
    : null
  const finalDosePct = lastDose?.completion_rate?.toFixed(1) ?? null

  return (
    <div className="adherence-layout">
      <div className="adherence-header">
        <h1>Schedule Adherence</h1>
        <p>Multi-dose series completion rates and timing — sourced from CDC National Immunization Survey. Each bar shows percentage completing that dose, split by on-time vs. delayed administration.</p>
      </div>

      {/* Series selector */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-5)', flexWrap: 'wrap' }}>
        <div className="series-selector">
          <span className="series-label">Series</span>
          {SERIES.map(s => (
            <button
              key={s}
              className={`series-pill ${series === s ? 'series-pill--active' : ''}`}
              onClick={() => setSeries(s)}
            >
              {s}
            </button>
          ))}
        </div>
        <div>
          <select
            className="year-select"
            value={year}
            onChange={e => setYear(+e.target.value)}
          >
            {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
          </select>
        </div>
        <div style={{ display: 'flex', gap: 'var(--sp-2)', alignItems: 'center' }}>
          <span className="series-label">Demographic</span>
          {DEMO_CATS.map(c => (
            <button
              key={c.value}
              className={`series-pill ${demoCat === c.value ? 'series-pill--active' : ''}`}
              onClick={() => setDemoCat(c.value)}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      {/* KPI row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--sp-4)' }}>
        <KPICard
          label="Dose 1 Initiation"
          value={dose1 ? `${dose1.completion_rate.toFixed(1)}%` : null}
          sub={`${series} · ${year}`}
          accent="teal"
          loading={seriesLoading}
        />
        <KPICard
          label={`Final Dose Completion (${MAX_DOSES[series] ?? '?'})`}
          value={finalDosePct ? `${finalDosePct}%` : null}
          sub="Fully up-to-date"
          accent={finalDosePct >= 85 ? 'sage' : finalDosePct >= 75 ? 'amber' : 'coral'}
          loading={seriesLoading}
        />
        <KPICard
          label="Total Drop-off"
          value={totalDropoff ? `${totalDropoff}pp` : null}
          sub="Dose 1 → final dose"
          accent="amber"
          loading={seriesLoading}
        />
        <KPICard
          label="On-time Rate"
          value={dose1?.on_time_rate != null ? `${dose1.on_time_rate.toFixed(1)}%` : null}
          sub="Dose 1 within recommended window"
          accent="sage"
          loading={seriesLoading}
        />
      </div>

      {/* Funnel + demographic */}
      <div className="adherence-main">
        <div className="adherence-panel">
          <h2>{series} Completion Funnel · {year}</h2>
          <CompletionFunnel data={seriesData} series={series} />
        </div>

        <div className="adherence-panel">
          <h2>Completion by Demographic</h2>
          <DemographicCompletion data={demoData} category={demoCat} />
          <div style={{ marginTop: 'var(--sp-4)', fontSize: '.75rem', color: 'var(--ink-3)', lineHeight: 1.6 }}>
            <strong style={{ color: 'var(--sage)' }}>≥85%</strong> meets national target &nbsp;·&nbsp;
            <strong style={{ color: 'var(--amber)' }}>75–84%</strong> approaching &nbsp;·&nbsp;
            <strong style={{ color: 'var(--coral)' }}>&lt;75%</strong> below target
          </div>
        </div>
      </div>
    </div>
  )
}

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { coverageApi } from '../../api/client'
import KPICard from '../../components/KPICard'
import CoverageMap from './CoverageMap'
import CoverageTrend from './CoverageTrend'
import DemographicBreakdown from './DemographicBreakdown'
import './styles.css'

const VACCINES = ['MMR','DTaP','VAR','HepB','PCV','Hib','Flu','HPV','MenACWY','Tdap']
const YEARS = [2023,2022,2021,2020,2019,2018,2017,2016,2015]
const DEMO_CATS = [
  { value: 'race_ethnicity', label: 'Race / Ethnicity' },
  { value: 'poverty_level',  label: 'Poverty Level' },
  { value: 'insurance_type', label: 'Insurance Type' },
]

const HP2030 = {
  MMR: 95, DTaP: 90, VAR: 90, HepB: 90, PCV: 90,
  Hib: 90, Flu: 70, HPV: 80, MenACWY: 80, Tdap: 80
}

export default function CoverageExplorer() {
  const [vaccine, setVaccine] = useState('MMR')
  const [year, setYear]       = useState(2023)
  const [demoCat, setDemoCat] = useState('race_ethnicity')
  const [selectedState, setSelectedState] = useState(null)

  const { data: national, isLoading: natLoading } = useQuery({
    queryKey: ['coverage-national', vaccine, year],
    queryFn: () => coverageApi.national(vaccine, year),
  })

  const { data: stateData = [] } = useQuery({
    queryKey: ['coverage-states', vaccine, year],
    queryFn: () => coverageApi.states(vaccine, year),
  })

  const trendState = selectedState || 'US'
  const { data: trendData = [] } = useQuery({
    queryKey: ['coverage-trend', vaccine, trendState],
    queryFn: () => coverageApi.trend(vaccine, trendState),
  })

  const { data: demoData = [] } = useQuery({
    queryKey: ['coverage-demographics', vaccine, year, demoCat],
    queryFn: () => coverageApi.demographics(vaccine, year, demoCat),
  })

  const selectedStateData = stateData.find(d =>
    d.state_abbr === selectedState
  )

  const rate = national?.national_rate
  const target = HP2030[vaccine]
  const targetGap = rate != null && target ? (rate - target).toFixed(1) : null
  const statesBelowTarget = national?.states_below_target ?? '—'

  const targetFillPct = rate != null ? Math.min((rate / target) * 100, 100) : 0
  const targetClass = rate == null ? '' : rate >= target ? '' : rate >= target - 5 ? 'near' : 'below'

  return (
    <div className="coverage-layout">
      <div className="coverage-header">
        <div>
          <h1>Coverage Explorer</h1>
          <p>Vaccination coverage rates by state, demographic, and year — sourced from CDC National Immunization Survey</p>
        </div>
        <div className="filter-strip">
          <div className="filter-group">
            <label className="filter-label">Vaccine</label>
            <select className="filter-select" value={vaccine} onChange={e => setVaccine(e.target.value)}>
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
            <label className="filter-label">Demographic</label>
            <select className="filter-select" value={demoCat} onChange={e => setDemoCat(e.target.value)}>
              {DEMO_CATS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* KPI row */}
      <div className="kpi-row">
        <KPICard
          label={`National ${vaccine} Coverage`}
          value={rate != null ? `${rate.toFixed(1)}%` : null}
          sub={`${year} · NIS estimate`}
          loading={natLoading}
          accent="teal"
        />
        <KPICard
          label="HP2030 Target Gap"
          value={targetGap != null ? `${targetGap > 0 ? '+' : ''}${targetGap}pp` : null}
          sub={target ? `Target: ${target}%` : '—'}
          accent={targetGap != null ? (parseFloat(targetGap) >= 0 ? 'sage' : 'coral') : null}
          deltaDir={targetGap != null && parseFloat(targetGap) >= 0 ? 'up' : 'down'}
          loading={natLoading}
        />
        <KPICard
          label="States Below Target"
          value={statesBelowTarget}
          sub={`of ${national?.total_states_with_data ?? '—'} states with data`}
          accent={statesBelowTarget > 15 ? 'coral' : statesBelowTarget > 5 ? 'amber' : 'sage'}
          loading={natLoading}
        />
        <KPICard
          label="States With Data"
          value={national?.total_states_with_data ?? '—'}
          sub={`${year} survey`}
          loading={natLoading}
        />
      </div>

      {/* Map + sidebar */}
      <div className="coverage-main">
        <div className="map-panel">
          <div className="panel-header">
            <span className="panel-title">{vaccine} Coverage by State · {year}</span>
            {selectedState && (
              <button
                onClick={() => setSelectedState(null)}
                style={{
                  fontSize: '.75rem', color: 'var(--ink-3)',
                  background: 'none', border: 'none', cursor: 'pointer',
                  textDecoration: 'underline'
                }}
              >
                Clear
              </button>
            )}
          </div>
          <CoverageMap
            stateData={stateData}
            vaccine={vaccine}
            year={year}
            selectedState={selectedState}
            onStateClick={setSelectedState}
          />
        </div>

        {/* State detail sidebar */}
        <div className="state-sidebar">
          {selectedState && selectedStateData ? (
            <>
              <div className="state-name">{selectedState}</div>
              <div className="state-rate-big">
                {selectedStateData.coverage_rate?.toFixed(1) ?? '—'}%
              </div>
              <div className="state-rate-sub">
                {vaccine} · {year}
                {selectedStateData.ci_lower != null && (
                  <span style={{ fontFamily: 'var(--f-mono)', fontSize: '.65rem', marginLeft: 6 }}>
                    ({selectedStateData.ci_lower.toFixed(1)}–{selectedStateData.ci_upper.toFixed(1)})
                  </span>
                )}
              </div>

              {target && selectedStateData.coverage_rate != null && (
                <div className="state-target-bar-wrap">
                  <div className="state-target-label">
                    <span>vs HP2030 target</span>
                    <span style={{ fontFamily: 'var(--f-mono)' }}>{target}%</span>
                  </div>
                  <div className="target-track">
                    <div
                      className={`target-fill ${targetClass}`}
                      style={{ width: `${Math.min((selectedStateData.coverage_rate / target) * 100, 100)}%` }}
                    />
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="state-detail-empty">
              <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
                <path d="M5 14 Q14 4 23 14 Q14 24 5 14Z" stroke="var(--ink-3)" strokeWidth="1.5" fill="none"/>
                <circle cx="14" cy="14" r="3" fill="var(--ink-3)"/>
              </svg>
              <span>Click a state on the map<br/>to see its detail</span>
            </div>
          )}
        </div>
      </div>

      {/* Trend + demographic charts */}
      <div className="charts-row">
        <div className="chart-panel">
          <div className="chart-title">
            Coverage Trend · {vaccine} · {trendState}
          </div>
          <CoverageTrend data={trendData} vaccine={vaccine} selectedState={trendState} />
        </div>

        <div className="chart-panel">
          <div className="chart-title">
            Demographic Breakdown · {vaccine} · {year}
          </div>
          <DemographicBreakdown data={demoData} vaccine={vaccine} category={demoCat} />
        </div>
      </div>
    </div>
  )
}

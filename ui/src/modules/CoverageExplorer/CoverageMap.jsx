import { useMemo, useState } from 'react'
import { ComposableMap, Geographies, Geography, ZoomableGroup } from 'react-simple-maps'
import { scaleLinear } from 'd3-scale'
import { interpolateRgb } from 'd3-interpolate'

const GEO_URL = 'https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json'

const STATE_FIPS = {
  '01':'AL','02':'AK','04':'AZ','05':'AR','06':'CA','08':'CO','09':'CT',
  '10':'DE','11':'DC','12':'FL','13':'GA','15':'HI','16':'ID','17':'IL',
  '18':'IN','19':'IA','20':'KS','21':'KY','22':'LA','23':'ME','24':'MD',
  '25':'MA','26':'MI','27':'MN','28':'MS','29':'MO','30':'MT','31':'NE',
  '32':'NV','33':'NH','34':'NJ','35':'NM','36':'NY','37':'NC','38':'ND',
  '39':'OH','40':'OK','41':'OR','42':'PA','44':'RI','45':'SC','46':'SD',
  '47':'TN','48':'TX','49':'UT','50':'VT','51':'VA','53':'WA','54':'WV',
  '55':'WI','56':'WY'
}

export default function CoverageMap({ stateData, vaccine, year, selectedState, onStateClick }) {
  const [tooltip, setTooltip] = useState(null)

  const rateByFips = useMemo(() => {
    const map = {}
    stateData.forEach(d => {
      if (d.state_fips) map[d.state_fips] = d
      else if (d.state_abbr) {
        const fips = Object.entries(STATE_FIPS).find(([, abbr]) => abbr === d.state_abbr)?.[0]
        if (fips) map[fips] = d
      }
    })
    return map
  }, [stateData])

  const rates = stateData.map(d => d.coverage_rate).filter(Boolean)
  const minRate = rates.length ? Math.min(...rates) : 75
  const maxRate = rates.length ? Math.max(...rates) : 99

  const colorScale = scaleLinear()
    .domain([minRate, maxRate])
    .range([0, 1])
    .clamp(true)

  const getColor = (rate) => {
    if (rate == null) return 'var(--paper-dim)'
    const t = colorScale(rate)
    return interpolateRgb('#C14E3A', '#1D6E7E')(t)
  }

  return (
    <div className="map-container" style={{ position: 'relative' }}>
      <ComposableMap
        projection="geoAlbersUsa"
        style={{ width: '100%', height: 'auto' }}
      >
        <ZoomableGroup zoom={1}>
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map(geo => {
                const fips = geo.id?.toString().padStart(2, '0')
                const abbr = STATE_FIPS[fips]
                const data = rateByFips[fips]
                const rate = data?.coverage_rate
                const isSelected = selectedState === abbr

                return (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill={getColor(rate)}
                    stroke={isSelected ? 'var(--teal)' : 'var(--paper-raised)'}
                    strokeWidth={isSelected ? 2.5 : 0.8}
                    style={{
                      default: { outline: 'none' },
                      hover:   { outline: 'none', opacity: .85, cursor: 'pointer' },
                      pressed: { outline: 'none' },
                    }}
                    onMouseEnter={e => setTooltip({
                      x: e.clientX, y: e.clientY, abbr, rate, ci_lower: data?.ci_lower, ci_upper: data?.ci_upper
                    })}
                    onMouseLeave={() => setTooltip(null)}
                    onClick={() => abbr && onStateClick(abbr)}
                  />
                )
              })
            }
          </Geographies>
        </ZoomableGroup>
      </ComposableMap>

      {tooltip && (
        <div
          className="map-tooltip"
          style={{
            position: 'fixed',
            left: tooltip.x + 12,
            top: tooltip.y - 40,
            pointerEvents: 'none',
          }}
        >
          <div className="tooltip-state">{tooltip.abbr || '—'}</div>
          <div className="tooltip-rate">
            {tooltip.rate != null ? `${tooltip.rate.toFixed(1)}%` : 'No data'}
          </div>
          {tooltip.ci_lower != null && (
            <div className="tooltip-ci">
              95% CI: {tooltip.ci_lower.toFixed(1)}–{tooltip.ci_upper.toFixed(1)}
            </div>
          )}
        </div>
      )}

      <div className="map-legend">
        <span>{minRate.toFixed(0)}%</span>
        <div className="legend-bar" />
        <span>{maxRate.toFixed(0)}%</span>
      </div>

      <style>{`
        .map-tooltip {
          background: var(--ink);
          color: var(--paper);
          padding: 6px 10px;
          border-radius: 4px;
          font-size: .75rem;
          line-height: 1.5;
          z-index: 100;
          white-space: nowrap;
        }
        .tooltip-state { font-weight: 700; font-family: var(--f-mono); font-size: .7rem; letter-spacing: .06em; }
        .tooltip-rate  { font-size: .95rem; font-weight: 700; font-variant-numeric: tabular-nums; }
        .tooltip-ci    { font-size: .65rem; opacity: .7; font-family: var(--f-mono); }
      `}</style>
    </div>
  )
}

let BASE_URL = import.meta.env.VITE_API_URL || ''
if (BASE_URL && !BASE_URL.startsWith('http')) {
  BASE_URL = 'https://' + BASE_URL
}

async function request(path, params = {}) {
  const url = new URL(`${BASE_URL}/api${path}`, window.location.origin)
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) url.searchParams.set(k, v)
  })
  const res = await fetch(url)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${res.status}: ${text}`)
  }
  return res.json()
}

// ─── Coverage ───────────────────────────────────────────────────────────────

export const coverageApi = {
  national: (vaccine, year) =>
    request('/coverage/national', { vaccine, year }),

  states: (vaccine, year) =>
    request('/coverage/states', { vaccine, year }),

  trend: (vaccine, state = 'US') =>
    request('/coverage/trend', { vaccine, state }),

  demographics: (vaccine, year, category) =>
    request('/coverage/demographics', { vaccine, year, category }),

  vaccines: () => request('/coverage/vaccines'),

  years: () => request('/coverage/years'),
}

// ─── Adverse Events ──────────────────────────────────────────────────────────

export const adverseEventsApi = {
  summary: (vax_type, year) =>
    request('/adverse-events/summary', { vax_type, year }),

  events: (vax_type, year, severity = 'all', limit = 50) =>
    request('/adverse-events/events', { vax_type, year, severity, limit }),

  onset: (vax_type, year) =>
    request('/adverse-events/onset', { vax_type, year }),

  vaccines: () => request('/adverse-events/vaccines'),

  years: () => request('/adverse-events/years'),
}

// ─── Adherence ───────────────────────────────────────────────────────────────

export const adherenceApi = {
  series: (series, year, state = 'US') =>
    request('/adherence/series', { series, year, state }),

  demographics: (series, year, category = 'insurance_type') =>
    request('/adherence/demographics', { series, year, category }),

  seriesList: () => request('/adherence/series-list'),

  years: () => request('/adherence/years'),
}

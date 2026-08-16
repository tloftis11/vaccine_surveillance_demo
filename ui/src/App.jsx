import { Suspense, lazy } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Navigation from './components/Navigation'

const CoverageExplorer = lazy(() => import('./modules/CoverageExplorer'))
const AdverseEvents    = lazy(() => import('./modules/AdverseEvents'))
const Adherence        = lazy(() => import('./modules/Adherence'))

function ModuleLoader() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flex: 1, color: 'var(--ink-3)', fontSize: '.9rem', gap: '12px'
    }}>
      <svg width="20" height="20" viewBox="0 0 20 20" style={{ animation: 'spin 1s linear infinite' }}>
        <circle cx="10" cy="10" r="8" stroke="var(--teal-dim)" strokeWidth="3" fill="none"/>
        <path d="M10 2a8 8 0 0 1 8 8" stroke="var(--teal)" strokeWidth="3" strokeLinecap="round" fill="none"/>
      </svg>
      Loading module…
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}

export default function App() {
  return (
    <>
      <Navigation />
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflowY: 'auto' }}>
        <Suspense fallback={<ModuleLoader />}>
          <Routes>
            <Route path="/" element={<Navigate to="/coverage" replace />} />
            <Route path="/coverage"       element={<CoverageExplorer />} />
            <Route path="/adverse-events" element={<AdverseEvents />} />
            <Route path="/adherence"      element={<Adherence />} />
          </Routes>
        </Suspense>
      </main>
    </>
  )
}

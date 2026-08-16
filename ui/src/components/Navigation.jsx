import { NavLink } from 'react-router-dom'
import './Navigation.css'

const MODULES = [
  { path: '/coverage',        label: 'Coverage Explorer' },
  { path: '/adverse-events',  label: 'Adverse Events' },
  { path: '/adherence',       label: 'Schedule Adherence' },
]

export default function Navigation() {
  return (
    <header className="nav-shell">
      <div className="nav-brand">
        <svg className="nav-logo" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect width="24" height="24" rx="5" fill="var(--teal)"/>
          <path d="M12 5v14M7 10h10" stroke="white" strokeWidth="2.2" strokeLinecap="round"/>
          <circle cx="12" cy="19" r="1.8" fill="white"/>
        </svg>
        <div className="nav-brand-text">
          <span className="nav-brand-name">Vaccine Surveillance</span>
          <span className="nav-brand-sub">Public Health Intelligence</span>
        </div>
      </div>
      <nav className="nav-tabs">
        {MODULES.map(({ path, label }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) =>
              `nav-tab ${isActive ? 'nav-tab--active' : ''}`
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>
    </header>
  )
}

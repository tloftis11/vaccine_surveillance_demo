import './EmptyState.css'

export default function EmptyState({ title, message, icon }) {
  return (
    <div className="empty-state">
      {icon && <div className="empty-icon">{icon}</div>}
      <h3 className="empty-title">{title}</h3>
      {message && <p className="empty-message">{message}</p>}
    </div>
  )
}

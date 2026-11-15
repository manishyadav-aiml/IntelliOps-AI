import { Activity, AlertTriangle, BookOpen, FileText, FileDown, LayoutDashboard, MessageSquare, Settings } from 'lucide-react'
import { NavLink } from 'react-router-dom'

// Only routes that exist are listed. Entries are added as each phase delivers its page.
const NAV_ITEMS = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/logs', label: 'Logs', icon: FileText },
  { to: '/anomalies', label: 'Anomalies', icon: Activity },
  { to: '/incidents', label: 'Incidents', icon: AlertTriangle },
  { to: '/documents', label: 'Documents', icon: BookOpen },
  { to: '/assistant', label: 'Assistant', icon: MessageSquare },
  { to: '/reports', label: 'Reports', icon: FileDown },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export default function Sidebar() {
  return (
    <aside className="w-full bg-navy-900 text-slate-200 md:min-h-screen md:w-60">
      <div className="px-5 py-4 text-lg font-semibold text-white">IntelliOps AI</div>
      <nav aria-label="Main navigation" className="px-2 pb-4">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-2 rounded-md px-3 py-2 text-sm ${
                isActive ? 'bg-blue-600 text-white' : 'hover:bg-navy-800'
              }`
            }
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}

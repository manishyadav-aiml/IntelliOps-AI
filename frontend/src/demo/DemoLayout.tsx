import {
  Activity,
  AlertTriangle,
  BookOpen,
  FileDown,
  FileText,
  LayoutDashboard,
  MessageSquare,
  Settings,
} from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'

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

export default function DemoLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-slate-50 md:flex-row">
      <aside className="w-full bg-navy-900 text-slate-200 md:min-h-screen md:w-60 md:shrink-0">
        <div className="border-b border-slate-700 px-5 py-5">
          <div className="text-xl font-bold text-white">IntelliOps AI</div>
          <div className="mt-1 text-xs text-slate-400">Intelligent Operations Platform</div>
        </div>

        <nav aria-label="Demo navigation" className="flex gap-1 overflow-x-auto p-2 md:flex-col">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex shrink-0 items-center gap-3 rounded-md px-3 py-2.5 text-sm transition ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-300 hover:bg-navy-800 hover:text-white'
                }`
              }
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-4 hidden border-t border-slate-700 px-5 py-4 md:block">
          <div className="flex items-center gap-2 text-xs text-green-400">
            <span className="h-2 w-2 rounded-full bg-green-400" />
            Demo environment
          </div>
          <p className="mt-2 text-xs leading-5 text-slate-400">
            Static demonstration. No production systems are connected.
          </p>
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b bg-white px-4 py-3 md:px-6">
          <div>
            <div className="font-semibold text-slate-800">Operations Console</div>
            <div className="text-xs text-slate-500">Public portfolio demonstration</div>
          </div>
          <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800">
            DEMO MODE
          </span>
        </header>

        <div className="border-b border-blue-200 bg-blue-50 px-4 py-2.5 text-sm text-blue-900 md:px-6">
          <strong>Sample data only:</strong> This public demo uses illustrative data.
          Backend, database, file processing, and live AI services are not connected.
        </div>

        <main className="p-4 md:p-6">
          <Outlet />
        </main>

        <footer className="border-t bg-white px-6 py-4 text-center text-xs text-slate-500">
          IntelliOps AI · Public Demo · Sample data only
        </footer>
      </div>
    </div>
  )
}

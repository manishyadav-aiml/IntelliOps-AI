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
import { NavLink, Outlet, useLocation } from 'react-router-dom'

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
  const location = useLocation()

  const currentPage =
    NAV_ITEMS.find((item) =>
      item.to === '/'
        ? location.pathname === '/'
        : location.pathname.startsWith(item.to),
    )?.label ?? 'Overview'

  return (
    <div className="min-h-screen bg-slate-50 md:flex">

      {/* Sidebar */}
      <aside className="flex w-full shrink-0 flex-col bg-[#101c35] text-slate-300 md:sticky md:top-0 md:h-screen md:w-64">

        {/* Brand */}
        <div className="flex items-center gap-3 border-b border-white/10 px-6 py-6">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-sm font-bold text-white shadow-lg shadow-blue-950/30">
            IO
          </div>

          <div>
            <h1 className="text-lg font-bold tracking-tight text-white">
              IntelliOps AI
            </h1>
            <p className="mt-0.5 text-[11px] tracking-wide text-slate-400">
              INTELLIGENT OPERATIONS
            </p>
          </div>
        </div>

        {/* Navigation */}
        <div className="px-4 pt-7">
          <p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
            Workspace
          </p>

          <nav aria-label="Primary navigation" className="flex gap-1.5 overflow-x-auto pb-3 md:flex-col md:overflow-visible">
            {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `flex shrink-0 items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-md shadow-blue-950/20'
                      : 'text-slate-400 hover:bg-white/5 hover:text-white'
                  }`
                }
              >
                <Icon className="h-[18px] w-[18px]" aria-hidden="true" />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Sidebar bottom */}
        <div className="mt-auto hidden border-t border-white/10 px-6 py-5 md:block">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-slate-500" />
            <span className="text-xs font-medium text-slate-300">
              Portfolio workspace
            </span>
          </div>
          <p className="mt-2 text-[11px] leading-5 text-slate-500">
            IntelliOps AI Operations Platform
          </p>
        </div>
      </aside>

      {/* Main application */}
      <div className="flex min-h-screen min-w-0 flex-1 flex-col">

        {/* Top header */}
        <header className="sticky top-0 z-10 flex min-h-[76px] items-center justify-between border-b border-slate-200 bg-white/95 px-5 backdrop-blur md:px-8">
          <div>
            <p className="text-xs font-medium text-slate-400">
              Workspace / {currentPage}
            </p>
            <h2 className="mt-1 text-xl font-semibold tracking-tight text-slate-900">
              {currentPage}
            </h2>
          </div>

          <div className="hidden items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-2 sm:flex">
            <span className="h-2 w-2 rounded-full bg-slate-400" />
            <span className="text-xs font-medium text-slate-600">
              Portfolio preview
            </span>
          </div>
        </header>

        {/* Page content */}
        <main className="w-full flex-1 p-5 md:p-8">
          <Outlet />
        </main>

        {/* Footer */}
        <footer className="border-t border-slate-200 bg-white px-5 py-4 md:px-8">
          <div className="flex flex-col items-center justify-between gap-2 text-center sm:flex-row sm:text-left">
            <p className="text-xs font-medium text-slate-500">
              © 2026 IntelliOps AI
            </p>

            <p className="text-[11px] text-slate-400">
              IntelliOps AI · Intelligent Operations Platform · Portfolio Preview
            </p>
          </div>
        </footer>
      </div>
    </div>
  )
}
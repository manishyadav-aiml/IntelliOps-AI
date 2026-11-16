import {
  Activity,
  BrainCircuit,
  Database,
  Globe,
  LockKeyhole,
  Server,
  ShieldCheck,
} from 'lucide-react'

const SETTINGS = [
  {
    title: 'Application Environment',
    description: 'Public static demonstration',
    value: 'DEMO',
    icon: Globe,
  },
  {
    title: 'Backend API',
    description: 'FastAPI service connection',
    value: 'Not connected',
    icon: Server,
  },
  {
    title: 'Database',
    description: 'PostgreSQL / application storage',
    value: 'Not connected',
    icon: Database,
  },
  {
    title: 'AI / ML Services',
    description: 'Model inference and AI processing',
    value: 'Not active',
    icon: BrainCircuit,
  },
  {
    title: 'Monitoring',
    description: 'Live infrastructure monitoring',
    value: 'Sample data only',
    icon: Activity,
  },
  {
    title: 'Authentication',
    description: 'User login and session management',
    value: 'Disabled in demo',
    icon: LockKeyhole,
  },
]

export default function DemoSettings() {
  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-bold text-slate-900">Platform Settings</h1>
        <p className="mt-1 text-sm text-slate-500">
          Review the configuration and limitations of this public demonstration.
        </p>
      </section>

      <section className="rounded-lg border border-blue-200 bg-blue-50 p-4">
        <div className="flex items-start gap-3">
          <ShieldCheck className="mt-0.5 h-6 w-6 shrink-0 text-blue-700" />
          <div>
            <h2 className="font-semibold text-blue-900">Isolated demonstration environment</h2>
            <p className="mt-1 text-sm leading-6 text-blue-800">
              This GitHub Pages deployment is a static frontend. It does not connect
              to the production backend, database, authentication system, or AI services.
              Changes made in this demonstration cannot affect production data.
            </p>
          </div>
        </div>
      </section>

      <section className="overflow-hidden rounded-lg border bg-white shadow-sm">
        <div className="border-b px-4 py-3">
          <h2 className="font-semibold text-slate-800">System Configuration</h2>
          <p className="mt-1 text-xs text-slate-500">
            Actual connection states for this static demonstration.
          </p>
        </div>

        <div className="divide-y">
          {SETTINGS.map(({ title, description, value, icon: Icon }) => (
            <div
              key={title}
              className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-slate-100 p-2 text-slate-600">
                  <Icon className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-medium text-slate-800">{title}</h3>
                  <p className="mt-1 text-xs text-slate-500">{description}</p>
                </div>
              </div>

              <span className="w-fit rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800">
                {value}
              </span>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-lg border bg-white p-4 shadow-sm">
        <h2 className="font-semibold text-slate-800">Deployment Information</h2>
        <dl className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-xs text-slate-500">Hosting platform</dt>
            <dd className="mt-1 text-sm font-medium text-slate-800">GitHub Pages</dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500">Application type</dt>
            <dd className="mt-1 text-sm font-medium text-slate-800">Static React application</dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500">Data source</dt>
            <dd className="mt-1 text-sm font-medium text-slate-800">Local illustrative records</dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500">Production system access</dt>
            <dd className="mt-1 text-sm font-medium text-slate-800">None</dd>
          </div>
        </dl>
      </section>

      <p className="text-xs text-slate-500">
        Production configuration, API credentials, account management, and system controls
        are intentionally unavailable in this public demo.
      </p>
    </div>
  )
}

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
    description: 'Public portfolio deployment',
    value: 'Static frontend',
    type: 'neutral',
    icon: Globe,
  },
  {
    title: 'Backend API',
    description: 'FastAPI service connection',
    value: 'Disconnected',
    type: 'warning',
    icon: Server,
  },
  {
    title: 'Database',
    description: 'PostgreSQL application storage',
    value: 'Disconnected',
    type: 'warning',
    icon: Database,
  },
  {
    title: 'AI / ML Services',
    description: 'Model inference and AI processing',
    value: 'Inactive',
    type: 'warning',
    icon: BrainCircuit,
  },
  {
    title: 'Monitoring',
    description: 'Infrastructure and application metrics',
    value: 'Illustrative data',
    type: 'info',
    icon: Activity,
  },
  {
    title: 'Authentication',
    description: 'User login and session management',
    value: 'Unavailable',
    type: 'neutral',
    icon: LockKeyhole,
  },
]

const STATUS_STYLES: Record<string, string> = {
  neutral: 'border-slate-200 bg-slate-100 text-slate-600',
  warning: 'border-amber-200 bg-amber-50 text-amber-700',
  info: 'border-blue-200 bg-blue-50 text-blue-700',
}

export default function DemoSettings() {
  return (
    <div className="space-y-6">
      <section>
        <p className="text-sm leading-6 text-slate-500">
          Review application services, integration availability, and deployment details.
        </p>
      </section>

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 px-5 py-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-blue-600" />
            <h2 className="text-sm font-semibold text-slate-800">
              Environment overview
            </h2>
          </div>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            This public deployment operates independently of the production system.
          </p>
        </div>

        <div className="grid grid-cols-1 divide-y divide-slate-100 sm:grid-cols-2 sm:divide-x sm:divide-y-0">
          <div className="p-5">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-400">
              Deployment type
            </p>
            <p className="mt-2 text-lg font-semibold text-slate-900">
              Static web application
            </p>
            <p className="mt-1 text-xs text-slate-500">
              React frontend hosted on GitHub Pages
            </p>
          </div>

          <div className="p-5">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-400">
              Production connectivity
            </p>
            <p className="mt-2 text-lg font-semibold text-slate-900">
              Not connected
            </p>
            <p className="mt-1 text-xs text-slate-500">
              No access to production services or data
            </p>
          </div>
        </div>
      </section>

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-800">
            Service configuration
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            Availability of application components in this deployment.
          </p>
        </div>

        <div className="divide-y divide-slate-100">
          {SETTINGS.map(({ title, description, value, type, icon: Icon }) => (
            <div
              key={title}
              className="flex flex-col gap-3 px-5 py-4 transition-colors hover:bg-slate-50/70 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="flex min-w-0 items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
                  <Icon className="h-5 w-5" />
                </div>

                <div className="min-w-0">
                  <h3 className="text-sm font-medium text-slate-800">
                    {title}
                  </h3>
                  <p className="mt-1 text-xs text-slate-500">
                    {description}
                  </p>
                </div>
              </div>

              <span
                className={`w-fit shrink-0 rounded-full border px-3 py-1 text-xs font-semibold ${STATUS_STYLES[type]}`}
              >
                {value}
              </span>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-800">
          Deployment information
        </h2>

        <dl className="mt-5 grid grid-cols-1 gap-x-8 gap-y-5 sm:grid-cols-2">
          {[
            ['Hosting platform', 'GitHub Pages'],
            ['Application framework', 'React + Vite'],
            ['Application type', 'Static frontend'],
            ['Data source', 'Illustrative local records'],
            ['Backend integration', 'Not configured'],
            ['Production access', 'None'],
          ].map(([label, value]) => (
            <div key={label}>
              <dt className="text-xs font-medium text-slate-400">
                {label}
              </dt>
              <dd className="mt-1.5 text-sm font-medium text-slate-800">
                {value}
              </dd>
            </div>
          ))}
        </dl>
      </section>

      <p className="text-xs leading-5 text-slate-400">
        Production credentials, account management, and administrative controls
        are not exposed in this public portfolio deployment.
      </p>
    </div>
  )
}
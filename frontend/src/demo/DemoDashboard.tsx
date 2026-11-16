import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import MetricCard from '../components/common/MetricCard'
import ChartCard from '../components/common/ChartCard'
import DataTable from '../components/common/DataTable'
import SeverityBadge from '../components/common/SeverityBadge'
import StatusBadge from '../components/common/StatusBadge'
import { demoIncidents, demoMetrics, demoTrendData } from './data'

export default function DemoDashboard() {
  const columns = [
    { header: 'Incident ID', cell: (row: typeof demoIncidents[number]) => <span className="font-medium text-blue-700">{row.id}</span> },
    { header: 'Incident', cell: (row: typeof demoIncidents[number]) => row.title },
    { header: 'Service', cell: (row: typeof demoIncidents[number]) => <span className="font-mono text-xs">{row.service}</span> },
    { header: 'Severity', cell: (row: typeof demoIncidents[number]) => <SeverityBadge value={row.severity} /> },
    { header: 'Status', cell: (row: typeof demoIncidents[number]) => <StatusBadge value={row.status} /> },
    { header: 'Detected', cell: (row: typeof demoIncidents[number]) => <span className="whitespace-nowrap text-slate-500">{row.time}</span> },
  ]

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Operations Overview</h1>
          <p className="mt-1 text-sm text-slate-500">
            Illustrative monitoring metrics and operational activity.
          </p>
        </div>
        <span className="rounded-md border bg-white px-3 py-2 text-xs text-slate-600">
          Example reporting period · 16 November 2026
        </span>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {demoMetrics.map((metric) => (
          <MetricCard
            key={metric.label}
            label={metric.label}
            value={metric.value}
            hint={metric.hint}
          />
        ))}
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <ChartCard title="Log Volume & Anomaly Trend" empty={false}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={demoTrendData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="events" name="Log events" stroke="#2563eb" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="anomalies" name="Anomalies" stroke="#ea580c" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>

        <section className="rounded-lg border bg-white p-4 shadow-sm">
          <h2 className="mb-4 font-medium text-slate-800">Platform Summary</h2>
          <div className="space-y-4">
            <div>
              <div className="text-sm text-slate-500">Environment</div>
              <div className="mt-1 font-semibold">Public Demo</div>
            </div>
            <div>
              <div className="text-sm text-slate-500">Data source</div>
              <div className="mt-1 font-semibold">Static sample records</div>
            </div>
            <div>
              <div className="text-sm text-slate-500">Backend connection</div>
              <div className="mt-1">
                <StatusBadge value="UNKNOWN" />
                <span className="ml-2 text-xs text-slate-500">Not connected</span>
              </div>
            </div>
            <div>
              <div className="text-sm text-slate-500">AI processing</div>
              <div className="mt-1 font-semibold">Not active in demo</div>
            </div>
          </div>
        </section>
      </section>

      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Recent Incidents</h2>
            <p className="text-sm text-slate-500">Example incident records for demonstration.</p>
          </div>
          <span className="text-xs text-slate-500">{demoIncidents.length} sample records</span>
        </div>
        <DataTable
          columns={columns}
          rows={demoIncidents}
          rowKey={(row) => row.id}
        />
      </section>
    </div>
  )
}

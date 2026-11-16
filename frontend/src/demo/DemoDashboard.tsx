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

import {
  demoIncidents,
  demoMetrics,
  demoTrendData,
} from './data'

export default function DemoDashboard() {
  const openIncidents = demoIncidents.filter(
    (incident) =>
      incident.status === 'OPEN' ||
      incident.status === 'INVESTIGATING',
  ).length

  const resolvedIncidents = demoIncidents.filter(
    (incident) => incident.status === 'RESOLVED',
  ).length

  const columns = [
    {
      header: 'Incident ID',
      cell: (row: typeof demoIncidents[number]) => (
        <span className="font-semibold text-blue-700">{row.id}</span>
      ),
    },
    {
      header: 'Incident',
      cell: (row: typeof demoIncidents[number]) => (
        <span className="font-medium text-slate-800">{row.title}</span>
      ),
    },
    {
      header: 'Service',
      cell: (row: typeof demoIncidents[number]) => (
        <span className="font-mono text-xs text-slate-500">
          {row.service}
        </span>
      ),
    },
    {
      header: 'Severity',
      cell: (row: typeof demoIncidents[number]) => (
        <SeverityBadge value={row.severity} />
      ),
    },
    {
      header: 'Status',
      cell: (row: typeof demoIncidents[number]) => (
        <StatusBadge value={row.status} />
      ),
    },
    {
      header: 'Detected',
      cell: (row: typeof demoIncidents[number]) => (
        <span className="whitespace-nowrap text-slate-500">
          {row.time}
        </span>
      ),
    },
  ]

  return (
    <div className="space-y-7">
      {/* Dashboard introduction */}
      <section className="flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-2xl text-sm leading-6 text-slate-500">
          Monitor system activity, identify unusual patterns, and track
          incident response across your operations.
        </p>

        <span className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600">
          Reporting period · 16 Nov 2026
        </span>
      </section>

      {/* Key metrics */}
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

      {/* Trend chart and incident snapshot */}
      <section className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <div className="min-w-0 xl:col-span-2">
          <ChartCard
            title="Log Volume & Anomaly Trend"
            empty={demoTrendData.length === 0}
            emptyMessage="No trend data available."
          >
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={demoTrendData}
                margin={{ top: 8, right: 12, left: 0, bottom: 0 }}
              >
                <CartesianGrid
                  stroke="#e2e8f0"
                  strokeDasharray="3 3"
                  vertical={false}
                />

                <XAxis
                  dataKey="time"
                  tick={{ fontSize: 11, fill: '#64748b' }}
                  tickLine={false}
                  axisLine={{ stroke: '#e2e8f0' }}
                />

                <YAxis
                  yAxisId="events"
                  tick={{ fontSize: 11, fill: '#64748b' }}
                  tickLine={false}
                  axisLine={false}
                  width={42}
                />

                <YAxis
                  yAxisId="anomalies"
                  orientation="right"
                  tick={{ fontSize: 11, fill: '#64748b' }}
                  tickLine={false}
                  axisLine={false}
                  width={35}
                />

                <Tooltip
                  contentStyle={{
                    borderRadius: '10px',
                    border: '1px solid #e2e8f0',
                    boxShadow: '0 4px 12px rgba(15, 23, 42, 0.08)',
                    fontSize: '12px',
                  }}
                />

                <Legend
                  wrapperStyle={{
                    fontSize: '12px',
                    paddingTop: '12px',
                  }}
                />

                <Line
                  yAxisId="events"
                  type="monotone"
                  dataKey="events"
                  name="Log events"
                  stroke="#2563eb"
                  strokeWidth={2.5}
                  dot={false}
                  activeDot={{ r: 5 }}
                />

                <Line
                  yAxisId="anomalies"
                  type="monotone"
                  dataKey="anomalies"
                  name="Anomalies"
                  stroke="#ea580c"
                  strokeWidth={2.5}
                  dot={{ r: 3, strokeWidth: 0 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>

        {/* Incident snapshot */}
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="border-b border-slate-100 pb-4">
            <h2 className="text-sm font-semibold text-slate-800">
              Incident Snapshot
            </h2>
            <p className="mt-1 text-xs text-slate-400">
              Latest incident records represented in this workspace
            </p>
          </div>

          <div className="space-y-5 pt-5">
            <div>
              <p className="text-xs font-medium text-slate-500">
                Incident records
              </p>
              <p className="mt-1 text-3xl font-bold tracking-tight text-slate-900">
                {demoIncidents.length}
              </p>
            </div>

            {/* Open and investigating incidents */}
            <div className="border-t border-slate-100 pt-4">
              <p className="text-xs text-slate-500">
                Open / Investigating
              </p>
              <p className="mt-1 text-xl font-semibold text-slate-900">
                {openIncidents}
              </p>
            </div>

            {/* Resolved incidents */}
            <div className="flex items-center justify-between border-t border-slate-100 pt-4">
              <div>
                <p className="text-xs text-slate-500">Resolved</p>
                <p className="mt-1 text-xl font-semibold text-slate-900">
                  {resolvedIncidents}
                </p>
              </div>
              <StatusBadge value="RESOLVED" />
            </div>
          </div>
        </section>
      </section>

      {/* Recent incidents */}
      <section className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold tracking-tight text-slate-900">
              Recent Incidents
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Incident activity across monitored services.
            </p>
          </div>

          <span className="text-xs font-medium text-slate-500">
            {demoIncidents.length} records
          </span>
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
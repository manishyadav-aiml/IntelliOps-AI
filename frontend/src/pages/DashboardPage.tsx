import { RefreshCw } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import ChartCard from '../components/common/ChartCard'
import EmptyState from '../components/common/EmptyState'
import ErrorMessage from '../components/common/ErrorMessage'
import MetricCard from '../components/common/MetricCard'
import SeverityBadge from '../components/common/SeverityBadge'
import Spinner from '../components/common/Spinner'
import { incidentService } from '../services/incidentService'
import { dashboardService } from '../services/knowledgeService'
import type { Incident } from '../types/incidents'
import type { DashboardFilters, DashboardSummary, DashboardTrends, NamedCount } from '../types/knowledge'
import { getErrorMessage } from '../utils/errors'

const COLORS = ['#2563eb', '#f97316', '#eab308', '#64748b', '#16a34a']

function duration(seconds: number | null): string | null {
  if (seconds === null) return null
  if (seconds < 90) return `${Math.round(seconds)} s`
  if (seconds < 5400) return `${Math.round(seconds / 60)} min`
  return `${(seconds / 3600).toFixed(1)} h`
}

const tick = (bucket: string) => new Date(bucket).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit' })

export default function DashboardPage() {
  const [filters, setFilters] = useState<DashboardFilters>({ bucket: 'hour' })
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [trends, setTrends] = useState<DashboardTrends | null>(null)
  const [services, setServices] = useState<NamedCount[]>([])
  const [recent, setRecent] = useState<Incident[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    const f: DashboardFilters = {
      ...filters,
      start: startDate ? `${startDate}T00:00:00Z` : undefined,
      end: endDate ? `${endDate}T23:59:59Z` : undefined,
    }
    try {
      const [s, t, sv, inc] = await Promise.all([
        dashboardService.summary(f),
        dashboardService.trends(f),
        dashboardService.services(),
        incidentService.list({ page: 1 }),
      ])
      setSummary(s); setTrends(t); setServices(sv); setRecent(inc.items.slice(0, 5)); setError(null)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [filters, startDate, endDate])

  useEffect(() => { void load() }, [load])

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Overview</h1>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <label>From <input type="date" aria-label="Start date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="rounded border px-2 py-1" /></label>
          <label>To <input type="date" aria-label="End date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="rounded border px-2 py-1" /></label>
          <select aria-label="Service filter" value={filters.service ?? ''} onChange={(e) => setFilters({ ...filters, service: e.target.value || undefined })} className="rounded border px-2 py-1">
            <option value="">All services</option>
            {services.map((s) => <option key={s.name} value={s.name}>{s.name}</option>)}
          </select>
          <select aria-label="Bucket size" value={filters.bucket} onChange={(e) => setFilters({ ...filters, bucket: e.target.value as 'hour' | 'day' })} className="rounded border px-2 py-1">
            <option value="hour">Hourly</option><option value="day">Daily</option>
          </select>
          <button type="button" onClick={() => void load()} className="flex items-center gap-1 rounded border px-3 py-1">
            <RefreshCw className="h-4 w-4" aria-hidden="true" /> Refresh
          </button>
        </div>
      </div>

      {error && <ErrorMessage message={error} />}
      {loading && !summary ? <Spinner /> : summary && trends && (
        <>
          {summary.uploads_total === 0 && <EmptyState message="No data yet. Upload a log file on the Logs page, then run anomaly detection." />}
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <MetricCard label="Logs processed" value={summary.total_logs_processed} />
            <MetricCard label="Active incidents" value={summary.active_incidents} />
            <MetricCard label="Critical (P1) incidents" value={summary.critical_incidents} />
            <MetricCard label="Anomalous windows" value={summary.anomalies_detected} />
            <MetricCard label="Services monitored" value={summary.services_monitored} />
            <MetricCard label="Resolved incidents" value={summary.resolved_incidents} />
            <MetricCard label="Avg. time to acknowledge" value={duration(summary.avg_time_to_acknowledge_seconds)} hint="n/a until an incident is acknowledged" />
            <MetricCard label="Avg. time to resolve" value={duration(summary.avg_time_to_resolve_seconds)} hint="n/a until an incident is resolved" />
          </div>
          {trends.truncated && <p className="text-xs text-amber-700">Large data set: error frequency uses the first 200,000 matching entries.</p>}
          <div className="grid gap-4 lg:grid-cols-2">
            <ChartCard title="Error frequency over time" empty={trends.error_frequency.length === 0}>
              <ResponsiveContainer><LineChart data={trends.error_frequency}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="bucket" tickFormatter={tick} /><YAxis allowDecimals={false} /><Tooltip labelFormatter={tick} /><Line type="monotone" dataKey="count" stroke="#dc2626" dot={false} /></LineChart></ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Anomaly trend (anomalous windows)" empty={trends.anomaly_trend.length === 0}>
              <ResponsiveContainer><BarChart data={trends.anomaly_trend}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="bucket" tickFormatter={tick} /><YAxis allowDecimals={false} /><Tooltip labelFormatter={tick} /><Bar dataKey="count" fill="#2563eb" /></BarChart></ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Incident severity distribution" empty={trends.severity_distribution.length === 0}>
              <ResponsiveContainer><PieChart><Pie data={trends.severity_distribution} dataKey="count" nameKey="name" label>{trends.severity_distribution.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Service-wise incident distribution" empty={services.length === 0}>
              <ResponsiveContainer><BarChart data={services} layout="vertical"><CartesianGrid strokeDasharray="3 3" /><XAxis type="number" allowDecimals={false} /><YAxis type="category" dataKey="name" width={110} /><Tooltip /><Bar dataKey="count" fill="#0ea5e9" /></BarChart></ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Incident resolution trend" empty={trends.resolution_trend.length === 0} emptyMessage="No incidents resolved in this period.">
              <ResponsiveContainer><BarChart data={trends.resolution_trend}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="bucket" tickFormatter={tick} /><YAxis allowDecimals={false} /><Tooltip labelFormatter={tick} /><Bar dataKey="count" fill="#16a34a" /></BarChart></ResponsiveContainer>
            </ChartCard>
            <section className="rounded-lg border bg-white p-4 shadow-sm">
              <h2 className="mb-3 font-medium">Top recurring log templates</h2>
              {trends.top_templates.length === 0 ? <EmptyState message="No templates yet." /> : (
                <ol className="space-y-1 text-sm">{trends.top_templates.map((t) => <li key={t.name} className="flex justify-between gap-3"><code className="truncate" title={t.name}>{t.name}</code><span className="font-medium">{t.count}</span></li>)}</ol>
              )}
            </section>
          </div>
          <section className="rounded-lg border bg-white p-4 shadow-sm">
            <h2 className="mb-3 font-medium">Recent incidents</h2>
            {recent.length === 0 ? <EmptyState message="No incidents yet." /> : (
              <ul className="divide-y text-sm">{recent.map((i) => (
                <li key={i.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                  <Link to={`/incidents/${i.id}`} className="text-blue-600 hover:underline">{i.public_id} {i.title}</Link>
                  <span className="flex items-center gap-2"><SeverityBadge value={i.severity} /><span className="text-slate-500">{i.status}</span></span>
                </li>))}
              </ul>
            )}
          </section>
        </>
      )}
    </section>
  )
}

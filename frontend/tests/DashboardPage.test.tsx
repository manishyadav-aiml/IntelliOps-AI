import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import DashboardPage from '../src/pages/DashboardPage'
import { incidentService } from '../src/services/incidentService'
import { dashboardService } from '../src/services/knowledgeService'

vi.mock('recharts', () => {
  const Box = ({ children }: { children?: unknown }) => <div data-testid="chart">{children as never}</div>
  return { ResponsiveContainer: Box, LineChart: Box, BarChart: Box, PieChart: Box, Pie: Box, Bar: Box, Line: Box, Cell: Box, CartesianGrid: Box, XAxis: Box, YAxis: Box, Tooltip: Box }
})
vi.mock('../src/services/knowledgeService', () => ({ dashboardService: { summary: vi.fn(), trends: vi.fn(), services: vi.fn() } }))
vi.mock('../src/services/incidentService', () => ({ incidentService: { list: vi.fn() } }))

const summary = (over: object = {}) => ({
  total_logs_processed: 0, uploads_total: 0, active_incidents: 0, critical_incidents: 0, anomalies_detected: 0,
  services_monitored: 0, resolved_incidents: 0, avg_time_to_acknowledge_seconds: null, avg_time_to_resolve_seconds: null, ...over,
})
const trends = (over: object = {}) => ({
  bucket: 'hour', error_frequency: [], anomaly_trend: [], resolution_trend: [], severity_distribution: [], top_templates: [], truncated: false, ...over,
})
const renderPage = () => render(<MemoryRouter><DashboardPage /></MemoryRouter>)

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(dashboardService.services).mockResolvedValue([])
    vi.mocked(incidentService.list).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 10 } as never)
  })

  it('shows empty states and n/a, never invented numbers, for a new user', async () => {
    vi.mocked(dashboardService.summary).mockResolvedValue(summary() as never)
    vi.mocked(dashboardService.trends).mockResolvedValue(trends() as never)
    renderPage()
    expect(await screen.findByText(/No data yet/)).toBeInTheDocument()
    expect(screen.getAllByText('n/a').length).toBe(2)
    expect(screen.getByText('No incidents yet.')).toBeInTheDocument()
  })

  it('renders metrics and recurring templates from the backend', async () => {
    vi.mocked(dashboardService.summary).mockResolvedValue(summary({ uploads_total: 2, total_logs_processed: 1234, active_incidents: 3, avg_time_to_resolve_seconds: 600 }) as never)
    vi.mocked(dashboardService.trends).mockResolvedValue(trends({ top_templates: [{ name: 'Payment <*> failed', count: 12 }] }) as never)
    renderPage()
    expect(await screen.findByText('1234')).toBeInTheDocument()
    expect(screen.getByText('10 min')).toBeInTheDocument()
    expect(screen.getByText('Payment <*> failed')).toBeInTheDocument()
  })

  it('shows an error state when the API fails', async () => {
    vi.mocked(dashboardService.summary).mockRejectedValue(new Error('down'))
    vi.mocked(dashboardService.trends).mockRejectedValue(new Error('down'))
    renderPage()
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })
})

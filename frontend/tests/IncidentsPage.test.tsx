import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { ToastProvider } from '../src/components/common/Toast'
import IncidentsPage from '../src/pages/IncidentsPage'
import { incidentService } from '../src/services/incidentService'

vi.mock('../src/services/incidentService', () => ({
  incidentService: {
    list: vi.fn(),
    create: vi.fn(),
  },
}))

const incident = (over: object) => ({
  id: 1,
  public_id: 'INC-1001',
  title: 'Payment failures',
  description: '',
  service: 'payment',
  severity: 'P1',
  severity_label: 'CRITICAL',
  severity_reasons: [],
  status: 'OPEN',
  services: [],
  upload_id: null,
  detection_time: '2026-03-01T10:00:00Z',
  first_occurrence: null,
  last_occurrence: null,
  assigned_user_id: null,
  assigned_to: null,
  resolution_notes: null,
  acknowledged_at: null,
  resolved_at: null,
  created_at: '',
  updated_at: '',
  anomaly_summary: null,
  ...over,
})

const page = (items: object[]) => ({
  items,
  total: items.length,
  page: 1,
  page_size: 10,
})

const renderPage = () =>
  render(
    <MemoryRouter>
      <ToastProvider>
        <IncidentsPage />
      </ToastProvider>
    </MemoryRouter>,
  )

describe('IncidentsPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('lists incidents with severity and status and links to details', async () => {
    vi.mocked(incidentService.list).mockResolvedValue(
      page([incident({})]) as never,
    )

    renderPage()

    expect(
      await screen.findByRole('link', {
        name: 'INC-1001 Payment failures',
      }),
    ).toHaveAttribute('href', '/incidents/1')

    expect(screen.getByText('P1 CRITICAL')).toBeInTheDocument()

    // Target the status badge, not the OPEN option in the filter dropdown.
    expect(
      screen.getByText('OPEN', { selector: 'span' }),
    ).toBeInTheDocument()
  })

  it('shows an empty state', async () => {
    vi.mocked(incidentService.list).mockResolvedValue(
      page([]) as never,
    )

    renderPage()

    expect(
      await screen.findByText(/No incidents match/),
    ).toBeInTheDocument()
  })

  it('shows an error state when loading fails', async () => {
    vi.mocked(incidentService.list).mockRejectedValue(
      new Error('boom'),
    )

    renderPage()

    expect(
      await screen.findByRole('alert'),
    ).toBeInTheDocument()
  })

  it('passes filters to the service', async () => {
    vi.mocked(incidentService.list).mockResolvedValue(
      page([]) as never,
    )

    renderPage()

    await userEvent.selectOptions(
      await screen.findByLabelText('Filter by severity'),
      'P1',
    )

    expect(incidentService.list).toHaveBeenLastCalledWith(
      expect.objectContaining({
        severity: 'P1',
        page: 1,
      }),
    )
  })
})
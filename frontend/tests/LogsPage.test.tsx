import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import LogsPage from '../src/pages/LogsPage'
import { logService } from '../src/services/logService'

vi.mock('../src/services/logService', () => ({
  logService: { list: vi.fn(), remove: vi.fn(), retry: vi.fn(), upload: vi.fn() },
}))

const upload = (over: object) => ({
  id: 1, filename: 'app.log', extension: '.log', size_bytes: 2048, status: 'COMPLETED', total_lines: 10,
  processed_lines: 10, entry_count: 10, error_message: null, parse_stats: null, parser_used: 'regex',
  created_at: '2026-03-01T10:00:00Z', started_at: null, completed_at: null, ...over,
})
const page = (items: object[]) => ({ items, total: items.length, page: 1, page_size: 10 })
const renderPage = () => render(<MemoryRouter><LogsPage /></MemoryRouter>)

describe('LogsPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows an empty state when there are no uploads', async () => {
    vi.mocked(logService.list).mockResolvedValue(page([]) as never)
    renderPage()
    expect(await screen.findByText(/No log files yet/)).toBeInTheDocument()
  })

  it('lists files, linking only completed ones to their detail page', async () => {
    vi.mocked(logService.list).mockResolvedValue(
      page([upload({}), upload({ id: 2, filename: 'bad.log', status: 'FAILED', error_message: 'No log lines were found' })]) as never,
    )
    renderPage()
    expect(await screen.findByRole('link', { name: 'app.log' })).toHaveAttribute('href', '/logs/1')
    expect(screen.queryByRole('link', { name: 'bad.log' })).not.toBeInTheDocument()
    expect(screen.getByText('No log lines were found')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })

  it('shows an error state when loading fails', async () => {
    vi.mocked(logService.list).mockRejectedValue(new Error('boom'))
    renderPage()
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })

  it('asks for confirmation before deleting', async () => {
    vi.mocked(logService.list).mockResolvedValue(page([upload({})]) as never)
    vi.mocked(logService.remove).mockResolvedValue(undefined)
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Delete app.log' }))
    expect(logService.remove).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }))
    expect(logService.remove).toHaveBeenCalledWith(1)
  })
})

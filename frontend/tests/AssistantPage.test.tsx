import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AssistantPage from '../src/pages/AssistantPage'
import { ragService } from '../src/services/knowledgeService'

vi.mock('../src/services/knowledgeService', () => ({ ragService: { query: vi.fn() } }))

const citation = { label: 'C1', document_id: 1, document_name: 'payment_service_runbook.md', page_number: 2, chunk_id: 'c0003', snippet: 'Check gateway reachability', score: 0.62 }

describe('AssistantPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows the answer and a source panel with real document, page and chunk', async () => {
    vi.mocked(ragService.query).mockResolvedValue({ answer: 'Check the gateway.', sufficient: true, llm_used: true, citations: [citation], notice: null })
    render(<AssistantPage />)
    await userEvent.type(screen.getByLabelText('Question'), 'why do payments time out?')
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }))
    expect(await screen.findByText('Check the gateway.')).toBeInTheDocument()
    const sources = screen.getByLabelText('Sources')
    expect(sources).toHaveTextContent('payment_service_runbook.md, page 2')
    expect(sources).toHaveTextContent('chunk c0003')
  })

  it('tells the user when the documentation is insufficient', async () => {
    vi.mocked(ragService.query).mockResolvedValue({ answer: 'The uploaded documentation does not provide a sufficient answer to this question.', sufficient: false, llm_used: false, citations: [], notice: null })
    render(<AssistantPage />)
    await userEvent.type(screen.getByLabelText('Question'), 'bake bread?')
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }))
    expect(await screen.findByText(/does not provide a sufficient answer/)).toBeInTheDocument()
  })

  it('shows an error when the request fails', async () => {
    vi.mocked(ragService.query).mockRejectedValue(new Error('boom'))
    render(<AssistantPage />)
    await userEvent.type(screen.getByLabelText('Question'), 'anything')
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }))
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })

  it('ignores empty questions', async () => {
    render(<AssistantPage />)
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }))
    expect(ragService.query).not.toHaveBeenCalled()
  })
})

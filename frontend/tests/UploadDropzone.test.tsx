import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import UploadDropzone from '../src/components/logs/UploadDropzone'
import { logService } from '../src/services/logService'

vi.mock('../src/services/logService', () => ({ logService: { upload: vi.fn() } }))

const fakeUpload = { id: 1, filename: 'a.log', status: 'PENDING' }

describe('UploadDropzone', () => {
  beforeEach(() => vi.clearAllMocks())

  it('uploads a valid file and reports the result', async () => {
    vi.mocked(logService.upload).mockResolvedValue(fakeUpload as never)
    const onUploaded = vi.fn()
    render(<UploadDropzone onUploaded={onUploaded} />)
    const file = new File(['2026-03-01 10:00:00 INFO [api] ok\n'], 'a.log', { type: 'text/plain' })
    await userEvent.upload(screen.getByLabelText('Log file'), file)
    await waitFor(() => expect(onUploaded).toHaveBeenCalledWith(fakeUpload))
  })

  it('rejects unsupported extensions without calling the API', async () => {
    render(<UploadDropzone onUploaded={vi.fn()} />)
    const input = screen.getByLabelText('Log file') as HTMLInputElement
    const file = new File(['x'], 'malware.exe')
    // fireEvent-style change bypasses the accept attribute filter that userEvent applies
    await userEvent.upload(input, file, { applyAccept: false })
    expect(await screen.findByRole('alert')).toHaveTextContent('Only .log, .txt and .csv')
    expect(logService.upload).not.toHaveBeenCalled()
  })

  it('shows the server error when the upload fails', async () => {
    vi.mocked(logService.upload).mockRejectedValue(new Error('network'))
    render(<UploadDropzone onUploaded={vi.fn()} />)
    await userEvent.upload(screen.getByLabelText('Log file'), new File(['hello'], 'a.log'))
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })
})

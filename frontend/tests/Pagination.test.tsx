import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Pagination from '../src/components/common/Pagination'

describe('Pagination', () => {
  it('disables Previous on the first page and navigates forward', async () => {
    const onChange = vi.fn()
    render(<Pagination page={1} pageSize={10} total={25} onChange={onChange} />)
    expect(screen.getByText('Page 1 of 3 (25 total)')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(onChange).toHaveBeenCalledWith(2)
  })

  it('disables Next on the last page', () => {
    render(<Pagination page={3} pageSize={10} total={25} onChange={() => {}} />)
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
  })
})

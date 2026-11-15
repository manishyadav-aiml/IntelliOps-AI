import { render, screen } from '@testing-library/react'
import RcaPanel from '../src/components/incidents/RcaPanel'

describe('RcaPanel', () => {
  it('shows the findings together with the not-causation disclaimer', () => {
    render(<RcaPanel summary={{ rca: { summary: ["Errors began earliest in service 'db'."], disclaimer: 'Temporal evidence only.', earliest_error_services: [{ service: 'db', error_count: 12, seconds_after_first: 0 }] } }} />)
    expect(screen.getByText("Errors began earliest in service 'db'.")).toBeInTheDocument()
    expect(screen.getByText('Temporal evidence only.')).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
  })

  it('shows an empty state instead of inventing evidence', () => {
    render(<RcaPanel summary={null} />)
    expect(screen.getByText(/No log-based evidence/)).toBeInTheDocument()
  })
})

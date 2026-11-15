import { render, screen } from '@testing-library/react'
import ChartCard from '../src/components/common/ChartCard'
import EmptyState from '../src/components/common/EmptyState'
import MetricCard from '../src/components/common/MetricCard'
import SeverityBadge from '../src/components/common/SeverityBadge'
import StatusBadge from '../src/components/common/StatusBadge'
import { formatBytes, validateLogFile } from '../src/utils/format'
import { validatePassword } from '../src/utils/validation'

describe('reusable components', () => {
  it('MetricCard shows n/a for missing values instead of inventing a number', () => {
    render(<MetricCard label="Avg. time to resolve" value={null} />)
    expect(screen.getByText('n/a')).toBeInTheDocument()
  })

  it('SeverityBadge shows the priority and its label', () => {
    render(<SeverityBadge value="P1" />)
    expect(screen.getByText('P1 CRITICAL')).toBeInTheDocument()
  })

  it('StatusBadge renders any status text', () => {
    render(<StatusBadge value="INVESTIGATING" />)
    expect(screen.getByText('INVESTIGATING')).toBeInTheDocument()
  })

  it('ChartCard shows an empty state instead of an empty chart', () => {
    render(<ChartCard title="Errors" empty emptyMessage="Nothing here"><div>chart</div></ChartCard>)
    expect(screen.getByText('Nothing here')).toBeInTheDocument()
    expect(screen.queryByText('chart')).not.toBeInTheDocument()
  })

  it('EmptyState renders its message', () => {
    render(<EmptyState message="No incidents yet." />)
    expect(screen.getByText('No incidents yet.')).toBeInTheDocument()
  })
})

describe('utilities', () => {
  it('validateLogFile checks extension, emptiness and size', () => {
    expect(validateLogFile(new File(['x'], 'a.exe'))).toMatch(/Only/)
    expect(validateLogFile(new File([], 'a.log'))).toMatch(/empty/)
    expect(validateLogFile(new File(['x'], 'a.LOG'))).toBeNull()
  })

  it('validatePassword mirrors the backend rules', () => {
    expect(validatePassword('short1')).not.toBeNull()
    expect(validatePassword('onlyletters')).not.toBeNull()
    expect(validatePassword('Str0ngPassw0rd')).toBeNull()
  })

  it('formatBytes', () => {
    expect(formatBytes(512)).toBe('512 B')
    expect(formatBytes(2048)).toBe('2.0 KB')
  })
})

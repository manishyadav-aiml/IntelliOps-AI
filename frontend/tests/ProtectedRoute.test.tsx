import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AuthContext } from '../src/context/AuthContext'
import type { AuthContextValue } from '../src/context/AuthContext'
import ProtectedRoute from '../src/routes/ProtectedRoute'

const noop = async () => {}
const baseValue: AuthContextValue = { user: null, loading: false, login: noop, register: noop, logout: noop }

function renderAt(value: AuthContextValue) {
  return render(
    <AuthContext.Provider value={value}>
      <MemoryRouter initialEntries={['/secret']}>
        <Routes>
          <Route path="/login" element={<div>Login screen</div>} />
          <Route
            path="/secret"
            element={
              <ProtectedRoute>
                <div>Secret content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  )
}

describe('ProtectedRoute', () => {
  it('redirects anonymous users to /login', () => {
    renderAt(baseValue)
    expect(screen.getByText('Login screen')).toBeInTheDocument()
    expect(screen.queryByText('Secret content')).not.toBeInTheDocument()
  })

  it('renders children for an authenticated user', () => {
    const user = { id: 1, email: 'a@b.com', full_name: 'Ada', role: 'engineer', is_active: true, created_at: '' }
    renderAt({ ...baseValue, user })
    expect(screen.getByText('Secret content')).toBeInTheDocument()
  })

  it('shows a loading state while the session is being restored', () => {
    renderAt({ ...baseValue, loading: true })
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.queryByText('Login screen')).not.toBeInTheDocument()
  })
})

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { AuthContext } from '../src/context/AuthContext'
import type { AuthContextValue } from '../src/context/AuthContext'
import LoginPage from '../src/pages/LoginPage'

function renderLogin(login: AuthContextValue['login']) {
  const value: AuthContextValue = {
    user: null,
    loading: false,
    login,
    register: async () => {},
    logout: async () => {},
  }
  return render(
    <AuthContext.Provider value={value}>
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    </AuthContext.Provider>,
  )
}

describe('LoginPage', () => {
  it('submits the entered credentials', async () => {
    const login = vi.fn().mockResolvedValue(undefined)
    renderLogin(login)
    await userEvent.type(screen.getByLabelText('Email'), 'ada@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'Str0ngPassw0rd')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    await waitFor(() => expect(login).toHaveBeenCalledWith('ada@example.com', 'Str0ngPassw0rd'))
  })

  it('shows an error when login fails', async () => {
    renderLogin(vi.fn().mockRejectedValue(new Error('boom')))
    await userEvent.type(screen.getByLabelText('Email'), 'ada@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'whatever1')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })

  it('links to registration', () => {
    renderLogin(vi.fn())
    expect(screen.getByRole('link', { name: 'Register' })).toHaveAttribute('href', '/register')
  })
})

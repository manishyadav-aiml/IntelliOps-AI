import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import AuthCard from '../components/common/AuthCard'
import ErrorMessage from '../components/common/ErrorMessage'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../utils/errors'
import { validatePassword } from '../utils/validation'

export default function RegisterPage() {
  const { user, register } = useAuth()
  const navigate = useNavigate()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate to="/" replace />

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    const passwordProblem = validatePassword(password)
    if (passwordProblem) return setError(passwordProblem)
    if (password !== confirm) return setError('Passwords do not match.')
    setSubmitting(true)
    try {
      await register({ email, full_name: fullName, password })
      navigate('/', { replace: true })
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  const field = (id: string, label: string, type: string, value: string, set: (v: string) => void, autoComplete: string) => (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-medium">
        {label}
      </label>
      <input
        id={id}
        type={type}
        required
        autoComplete={autoComplete}
        value={value}
        onChange={(e) => set(e.target.value)}
        className="w-full rounded-md border px-3 py-2"
      />
    </div>
  )

  return (
    <AuthCard title="Create your account">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorMessage message={error} />}
        {field('full_name', 'Full name', 'text', fullName, setFullName, 'name')}
        {field('email', 'Email', 'email', email, setEmail, 'email')}
        {field('password', 'Password', 'password', password, setPassword, 'new-password')}
        {field('confirm', 'Confirm password', 'password', confirm, setConfirm, 'new-password')}
        <p className="text-xs text-slate-500">At least 8 characters, with a letter and a digit.</p>
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-slate-600">
        Already registered?{' '}
        <Link to="/login" className="text-blue-600 hover:underline">
          Sign in
        </Link>
      </p>
    </AuthCard>
  )
}

import { LogOut, User as UserIcon } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

export default function Navbar({ onLogout }: { onLogout: () => void }) {
  const { user } = useAuth()
  return (
    <header className="flex items-center justify-end gap-4 border-b bg-white px-6 py-3">
      <Link to="/profile" className="flex items-center gap-1 text-sm text-slate-600 hover:underline">
        <UserIcon className="h-4 w-4" aria-hidden="true" />
        {user?.full_name}
      </Link>
      <button type="button" onClick={onLogout} className="flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm hover:bg-slate-100">
        <LogOut className="h-4 w-4" aria-hidden="true" />
        Log out
      </button>
    </header>
  )
}

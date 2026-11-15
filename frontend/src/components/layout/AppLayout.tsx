import { Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import Navbar from './Navbar'
import Sidebar from './Sidebar'

export default function AppLayout() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <Sidebar />
      <div className="min-w-0 flex-1">
        <Navbar onLogout={handleLogout} />
        <main className="p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

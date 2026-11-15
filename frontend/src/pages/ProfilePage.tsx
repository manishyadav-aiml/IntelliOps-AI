import { useAuth } from '../context/AuthContext'
import { formatDate } from '../utils/format'

export default function ProfilePage() {
  const { user } = useAuth()
  if (!user) return null
  const rows: [string, string][] = [['Name', user.full_name], ['Email', user.email], ['Role', user.role], ['Member since', formatDate(user.created_at)]]
  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">Profile</h1>
      <dl className="max-w-xl divide-y rounded-lg border bg-white text-sm">
        {rows.map(([k, v]) => <div key={k} className="flex justify-between p-3"><dt className="text-slate-500">{k}</dt><dd className="font-medium">{v}</dd></div>)}
      </dl>
    </section>
  )
}

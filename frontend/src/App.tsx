import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'

import AppLayout from './components/layout/AppLayout'
import ProtectedRoute from './routes/ProtectedRoute'

// Authentication
const LoginPage = lazy(() => import('./pages/LoginPage'))
const RegisterPage = lazy(() => import('./pages/RegisterPage'))

// Dashboard and monitoring
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const LogsPage = lazy(() => import('./pages/LogsPage'))
const LogDetailPage = lazy(() => import('./pages/LogDetailPage'))
const AnomaliesPage = lazy(() => import('./pages/AnomaliesPage'))

// Incident management
const IncidentsPage = lazy(() => import('./pages/IncidentsPage'))
const IncidentDetailPage = lazy(() => import('./pages/IncidentDetailPage'))

// AI and documents
const DocumentsPage = lazy(() => import('./pages/DocumentsPage'))
const AssistantPage = lazy(() => import('./pages/AssistantPage'))

// Other pages
const ReportsPage = lazy(() => import('./pages/ReportsPage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))
const ProfilePage = lazy(() => import('./pages/ProfilePage'))

function PageLoader() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex min-h-[60vh] items-center justify-center"
    >
      <span className="text-sm text-gray-500">
        Loading page...
      </span>
    </div>
  )
}

export default function App() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        <Route
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<DashboardPage />} />
          <Route path="/logs" element={<LogsPage />} />
          <Route path="/logs/:id" element={<LogDetailPage />} />
          <Route path="/anomalies" element={<AnomaliesPage />} />
          <Route path="/incidents" element={<IncidentsPage />} />
          <Route path="/incidents/:id" element={<IncidentDetailPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/assistant" element={<AssistantPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import DemoLayout from './DemoLayout'

const DemoDashboard = lazy(() => import('./DemoDashboard'))
const DemoLogs = lazy(() => import('./DemoLogs'))
const DemoAnomalies = lazy(() => import('./DemoAnomalies'))
const DemoIncidents = lazy(() => import('./DemoIncidents'))
const DemoDocuments = lazy(() => import('./DemoDocuments'))
const DemoAssistant = lazy(() => import('./DemoAssistant'))
const DemoReports = lazy(() => import('./DemoReports'))
const DemoSettings = lazy(() => import('./DemoSettings'))

export default function DemoApp() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-slate-50">
          <p className="text-sm font-medium text-slate-500">
            Loading workspace...
          </p>
        </div>
      }
    >
      <Routes>
        <Route element={<DemoLayout />}>
          <Route path="/" element={<DemoDashboard />} />
          <Route path="/logs" element={<DemoLogs />} />
          <Route path="/anomalies" element={<DemoAnomalies />} />
          <Route path="/incidents" element={<DemoIncidents />} />
          <Route path="/documents" element={<DemoDocuments />} />
          <Route path="/assistant" element={<DemoAssistant />} />
          <Route path="/reports" element={<DemoReports />} />
          <Route path="/settings" element={<DemoSettings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Suspense>
  )
}
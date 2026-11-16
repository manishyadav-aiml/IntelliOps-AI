import { Navigate, Route, Routes } from 'react-router-dom'
import DemoLayout from './DemoLayout'
import DemoDashboard from './DemoDashboard'
import DemoLogs from './DemoLogs'
import DemoAnomalies from './DemoAnomalies'
import DemoIncidents from './DemoIncidents'
import DemoDocuments from './DemoDocuments'
import DemoAssistant from './DemoAssistant'
import DemoReports from './DemoReports'
import DemoSettings from './DemoSettings'

export default function DemoApp() {
  return (
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
  )
}

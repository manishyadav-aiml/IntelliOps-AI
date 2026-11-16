export const demoMetrics = [
  { label: 'Total Log Events', value: '24,850', hint: 'Illustrative 24-hour volume' },
  { label: 'Anomalies Detected', value: '127', hint: 'Sample anomaly records' },
  { label: 'Open Incidents', value: '18', hint: 'Illustrative incident count' },
  { label: 'Services Monitored', value: '12', hint: 'Example monitored services' },
]

export const demoTrendData = [
  { time: '00:00', events: 820, anomalies: 12 },
  { time: '04:00', events: 640, anomalies: 8 },
  { time: '08:00', events: 1450, anomalies: 19 },
  { time: '12:00', events: 1820, anomalies: 25 },
  { time: '16:00', events: 1650, anomalies: 21 },
  { time: '20:00', events: 2100, anomalies: 32 },
]

export const demoLogs = [
  { id: 'LOG-1001', service: 'payment-service', level: 'ERROR', message: 'Payment gateway timeout', time: '2026-11-16 11:42:18' },
  { id: 'LOG-1002', service: 'auth-service', level: 'WARNING', message: 'Repeated authentication failures', time: '2026-11-16 11:39:05' },
  { id: 'LOG-1003', service: 'order-service', level: 'INFO', message: 'Order processed successfully', time: '2026-11-16 11:35:42' },
  { id: 'LOG-1004', service: 'inventory-service', level: 'CRITICAL', message: 'Database connection pool exhausted', time: '2026-11-16 11:31:11' },
  { id: 'LOG-1005', service: 'notification-service', level: 'DEBUG', message: 'Notification queue checked', time: '2026-11-16 11:27:50' },
]

export const demoIncidents = [
  { id: 'INC-2041', title: 'Payment gateway latency spike', service: 'payment-service', severity: 'P1', status: 'INVESTIGATING', time: '2026-11-16 11:42' },
  { id: 'INC-2040', title: 'Database connection pool exhaustion', service: 'inventory-service', severity: 'P1', status: 'OPEN', time: '2026-11-16 11:31' },
  { id: 'INC-2039', title: 'Authentication failure increase', service: 'auth-service', severity: 'P2', status: 'MITIGATED', time: '2026-11-16 10:58' },
  { id: 'INC-2038', title: 'Notification delivery delays', service: 'notification-service', severity: 'P3', status: 'RESOLVED', time: '2026-11-16 09:45' },
]

export const demoAnomalies = [
  { id: 'ANM-301', service: 'payment-service', description: 'Unusual increase in request latency', score: '98.2%', severity: 'P1' },
  { id: 'ANM-302', service: 'inventory-service', description: 'Abnormal database connection usage', score: '94.7%', severity: 'P1' },
  { id: 'ANM-303', service: 'auth-service', description: 'Higher-than-normal failed login rate', score: '87.5%', severity: 'P2' },
  { id: 'ANM-304', service: 'notification-service', description: 'Unexpected queue growth', score: '76.3%', severity: 'P3' },
]

export const demoDocuments = [
  { id: 'DOC-101', name: 'Production Incident Response Guide.pdf', category: 'Runbook', status: 'Indexed' },
  { id: 'DOC-102', name: 'Payment Service Architecture.pdf', category: 'Architecture', status: 'Indexed' },
  { id: 'DOC-103', name: 'Database Troubleshooting Manual.pdf', category: 'Technical Guide', status: 'Indexed' },
]

export const demoReports = [
  { id: 'RPT-501', name: 'Daily Operations Summary', period: 'November 16, 2026', status: 'Sample' },
  { id: 'RPT-502', name: 'Incident Analysis Report', period: 'November 15, 2026', status: 'Sample' },
  { id: 'RPT-503', name: 'Service Health Overview', period: 'November 14, 2026', status: 'Sample' },
]

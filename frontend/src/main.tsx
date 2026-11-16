import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, HashRouter } from 'react-router-dom'
import App from './App'
import DemoApp from './demo/DemoApp'
import { ToastProvider } from './components/common/Toast'
import { AuthProvider } from './context/AuthContext'
import './index.css'

const isDemo = import.meta.env.MODE === 'demo'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {isDemo ? (
      <HashRouter>
        <ToastProvider>
          <DemoApp />
        </ToastProvider>
      </HashRouter>
    ) : (
      <BrowserRouter basename={import.meta.env.BASE_URL}>
        <AuthProvider>
          <ToastProvider>
            <App />
          </ToastProvider>
        </AuthProvider>
      </BrowserRouter>
    )}
  </StrictMode>,
)

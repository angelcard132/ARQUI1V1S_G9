import { InvernaderoProvider } from './context/InvernaderoContext'
import Sidebar   from './components/Sidebar'
import Topbar    from './components/Topbar'
import Dashboard from './pages/Dashboard'

export default function App() {
  return (
    <InvernaderoProvider>
      <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
        <Sidebar />
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <Topbar />
          <main style={{ flex: 1, overflowY: 'auto', padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 16 }}>
            <Dashboard />
          </main>
        </div>
      </div>
    </InvernaderoProvider>
  )
}
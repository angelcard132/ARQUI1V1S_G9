import { useInvernadero } from '../context/InvernaderoContext'
import { useClock } from '../hooks/useClock'

export default function Topbar() {
  const { state, setModo } = useInvernadero()
  const { time, date }     = useClock()

  return (
    <header style={styles.topbar}>
      <div style={styles.left}>
        <h1 style={styles.title}>Panel de monitoreo</h1>
        <span style={styles.sub}>MQTT | MONGO DB | ARM64 | {BASE_TOPIC}</span>
      </div>

      <div style={styles.right}>
        {/* Toggle modo */}
        <div style={styles.modeWrap}>
          <button
            style={{ ...styles.modeBtn, ...(state.modo === 'AUTOMATICO' ? styles.modeBtnActive : {}) }}
            onClick={() => setModo('AUTOMATICO')}
          >
            <i className="ti ti-robot" style={{ fontSize: 13 }} />
            Auto
          </button>
          <button
            style={{ ...styles.modeBtn, ...(state.modo === 'MANUAL' ? styles.modeBtnManual : {}) }}
            onClick={() => setModo('MANUAL')}
          >
            <i className="ti ti-hand-click" style={{ fontSize: 13 }} />
            Manual
          </button>
        </div>

        {/* Ultima lectura */}
        {state.ultimaLectura && (
          <div style={styles.lastRead}>
            <i className="ti ti-clock" style={{ fontSize: 12, color: '#8a9280' }} />
            <span style={styles.lastReadText}>Ultima: {state.ultimaLectura}</span>
          </div>
        )}

        {/* Reloj */}
        <div style={styles.clock}>
          <div style={styles.clockTime}>{time}</div>
          <div style={styles.clockDate}>{date}</div>
        </div>
      </div>
    </header>
  )
}

const BASE_TOPIC = 'Vacaciones 2026 | Primer Semestre'

const styles = {
  topbar: {
    height: 56,
    background: '#faf8f2',
    borderBottom: '1px solid rgba(26,28,22,0.08)',
    padding: '0 20px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexShrink: 0,
    gap: 12,
  },
  left: {
    display: 'flex',
    flexDirection: 'column',
    gap: 1,
  },
  title: {
    fontFamily: "'Fraunces', Georgia, serif",
    fontSize: 16,
    fontWeight: 500,
    color: '#1a1c16',
    letterSpacing: '-0.02em',
  },
  sub: {
    fontSize: 10,
    color: '#8a9280',
    fontFamily: "'DM Mono', monospace",
  },
  right: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
  },
  modeWrap: {
    display: 'flex',
    background: '#ede8dc',
    borderRadius: 8,
    padding: 2,
    gap: 2,
  },
  modeBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 5,
    padding: '5px 12px',
    borderRadius: 6,
    border: 'none',
    background: 'transparent',
    cursor: 'pointer',
    fontSize: 12,
    color: '#4a5240',
    fontFamily: "'DM Sans', system-ui, sans-serif",
    transition: 'all 0.15s',
  },
  modeBtnActive: {
    background: '#ffffff',
    color: '#3a6b1a',
    fontWeight: 500,
    boxShadow: '0 1px 3px rgba(26,28,22,0.10)',
  },
  modeBtnManual: {
    background: '#ffffff',
    color: '#b86b0a',
    fontWeight: 500,
    boxShadow: '0 1px 3px rgba(26,28,22,0.10)',
  },
  lastRead: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
  },
  lastReadText: {
    fontSize: 11,
    color: '#8a9280',
    fontFamily: "'DM Mono', monospace",
  },
  clock: {
    textAlign: 'right',
    borderLeft: '1px solid rgba(26,28,22,0.08)',
    paddingLeft: 12,
  },
  clockTime: {
    fontFamily: "'DM Mono', monospace",
    fontSize: 15,
    fontWeight: 500,
    color: '#1a1c16',
    letterSpacing: '0.04em',
  },
  clockDate: {
    fontSize: 10,
    color: '#8a9280',
  },
}
import { useInvernadero } from '../context/InvernaderoContext'
import { THRESHOLDS } from '../lib/config'

export default function AreaCard({ area }) {
  const { state, publicar } = useInvernadero()
  const n        = area === 1 ? 'suelo1' : 'suelo2'
  const riegoKey = area === 1 ? 'riego1' : 'riego2'
  const valor    = state[n]
  const on       = state[riegoKey]

  const pct    = valor !== null ? Math.min(Math.max(valor, 0), 100) : 0
  const estado = valor === null ? '—'
    : valor < THRESHOLDS.SUELO_SECO ? 'SECO'
    : valor > THRESHOLDS.SUELO_SAT  ? 'SATURADO'
    : 'NORMAL'

  const barColor = estado === 'SECO'     ? '#b86b0a'
                 : estado === 'SATURADO' ? '#9b2020'
                 : '#3a6b1a'

  const accentColor = area === 1 ? '#3a6b1a' : '#0e6e56'
  const accentBg    = area === 1 ? '#d6e8c4'  : '#c4e0d8'

  return (
    <div style={styles.card}>
      {/* Header */}
      <div style={{ ...styles.header, background: accentBg, borderBottomColor: accentColor + '30' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <i className="ti ti-plant" style={{ fontSize: 14, color: accentColor }} />
          <span style={{ ...styles.headerTitle, color: accentColor }}>Area {area}</span>
        </div>
        <span style={{ ...styles.headerBadge, background: accentColor + '20', color: accentColor }}>
          FC-28
        </span>
      </div>

      {/* Body */}
      <div style={styles.body}>
        <div style={styles.barLabel}>
          <span style={styles.barLabelText}>Humedad de suelo</span>
          <span style={{ ...styles.barEstado, color: barColor }}>{estado}</span>
        </div>

        {/* Barra */}
        <div style={styles.barTrack}>
          <div style={{ ...styles.barFill, width: `${pct}%`, background: barColor, transition: 'width 0.6s ease, background 0.3s' }} />
        </div>

        <div style={styles.barVal}>
          <span style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 22, fontWeight: 500, color: barColor }}>
            {valor !== null ? valor : '—'}
          </span>
          {valor !== null && <span style={{ fontSize: 12, color: '#8a9280', marginLeft: 2 }}>%</span>}
        </div>

        {/* Accion */}
        <div style={styles.actions}>
          <div style={styles.chip}>
            <span style={{ ...styles.chipDot, background: on ? '#5a9a2a' : '#8a9280', animation: on ? 'pulse-dot 1.5s infinite' : 'none' }} />
            <span style={{ fontSize: 11, color: on ? '#3a6b1a' : '#8a9280' }}>
              {on ? 'Regando...' : 'Sin riego'}
            </span>
          </div>

          <button
            style={{ ...styles.riegoBtn, ...(on ? styles.riegoBtnOff : styles.riegoBtnOn) }}
            onClick={() => publicar(area === 1 ? 'riego_area1' : 'riego_area2', on ? 'OFF' : 'ON')}
            onMouseEnter={e => e.currentTarget.style.opacity = '0.75'}
            onMouseLeave={e => e.currentTarget.style.opacity = '1'}
          >
            <i className={`ti ${on ? 'ti-player-stop' : 'ti-droplet'}`} style={{ fontSize: 12 }} />
            {on ? 'Detener' : 'Regar'}
          </button>
        </div>
      </div>
    </div>
  )
}

const styles = {
  card: {
    border: '1px solid rgba(26,28,22,0.09)',
    borderRadius: 10,
    overflow: 'hidden',
  },
  header: {
    padding: '9px 12px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderBottom: '1px solid',
  },
  headerTitle: {
    fontSize: 13,
    fontWeight: 500,
    fontFamily: "'DM Sans', system-ui, sans-serif",
  },
  headerBadge: {
    fontSize: 10,
    padding: '2px 7px',
    borderRadius: 20,
    fontFamily: "'DM Mono', monospace",
  },
  body: {
    padding: '12px 12px',
    background: '#405740',
  },
  barLabel: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  barLabelText: {
    fontSize: 11,
    color: '#8a9280',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  barEstado: {
    fontSize: 11,
    fontWeight: 500,
    fontFamily: "'DM Mono', monospace",
  },
  barTrack: {
    height: 6,
    background: '#ede8dc',
    borderRadius: 3,
    overflow: 'hidden',
    marginBottom: 6,
  },
  barFill: {
    height: '100%',
    borderRadius: 3,
  },
  barVal: {
    marginBottom: 10,
  },
  actions: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  chip: {
    display: 'flex',
    alignItems: 'center',
    gap: 5,
  },
  chipDot: {
    width: 6, height: 6,
    borderRadius: '50%',
  },
  riegoBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 5,
    padding: '5px 12px',
    borderRadius: 20,
    border: '1px solid',
    background: 'transparent',
    cursor: 'pointer',
    fontSize: 11,
    fontFamily: "'DM Sans', system-ui, sans-serif",
    transition: 'opacity 0.15s',
  },
  riegoBtnOn:  { borderColor: '#3a6b1a', color: '#3a6b1a' },
  riegoBtnOff: { borderColor: '#9b2020', color: '#9b2020' },
}
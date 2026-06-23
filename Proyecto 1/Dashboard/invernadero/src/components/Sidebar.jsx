import { useInvernadero } from '../context/InvernaderoContext'

const NAV = [
  { icon: 'ti-layout-dashboard', label: 'Dashboard',   href: '#dashboard' },
  { icon: 'ti-chart-line',       label: 'Historico',   href: '#historico' },
  { icon: 'ti-droplet',          label: 'Riego',       href: '#riego' },
  { icon: 'ti-adjustments-horizontal', label: 'Actuadores', href: '#actuadores' },
  { icon: 'ti-cpu',              label: 'ARM64',       href: '#arm64' },
  { icon: 'ti-history',          label: 'Eventos',     href: '#eventos' },
  { icon: 'ti-terminal-2',       label: 'Comandos',    href: '#comandos' },
  { icon: 'ti-antenna',          label: 'MQTT',        href: '#mqtt' },
]

const STATE_COLORS = {
  NORMAL:      '#5a9a2a',
  ADVERTENCIA: '#b86b0a',
  RIEGO_ACTIVO:'#0e6e56',
  MODO_MANUAL: '#5a5a3a',
  EMERGENCIA:  '#9b2020',
  OFFLINE:     '#8a9280',
}

export default function Sidebar() {
  const { state } = useInvernadero()
  const color = STATE_COLORS[state.estadoGlobal] || '#5a9a2a'

  return (
    <aside style={styles.sidebar}>

      {/* Logo */}
      <div style={styles.logo}>
        <div>
          <div style={styles.logoName}>Invernadero</div>
          <div style={styles.logoSub}>ARQUI 1 | PRIMER PROYECTO</div>
        </div>
      </div>

      {/* Estado global prominente */}
      <div style={{ ...styles.globalBadge, background: color + '18', borderColor: color + '40' }}>
        <span style={{ ...styles.globalDot, background: color }} />
        <span style={{ ...styles.globalLabel, color }}>{state.estadoGlobal}</span>
      </div>

      {/* Nav */}
      <nav style={styles.nav}>
        {NAV.map(item => (
          <a key={item.href} href={item.href} style={styles.navItem}
            onMouseEnter={e => e.currentTarget.style.background = '#3a6b1a12'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
          >
            <i className={`ti ${item.icon}`} style={styles.navIcon} />
            <span style={styles.navLabel}>{item.label}</span>
          </a>
        ))}
      </nav>

      {/* Footer MQTT */}
      <div style={styles.footer}>
        <span
          style={{
            ...styles.footerDot,
            background: state.mqttConnected ? '#5a9a2a' : '#9b2020',
            boxShadow: state.mqttConnected ? '0 0 6px #5a9a2a88' : 'none',
          }}
        />
        <div>
          <div style={styles.footerTitle}>MQTT</div>
          <div style={styles.footerSub}>{state.mqttStatus}</div>
        </div>
        <div style={styles.footerLecturas}>
          <div style={styles.footerNum}>{state.totalLecturas}</div>
          <div style={styles.footerSub}>lecturas</div>
        </div>
      </div>

    </aside>
  )
}

const styles = {
  sidebar: {
    width: 220,
    minWidth: 220,
    background: '#faf8f2',
    borderRight: '1px solid rgba(26,28,22,0.08)',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  logo: {
    padding: '20px 16px 16px',
    borderBottom: '1px solid rgba(26,28,22,0.07)',
    display: 'flex',
    alignItems: 'center',
    gap: 10,
  },
  logoIcon: {
    width: 36, height: 36,
    background: '#d6e8c4',
    borderRadius: 8,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    flexShrink: 0,
  },
  logoName: {
    fontFamily: "'Fraunces', Georgia, serif",
    fontSize: 14,
    fontWeight: 500,
    color: '#1a1c16',
    letterSpacing: '-0.02em',
  },
  logoSub: {
    fontSize: 11,
    color: '#8a9280',
    fontFamily: "'DM Mono', monospace",
  },
  globalBadge: {
    margin: '12px 14px',
    padding: '8px 12px',
    borderRadius: 8,
    border: '1px solid',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    transition: 'all 0.3s ease',
  },
  globalDot: {
    width: 8, height: 8,
    borderRadius: '50%',
    animation: 'pulse-dot 2s infinite',
    flexShrink: 0,
  },
  globalLabel: {
    fontSize: 12,
    fontFamily: "'DM Mono', monospace",
    fontWeight: 500,
    letterSpacing: '0.04em',
  },
  nav: {
    flex: 1,
    padding: '8px 8px',
    display: 'flex',
    flexDirection: 'column',
    gap: 1,
    overflowY: 'auto',
  },
  navItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 9,
    padding: '8px 10px',
    borderRadius: 6,
    textDecoration: 'none',
    color: '#4a5240',
    fontSize: 13,
    transition: 'background 0.12s',
    fontFamily: "'DM Sans', system-ui, sans-serif",
  },
  navIcon: {
    fontSize: 16,
    color: '#8a9280',
    flexShrink: 0,
  },
  navLabel: {
    fontSize: 13,
  },
  footer: {
    padding: '12px 14px',
    borderTop: '1px solid rgba(26,28,22,0.07)',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  footerDot: {
    width: 8, height: 8,
    borderRadius: '50%',
    flexShrink: 0,
    transition: 'all 0.3s',
  },
  footerTitle: {
    fontSize: 11,
    fontFamily: "'DM Mono', monospace",
    color: '#4a5240',
    fontWeight: 500,
  },
  footerSub: {
    fontSize: 10,
    color: '#8a9280',
  },
  footerLecturas: {
    marginLeft: 'auto',
    textAlign: 'right',
  },
  footerNum: {
    fontSize: 16,
    fontFamily: "'Fraunces', Georgia, serif",
    fontWeight: 500,
    color: '#3a6b1a',
    lineHeight: 1,
  },
}
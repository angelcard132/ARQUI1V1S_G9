export default function ActuadorCard({ icon, label, on, color = '#3a6b1a', onClick, disabled }) {
  const bg    = on ? color + '18' : '#f5f2eb'
  const ic    = on ? color        : '#8a9280'
  const border = on ? color + '35' : 'rgba(26,28,22,0.09)'

  return (
    <button
      style={{ ...styles.card, background: bg, borderColor: border, cursor: disabled ? 'default' : 'pointer' }}
      onClick={disabled ? undefined : onClick}
      onMouseEnter={e => { if (!disabled) e.currentTarget.style.opacity = '0.8' }}
      onMouseLeave={e => e.currentTarget.style.opacity = '1'}
    >
      <div style={{ ...styles.iconWrap, background: ic + '20' }}>
        <i className={`ti ${icon}`} style={{ fontSize: 18, color: ic }} />
      </div>
      <span style={styles.label}>{label}</span>
      <span style={{ ...styles.badge, background: on ? color + '20' : '#ede8dc', color: on ? color : '#8a9280' }}>
        {on ? 'ON' : 'OFF'}
      </span>
    </button>
  )
}

const styles = {
  card: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 7,
    padding: '12px 8px',
    borderRadius: 10,
    border: '1px solid',
    transition: 'opacity 0.15s, background 0.2s, border-color 0.2s',
    fontFamily: "'DM Sans', system-ui, sans-serif",
  },
  iconWrap: {
    width: 36, height: 36,
    borderRadius: '50%',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  label: {
    fontSize: 11,
    color: '#4a5240',
    textAlign: 'center',
    lineHeight: 1.3,
  },
  badge: {
    fontSize: 10,
    padding: '2px 8px',
    borderRadius: 20,
    fontWeight: 500,
    fontFamily: "'DM Mono', monospace",
  },
}
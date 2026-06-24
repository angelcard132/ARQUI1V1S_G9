export default function MetricCard({ icon, label, value, unit, status, statusColor = '#5a9a2a', delay = 0 }) {
  return (
    <div
      className="fade-up"
      style={{ ...styles.card, animationDelay: `${delay}ms` }}
    >
      <div style={styles.header}>
        <i className={`ti ${icon}`} style={styles.icon} />
        <span style={styles.label}>{label}</span>
      </div>
      <div style={styles.valueRow}>
        <span style={styles.value}>
          {value !== null && value !== undefined ? value : '—'}
        </span>
        {unit && <span style={styles.unit}>{unit}</span>}
      </div>
      {status && (
        <div style={{ ...styles.status, color: statusColor }}>
          {status}
        </div>
      )}
    </div>
  )
}

const styles = {
  card: {
    background: '#314432',
    border: '1px solid rgba(26,28,22,0.08)',
    borderRadius: 10,
    padding: '12px 14px',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    marginBottom: 6,
  },
  icon: {
    fontSize: 14,
    color: '#8a9280',
  },
  label: {
    fontSize: 11,
    color: '#8a9280',
    fontFamily: "'DM Sans', system-ui, sans-serif",
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  valueRow: {
    display: 'flex',
    alignItems: 'baseline',
    gap: 3,
  },
  value: {
    fontFamily: "'Fraunces', Georgia, serif",
    fontSize: 28,
    fontWeight: 500,
    color: '#1a1c16',
    lineHeight: 1,
    letterSpacing: '-0.02em',
  },
  unit: {
    fontSize: 12,
    color: '#8a9280',
    fontFamily: "'DM Mono', monospace",
  },
  status: {
    fontSize: 11,
    marginTop: 4,
    fontWeight: 500,
  },
}
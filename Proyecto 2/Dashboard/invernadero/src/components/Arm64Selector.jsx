import { useState } from 'react'
import { useInvernadero } from '../context/InvernaderoContext'

// Columnas disponibles en lecturas.csv 
const COLUMNAS = [
  { value: 'TEMP',         label: 'Temperatura'      },
  { value: 'HUM_AIRE',      label: 'Humedad aire'     },
  { value: 'HUM_SUELO_1',   label: 'Humedad suelo 1'  },
  { value: 'HUM_SUELO_2',   label: 'Humedad suelo 2'  },
  { value: 'LUZ',           label: 'Luz'              },
  { value: 'GAS',           label: 'Gas'              },
]

// Modulos ARM64 disponibles
const MODULOS = [
  { value: 'modulo_1_media',      label: 'Modulo 1 — Media ponderada'      },
  { value: 'modulo_2_varianza',   label: 'Modulo 2 — Varianza y desv. est.'},
  { value: 'modulo_3_anomalias',  label: 'Modulo 3 — Deteccion anomalias'  },
  { value: 'modulo_4_prediccion', label: 'Modulo 4 — Prediccion lineal'    },
  { value: 'modulo_5_tendencia',  label: 'Modulo 5 — Tendencia acumulada'  },
]

export default function Arm64Selector() {
  const { cmd, state } = useInvernadero()
  const [modulo, setModulo]   = useState(MODULOS[0].value)
  const [columna, setColumna] = useState(COLUMNAS[0].value)
  const [archivo, setArchivo] = useState('lecturas.csv')
  const [lineaInicial, setLineaInicial] = useState(1)
  const [lineaFinal, setLineaFinal] = useState(30)
  const [enviado, setEnviado] = useState(false)

  const handleEjecutar = () => {
    cmd.ejecutarArm64(modulo, columna, archivo, lineaInicial, lineaFinal)
    setEnviado(true)
    setTimeout(() => setEnviado(false), 2000)
  }

  return (
    <div style={s.wrap}>
      <div style={s.row}>

        <div style={s.field}>
          <label style={s.label}>Modulo ARM64</label>
          <select
            value={modulo}
            onChange={e => setModulo(e.target.value)}
            style={s.select}
          >
            {MODULOS.map(m => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
        </div>

        <div style={s.field}>
          <label style={s.label}>Columna de lecturas.csv</label>
          <select
            value={columna}
            onChange={e => setColumna(e.target.value)}
            style={s.select}
          >
            {COLUMNAS.map(c => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>

      </div>

      <div style={{ ...s.row, marginTop: 8 }}>

        <div style={s.field}>
          <label style={s.label}>Archivo de entrada</label>
          <input
            type="text"
            value={archivo}
            onChange={e => setArchivo(e.target.value)}
            style={s.input}
          />
        </div>

        <div style={s.field}>
          <label style={s.label}>Línea Inicial</label>
          <input
            type="number"
            min="1"
            value={lineaInicial}
            onChange={e => setLineaInicial(parseInt(e.target.value) || 1)}
            style={s.input}
          />
        </div>

        <div style={s.field}>
          <label style={s.label}>Línea Final</label>
          <input
            type="number"
            min="1"
            value={lineaFinal}
            onChange={e => setLineaFinal(parseInt(e.target.value) || 1)}
            style={s.input}
          />
        </div>

        <button
          onClick={handleEjecutar}
          disabled={!state.mqttConnected}
          style={{
            ...s.btn,
            opacity: state.mqttConnected ? 1 : 0.5,
            background: enviado ? '#3a6b1a' : '#1a1c16',
            marginTop: 18,
          }}
        >
          <i className={`ti ${enviado ? 'ti-check' : 'ti-player-play'}`} style={{ fontSize: 14 }} />
          {enviado ? 'Enviado' : 'Ejecutar'}
        </button>

      </div>

      <div style={s.hint}>
        <i className="ti ti-info-circle" style={{ fontSize: 12 }} />
        Se ejecutará <code style={s.code}>{modulo}.s</code> sobre la columna{' '}
        <code style={s.code}>{columna}</code> en el rango L{lineaInicial}-L{lineaFinal} de <code style={s.code}>{archivo}</code>
      </div>

      {state.arm64.ultimoError && (
        <div style={s.errorBox}>
          <div style={s.errorTitle}>
            <i className="ti ti-alert-triangle" style={{ marginRight: 6, fontSize: 14 }} />
            Error en Módulo ARM64 ({state.arm64.ultimoError.modulo})
          </div>
          <div style={s.errorText}>
            <strong>{state.arm64.ultimoError.error}</strong>: {state.arm64.ultimoError.detail}
          </div>
        </div>
      )}
    </div>
  )
}

const s = {
  wrap: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    marginBottom: 14,
    padding: '12px 14px',
    background: '#f5f2eb',
    border: '1px solid rgba(26,28,22,0.08)',
    borderRadius: 10,
  },
  row: {
    display: 'flex',
    gap: 10,
    alignItems: 'flex-end',
    flexWrap: 'wrap',
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
    flex: '1 1 200px',
  },
  label: {
    fontSize: 10,
    color: '#8a9280',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    fontFamily: 'DM Sans, system-ui, sans-serif',
  },
  select: {
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid rgba(26,28,22,0.12)',
    background: '#ffffff',
    fontSize: 12,
    fontFamily: 'DM Sans, system-ui, sans-serif',
    color: '#1a1c16',
    cursor: 'pointer',
    width: '100%',
  },
  input: {
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid rgba(26,28,22,0.12)',
    background: '#ffffff',
    fontSize: 12,
    fontFamily: 'DM Sans, system-ui, sans-serif',
    color: '#1a1c16',
    boxSizing: 'border-box',
    width: '100%',
  },
  btn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    padding: '8px 16px',
    borderRadius: 8,
    border: 'none',
    color: '#ffffff',
    fontSize: 12,
    fontWeight: 500,
    fontFamily: 'DM Sans, system-ui, sans-serif',
    cursor: 'pointer',
    transition: 'background 0.2s, opacity 0.2s',
    height: 36,
  },
  hint: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    fontSize: 11,
    color: '#8a9280',
    fontFamily: 'DM Sans, system-ui, sans-serif',
    marginTop: 6,
  },
  code: {
    fontFamily: 'DM Mono, monospace',
    color: '#3a6b1a',
    background: '#d6e8c4',
    padding: '1px 5px',
    borderRadius: 4,
  },
  errorBox: {
    marginTop: 10,
    padding: '10px 12px',
    background: '#fdf2f2',
    border: '1px solid #f5c2c2',
    borderRadius: 8,
    fontFamily: 'DM Sans, system-ui, sans-serif',
  },
  errorTitle: {
    fontSize: 12,
    fontWeight: 600,
    color: '#9b1c1c',
    display: 'flex',
    alignItems: 'center',
    marginBottom: 4,
  },
  errorText: {
    fontSize: 11,
    color: '#de3838',
  },
}
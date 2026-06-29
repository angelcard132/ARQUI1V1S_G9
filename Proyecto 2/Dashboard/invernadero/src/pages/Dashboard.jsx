import React from 'react'
import Arm64Selector from '../components/Arm64Selector'
import { useInvernadero } from '../context/InvernaderoContext'
import { THRESHOLDS } from '../lib/config'
import {
  LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'

/*  helpers  */
function cls(v, warn, danger) {
  if (v === null || v === undefined) return '#8a9280'
  if (danger !== undefined && v >= danger) return '#9b2020'
  if (v >= warn) return '#b86b0a'
  return '#3a6b1a'
}

function getCmdStyle(cmd) {
  if (['ON', 'AUTOMATICO', 'RESET', 'SILENCIAR'].includes(cmd)) {
    return { background: '#d6e8c4', color: '#3a6b1a' }
  }
  if (['MANUAL'].includes(cmd)) {
    return { background: '#fce4c8', color: '#b86b0a' }
  }
  return { background: '#f5d0d0', color: '#9b2020' }
}


/*  Panel wrapper  */
function Panel({ title, icon, children, right }) {
  return (
    <div style={s.panel}>
      <div style={s.panelHead}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <i className={`ti ${icon}`} style={{ fontSize: 15, color: '#8a9280' }} />
          <span style={s.panelTitle}>{title}</span>
        </div>
        {right}
      </div>
      <div style={s.panelBody}>{children}</div>
    </div>
  )
}

/*  Sensor card  */
function SCard({ icon, label, value, unit, color }) {
  return (
    <div style={s.scard}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 6 }}>
        <i className={`ti ${icon}`} style={{ fontSize: 13, color: '#8a9280' }} />
        <span style={s.scardLabel}>{label}</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 3 }}>
        <span style={{ ...s.scardVal, color: color || '#1a1c16' }}>
          {value !== null && value !== undefined ? value : '—'}
        </span>
        {unit && <span style={s.scardUnit}>{unit}</span>}
      </div>
    </div>
  )
}

/*  Actuador btn  */
function ABtn({ icon, label, on, onPress, color = '#3a6b1a' }) {
  return (
    <button
      onClick={onPress}
      style={{
        ...s.abtn,
        background: on ? color + '15' : '#f5f2eb',
        borderColor: on ? color + '40' : 'rgba(26,28,22,0.09)',
      }}
    >
      <div style={{ ...s.abtnIcon, background: on ? color + '22' : '#ede8dc' }}>
        <i className={`ti ${icon}`} style={{ fontSize: 16, color: on ? color : '#8a9280' }} />
      </div>
      <span style={s.abtnLabel}>{label}</span>
      <span style={{ ...s.abtnBadge, background: on ? color + '20' : '#ede8dc', color: on ? color : '#8a9280' }}>
        {on ? 'ON' : 'OFF'}
      </span>
    </button>
  )
}

/*  Suelo bar  */
function SueloBar({ area, valor, on, onRiego }) {
  const pct = valor !== null ? Math.min(Math.max(valor, 0), 100) : 0
  const estado = valor === null ? '—' : valor < 35 ? 'SECO' : valor > 80 ? 'SATURADO' : 'NORMAL'
  const color = estado === 'SECO' ? '#b86b0a' : estado === 'SATURADO' ? '#9b2020' : '#3a6b1a'
  const accent = area === 1 ? '#3a6b1a' : '#0e6e56'

  return (
    <div style={s.suelo}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: 12, fontWeight: 500, color: accent }}>Area {area}</span>
        <span style={{ fontSize: 11, fontFamily: 'DM Mono, monospace', color }}>{estado}</span>
      </div>
      <div style={s.barTrack}>
        <div style={{ ...s.barFill, width: pct + '%', background: color, transition: 'width 0.6s ease' }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 6 }}>
        <span style={{ fontFamily: 'Fraunces, Georgia, serif', fontSize: 20, fontWeight: 500, color }}>
          {valor !== null ? valor : '—'}<span style={{ fontSize: 12, color: '#8a9280', marginLeft: 2 }}>{valor !== null ? '%' : ''}</span>
        </span>
        <button
          style={{ ...s.rBtn, borderColor: on ? '#9b2020' : accent, color: on ? '#9b2020' : accent }}
          onClick={onRiego}
        >
          <i className={`ti ${on ? 'ti-player-stop' : 'ti-droplet'}`} style={{ fontSize: 11 }} />
          {on ? 'Detener' : 'Regar'}
        </button>
      </div>
    </div>
  )
}

/*  LCD  */
function LCD({ state }) {
  const [idx, setIdx] = React.useState(0)
  const pantallas = [
    ['Invernadero IoT ', `Estado: ${(state.estadoGlobal || 'NORMAL').slice(0, 14).padEnd(14)}`],
    ['Temperatura:    ', `  ${state.temp ?? '--'} C            `.slice(0, 16)],
    ['Humedad aire:   ', `  ${state.hum ?? '--'} %            `.slice(0, 16)],
    ['Suelo Area 1:   ', `  ${state.suelo1 ?? '--'} %          `.slice(0, 16)],
    ['Suelo Area 2:   ', `  ${state.suelo2 ?? '--'} %          `.slice(0, 16)],
    ['Luz:            ', `  ${state.luz ?? '--'} lux         `.slice(0, 16)],
    ['Gas:            ', `  ${state.gas ?? '--'} ppm         `.slice(0, 16)],
    ['Riego:          ', `  ${(state.riego1 || state.riego2) ? 'ACTIVO  ' : 'OFF     '}`],
    ['Ventilador:     ', `  ${state.ventilador ? 'ON      ' : 'OFF     '}`],
  ]

  React.useEffect(() => {
    if (state.estadoGlobal === 'EMERGENCIA') return
    const id = setInterval(() => setIdx(i => (i + 1) % pantallas.length), 3000)
    return () => clearInterval(id)
  }, [pantallas.length, state.estadoGlobal])

  const screen = state.estadoGlobal === 'EMERGENCIA'
    ? ['!! EMERGENCIA !!', `GAS: ${state.gas ?? '--'} ppm    `]
    : pantallas[idx]

  return (
    <div style={s.lcd}>
      <div style={s.lcdLine}>{(screen[0] || '').padEnd(16).slice(0, 16)}</div>
      <div style={s.lcdLine}>{(screen[1] || '').padEnd(16).slice(0, 16)}</div>
    </div>
  )
}

/*  Grafica simple  */
function Grafica({ labels, data, color, unit }) {
  const puntos = labels.map((l, i) => ({ l, v: data[i] ?? null }))
  if (puntos.length === 0) return <div style={s.chartEmpty}>Sin datos aun</div>
  return (
    <ResponsiveContainer width="100%" height={120}>
      <LineChart data={puntos} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(26,28,22,0.06)" />
        <XAxis dataKey="l" tick={{ fontSize: 8, fill: '#8a9280', fontFamily: 'DM Mono,monospace' }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
        <YAxis tick={{ fontSize: 8, fill: '#8a9280', fontFamily: 'DM Mono,monospace' }} tickLine={false} axisLine={false} />
        <Tooltip
          contentStyle={{ background: '#faf8f2', border: '1px solid rgba(26,28,22,0.12)', borderRadius: 6, fontSize: 11, fontFamily: 'DM Sans,system-ui,sans-serif' }}
          formatter={v => [`${v} ${unit}`, '']}
          labelFormatter={() => ''}
        />
        <Line type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} dot={false} activeDot={{ r: 3, strokeWidth: 0 }} connectNulls />
      </LineChart>
    </ResponsiveContainer>
  )
}

/*  Evento item  */
function EvItem({ ev }) {
  const color = ev.tipo === 'danger' ? '#9b2020' : ev.tipo === 'warn' ? '#b86b0a' : '#3a6b1a'
  return (
    <div style={s.evItem}>
      <span style={{ ...s.evDot, background: color }} />
      <span style={s.evText}>{ev.texto}</span>
      <span style={s.evHora}>{ev.hora}</span>
    </div>
  )
}

/*  ARM64 card  */
function ArmCard({ archivo, titulo, children, ok, columna }) {
  return (
    <div style={s.armCard}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
        <span style={s.armFile}>
          {archivo} {columna ? `(${columna})` : ''}
        </span>
        <span style={{ ...s.armBadge, background: ok ? '#d6e8c4' : '#ede8dc', color: ok ? '#3a6b1a' : '#8a9280' }}>
          {ok ? 'OK' : 'Pendiente'}
        </span>
      </div>
      <div style={s.armTitulo}>{titulo}</div>
      <div style={{ marginTop: 6 }}>{children}</div>
    </div>
  )
}

function ArmFila({ label, value, color }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0', borderBottom: '1px solid rgba(26,28,22,0.05)' }}>
      <span style={{ fontSize: 10, color: '#8a9280' }}>{label}</span>
      <span style={{ fontSize: 12, fontWeight: 500, fontFamily: 'DM Mono,monospace', color: color || '#1a1c16' }}>{value ?? '—'}</span>
    </div>
  )
}

/*  Dashboard principal  */
export default function Dashboard() {
  const { state, publicar } = useInvernadero()
  const T = THRESHOLDS

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

      {/* Sensores */}
      <section id="dashboard">
        <div style={s.secLabel}>Sensores ambientales</div>
        <div style={s.row6}>
          <SCard icon="ti-temperature" label="Temperatura" value={state.temp} unit="°C" color={cls(state.temp, T.TEMP_ALTA)} />
          <SCard icon="ti-droplets" label="Humedad aire" value={state.hum} unit="%" color={cls(state.hum, T.HUM_ALTA)} />
          <SCard icon="ti-sun" label="Luz" value={state.luz} unit="lux" color={state.luz < T.LUZ_BAJA ? '#b86b0a' : '#3a6b1a'} />
          <SCard icon="ti-cloud" label="Gas / humo" value={state.gas} unit="ppm" color={cls(state.gas, T.GAS_WARN, T.GAS_EMRG)} />
          <SCard icon="ti-timeline" label="Lecturas" value={state.totalLecturas} />
          <SCard icon="ti-clock" label="Ultima" value={state.ultimaLectura || '—'} color={state.mqttConnected ? '#3a6b1a' : '#8a9280'} />
        </div>
      </section>

      {/* Areas + Actuadores */}
      <div style={s.row2} id="riego">
        <Panel title="Areas de cultivo" icon="ti-layout-columns">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <SueloBar area={1} valor={state.suelo1} on={state.riego1} onRiego={() => publicar('riego_area1', state.riego1 ? 'OFF' : 'ON')} />
            <div style={{ borderTop: '1px solid rgba(26,28,22,0.07)' }} />
            <SueloBar area={2} valor={state.suelo2} on={state.riego2} onRiego={() => publicar('riego_area2', state.riego2 ? 'OFF' : 'ON')} />
          </div>
        </Panel>

        <Panel title="Actuadores" icon="ti-adjustments-horizontal" id="actuadores">
          <div style={s.row4}>
            <ABtn icon="ti-droplet" label="Bomba" on={state.riego1 || state.riego2} color="#3a6b1a" onPress={() => publicar('riego', (state.riego1 || state.riego2) ? 'OFF' : 'ON')} />
            <ABtn icon="ti-wind" label="Ventilador" on={state.ventilador} color="#0e6e56" onPress={() => publicar('ventilador', state.ventilador ? 'OFF' : 'ON')} />
            <ABtn icon="ti-bulb" label="Luces" on={state.luces} color="#b86b0a" onPress={() => publicar('luces', state.luces ? 'OFF' : 'ON')} />
            <ABtn icon="ti-bell" label="Alarma" on={state.alarma} color="#9b2020" onPress={() => publicar('alarma', 'SILENCIAR')} />
            <ABtn icon="ti-circle-check" label="LED verde" on={state.estadoGlobal === 'NORMAL'} color="#3a6b1a" />
            <ABtn icon="ti-circle" label="LED amarillo" on={['ADVERTENCIA', 'RIEGO_ACTIVO', 'MODO_MANUAL'].includes(state.estadoGlobal)} color="#b86b0a" />
            <ABtn icon="ti-alert-circle" label="LED rojo" on={state.estadoGlobal === 'EMERGENCIA'} color="#9b2020" />
            <ABtn icon="ti-plug" label="Raspberry online" on={state.mqttConnected} color="#3a6b1a" />
          </div>
        </Panel>
      </div>

      {/* LCD + Control remoto */}
      <div style={s.row2}>
        <Panel title="Vista LCD" icon="ti-device-tablet"
          right={<span style={{ fontSize: 10, color: '#8a9280', fontFamily: 'DM Mono,monospace' }}>Cada 3 segundos cambiará</span>}
        >
          <LCD state={state} />
        </Panel>

        <Panel title="Control remoto" icon="ti-remote-control">
          <div style={s.row2ctrl}>
            {[
              { label: 'Riego ON', actuador: 'riego', cmd: 'ON', color: '#3a6b1a', icon: 'ti-droplet' },
              { label: 'Riego OFF', actuador: 'riego', cmd: 'OFF', color: '#9b2020', icon: 'ti-droplet-off' },
              { label: 'Ventilador ON', actuador: 'ventilador', cmd: 'ON', color: '#0e6e56', icon: 'ti-wind' },
              { label: 'Ventilador OFF', actuador: 'ventilador', cmd: 'OFF', color: '#9b2020', icon: 'ti-wind' },
              { label: 'Luces ON', actuador: 'luces', cmd: 'ON', color: '#b86b0a', icon: 'ti-bulb' },
              { label: 'Luces OFF', actuador: 'luces', cmd: 'OFF', color: '#9b2020', icon: 'ti-bulb-off' },
              { label: 'Silenciar alarma', actuador: 'alarma', cmd: 'SILENCIAR', color: '#4a5240', icon: 'ti-bell-off' },
              { label: 'Reset estado', actuador: 'global', cmd: 'RESET', color: '#185FA5', icon: 'ti-refresh' },
            ].map(b => (
              <button key={b.label}
                style={{ ...s.ctrlBtn, borderColor: b.color + '50', color: b.color }}
                onClick={() => publicar(b.actuador, b.cmd)}
                disabled={!state.mqttConnected}
                onMouseEnter={e => e.currentTarget.style.background = b.color + '12'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <i className={`ti ${b.icon}`} style={{ fontSize: 13 }} />
                {b.label}
              </button>
            ))}
          </div>
        </Panel>
      </div>

      {/* Graficas */}
      <section id="historico">
        <Panel title="Historial de sensores | ultimas 30 lecturas" icon="ti-chart-line">
          <div style={s.row2}>
            <div>
              <div style={s.chartLabel}>Temperatura (°C) y Humedad (%)</div>
              <ResponsiveContainer width="100%" height={130}>
                <LineChart data={state.histLabels.map((l, i) => ({ l, temp: state.histTemp[i], hum: state.histHum[i] }))} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(26,28,22,0.06)" />
                  <XAxis dataKey="l" tick={{ fontSize: 8, fill: '#8a9280' }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                  <YAxis tick={{ fontSize: 8, fill: '#8a9280' }} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ background: '#faf8f2', border: '1px solid rgba(26,28,22,0.12)', borderRadius: 6, fontSize: 11 }} />
                  <Line type="monotone" dataKey="temp" stroke="#E85D24" strokeWidth={1.5} dot={false} connectNulls name="Temp °C" />
                  <Line type="monotone" dataKey="hum" stroke="#185FA5" strokeWidth={1.5} dot={false} connectNulls name="Hum %" />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div>
              <div style={s.chartLabel}>Humedad suelo Area 1 y Area 2 (%)</div>
              <ResponsiveContainer width="100%" height={130}>
                <LineChart data={state.histLabels.map((l, i) => ({ l, s1: state.histSuelo1[i], s2: state.histSuelo2[i] }))} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(26,28,22,0.06)" />
                  <XAxis dataKey="l" tick={{ fontSize: 8, fill: '#8a9280' }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                  <YAxis tick={{ fontSize: 8, fill: '#8a9280' }} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ background: '#faf8f2', border: '1px solid rgba(26,28,22,0.12)', borderRadius: 6, fontSize: 11 }} />
                  <Line type="monotone" dataKey="s1" stroke="#3a6b1a" strokeWidth={1.5} dot={false} connectNulls name="Area 1 %" />
                  <Line type="monotone" dataKey="s2" stroke="#0e6e56" strokeWidth={1.5} dot={false} connectNulls name="Area 2 %" />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div>
              <div style={s.chartLabel}>Luz (lux)</div>
              <Grafica labels={state.histLabels} data={state.histLuz} color="#b86b0a" unit="lux" />
            </div>
            <div>
              <div style={s.chartLabel}>Gas (ppm)</div>
              <Grafica labels={state.histLabels} data={state.histGas} color="#9b2020" unit="ppm" />
            </div>
          </div>
        </Panel>
      </section>

      {/* ARM64 + Eventos */}
      <div style={s.row2} id="arm64">
        <Panel title="Analisis ARM64" icon="ti-cpu"
          right={<span style={{ fontSize: 10, color: '#8a9280', fontFamily: 'DM Mono,monospace' }}>5 modulos · lecturas.csv</span>}
        >

          {/* Selector: modulo + columna + boton ejecutar */}
          <Arm64Selector />

          {/* Indicador de "ejecutando..." mientras llega la respuesta */}
          {state.arm64Ejecutando && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 6,
              fontSize: 11, color: '#b86b0a', marginBottom: 10,
              fontFamily: 'DM Sans, system-ui, sans-serif',
            }}>
              <i className="ti ti-loader-2" style={{ fontSize: 13, animation: 'spin 1s linear infinite' }} />
              Ejecutando {state.arm64Ejecutando.modulo} sobre columna {state.arm64Ejecutando.columna}...
            </div>
          )}

          {/* Grid de 4 cards: modulos 1 al 4 */}
          <div style={s.row2}>

            <ArmCard
              archivo="modulo_1_media.s"
              titulo="Media ponderada"
              ok={!!state.arm64.media}
              columna={state.arm64.media?.columna}
            >
              <ArmFila label="Media" value={state.arm64.media?.val} color="#3a6b1a" />
              <ArmFila label="Suma X" value={state.arm64.media?.sum} />
              <ArmFila label="Suma pesos" value={state.arm64.media?.pesos} />
            </ArmCard>

            <ArmCard
              archivo="modulo_2_varianza.s"
              titulo="Varianza y desv. estandar"
              ok={!!state.arm64.varianza}
              columna={state.arm64.varianza?.columna}
            >
              <ArmFila label="Media" value={state.arm64.varianza?.media} />
              <ArmFila label="Varianza" value={state.arm64.varianza?.varianza} />
              <ArmFila label="Desv. est." value={state.arm64.varianza?.desv} color="#3a6b1a" />
            </ArmCard>

            <ArmCard
              archivo="modulo_3_anomalias.s"
              titulo="Deteccion de anomalias"
              ok={!!state.arm64.anomalias}
              columna={state.arm64.anomalias?.columna}
            >
              <ArmFila label="Media" value={state.arm64.anomalias?.media} />
              <ArmFila label="Anomalias" value={state.arm64.anomalias?.cantidad} color="#b86b0a" />
              <ArmFila
                label="Riesgo"
                value={state.arm64.anomalias?.riesgo}
                color={
                  state.arm64.anomalias?.riesgo === 'HIGH' ? '#9b2020' :
                    state.arm64.anomalias?.riesgo === 'MEDIUM' ? '#b86b0a' :
                      '#3a6b1a'
                }
              />
            </ArmCard>

            <ArmCard
              archivo="modulo_4_prediccion.s"
              titulo="Prediccion lineal"
              ok={!!state.arm64.prediccion}
              columna={state.arm64.prediccion?.columna}
            >
              <ArmFila label="Inicial" value={state.arm64.prediccion?.inicial} />
              <ArmFila label="Final" value={state.arm64.prediccion?.final} />
              <ArmFila label="Cambio" value={state.arm64.prediccion?.cambio} />
              <ArmFila label="Siguiente" value={state.arm64.prediccion?.siguiente} color="#3a6b1a" />
            </ArmCard>

          </div>

          {/* Card 5: tendencia — ocupa todo el ancho */}
          <div style={{ marginTop: 10 }}>
            <ArmCard
              archivo="modulo_5_tendencia.s"
              titulo="Tendencia acumulada avanzada"
              ok={!!state.arm64.tendencia}
              columna={state.arm64.tendencia?.columna}
            >
              {state.arm64.tendencia
                ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <i
                        className={`ti ${state.arm64.tendencia.trend === 'UP' ? 'ti-trending-up' :
                            state.arm64.tendencia.trend === 'DOWN' ? 'ti-trending-down' :
                              'ti-minus'
                          }`}
                        style={{
                          fontSize: 22,
                          color: state.arm64.tendencia.trend === 'UP' ? '#3a6b1a' :
                            state.arm64.tendencia.trend === 'DOWN' ? '#9b2020' :
                              '#8a9280',
                        }}
                      />
                      <span style={{
                        fontFamily: 'Fraunces,Georgia,serif', fontSize: 20, fontWeight: 500,
                        color: state.arm64.tendencia.trend === 'UP' ? '#3a6b1a' : '#9b2020',
                      }}>
                        {state.arm64.tendencia.trend}
                      </span>
                    </div>
                    <div style={{ flex: 1 }}>
                      <ArmFila label="Incrementos" value={state.arm64.tendencia.incrementos} />
                      <ArmFila label="Decrementos" value={state.arm64.tendencia.decrementos} />
                      <ArmFila label="Racha max" value={state.arm64.tendencia.racha} />
                      <ArmFila label="Dif. acumulada" value={state.arm64.tendencia.acum} />
                    </div>
                  </div>
                )
                : <span style={{ fontSize: 11, color: '#8a9280', fontStyle: 'italic' }}>Esperando 30 lecturas reales...</span>
              }
            </ArmCard>
          </div>

          {/* Separador para Fase 2 */}
          <div style={{
            height: 1,
            background: 'rgba(26,28,22,0.08)',
            margin: '24px 0 16px 0',
            position: 'relative'
          }}>
            <span style={{
              position: 'absolute',
              top: '50%',
              left: 12,
              transform: 'translateY(-50%)',
              background: '#fdfbf7',
              padding: '0 8px',
              fontSize: 10,
              fontWeight: 600,
              color: '#8a9280',
              textTransform: 'uppercase',
              letterSpacing: '0.05em'
            }}>
              Fase 2 — Nuevas Rutinas del Analizador
            </span>
          </div>

          {/* Grid de 4 cards para Fase 2 */}
          <div style={s.row2}>

            <ArmCard
              archivo="modulo_1_rmse.s"
              titulo="RMSE (Error cuadrático)"
              ok={!!state.arm64.rmse}
              columna={state.arm64.rmse?.columna}
            >
              <ArmFila label="Ideal" value={state.arm64.rmse?.ideal} />
              <ArmFila label="RMSE" value={state.arm64.rmse?.rmse} color="#b86b0a" />
            </ArmCard>

            <ArmCard
              archivo="modulo_2_regresion.s"
              titulo="Regresión Lineal Simple"
              ok={!!state.arm64.regresion}
              columna={state.arm64.regresion?.columna}
            >
              <ArmFila label="Pendiente x100" value={state.arm64.regresion?.slope} color="#3a6b1a" />
              <ArmFila label="Tendencia" value={state.arm64.regresion?.trend} />
            </ArmCard>

            <ArmCard
              archivo="modulo_3_prediccion.s"
              titulo="Predicción Futura"
              ok={!!state.arm64.prediccionF2}
              columna={state.arm64.prediccionF2?.columna}
            >
              <ArmFila label="Proyección K" value={state.arm64.prediccionF2?.k} />
              <ArmFila label="Pendiente x100" value={state.arm64.prediccionF2?.slope} />
              <ArmFila label="Intercepto x100" value={state.arm64.prediccionF2?.intercept} />
              <ArmFila label="Predicción futura" value={state.arm64.prediccionF2?.predicted} color="#3a6b1a" />
            </ArmCard>

            <ArmCard
              archivo="modulo_4_integral_error.s"
              titulo="Integral del Error (Trapecio)"
              ok={!!state.arm64.integral}
              columna={state.arm64.integral?.columna}
            >
              <ArmFila label="Ideal" value={state.arm64.integral?.ideal} />
              <ArmFila label="Integral" value={state.arm64.integral?.integral} color="#b86b0a" />
            </ArmCard>

          </div>

          {/* Card 5 Fase 2 */}
          <div style={{ marginTop: 10 }}>
            <ArmCard
              archivo="modulo_5_derivada_local.s"
              titulo="Derivada Suavizada Local"
              ok={!!state.arm64.derivada}
              columna={state.arm64.derivada?.columna}
            >
              {state.arm64.derivada
                ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <i className="ti ti-activity" style={{ fontSize: 22, color: '#b86b0a' }} />
                      <span style={{
                        fontFamily: 'Fraunces,Georgia,serif', fontSize: 20, fontWeight: 500,
                        color: '#b86b0a',
                      }}>
                        Derivada Local
                      </span>
                    </div>
                    <div style={{ flex: 1 }}>
                      <ArmFila label="Tamaño de ventana" value={state.arm64.derivada.windowSize} />
                      <ArmFila label="Máxima Pendiente x100" value={state.arm64.derivada.maxSlope} color="#9b2020" />
                    </div>
                  </div>
                )
                : <span style={{ fontSize: 11, color: '#8a9280', fontStyle: 'italic' }}>Esperando ejecución...</span>
              }
            </ArmCard>
          </div>

        </Panel>

        <Panel title="Ultimos eventos" icon="ti-history" id="eventos">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5, maxHeight: 340, overflowY: 'auto' }}>
            {state.eventos.length === 0
              ? <div style={{ textAlign: 'center', color: '#8a9280', fontSize: 12, padding: '20px 0' }}>Sin eventos aun</div>
              : state.eventos.map(ev => <EvItem key={ev.id} ev={ev} />)
            }
          </div>
        </Panel>
      </div>

      {/* MQTT + Comandos */}
      <div style={s.row2} id="mqtt">
        <Panel title="MQTT topics en vivo" icon="ti-antenna">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {[
              { label: 'sensores/temperatura', val: state.temp, unit: '°C' },
              { label: 'sensores/humedad_ambiente', val: state.hum, unit: '%' },
              { label: 'sensores/humedad_suelo_area1', val: state.suelo1, unit: '%' },
              { label: 'sensores/humedad_suelo_area2', val: state.suelo2, unit: '%' },
              { label: 'sensores/luz', val: state.luz, unit: 'lux' },
              { label: 'sensores/gas', val: state.gas, unit: 'ppm' },
              { label: 'actuadores/riego_area1', val: state.riego1, unit: '' },
              { label: 'actuadores/ventilador', val: state.ventilador, unit: '' },
              { label: 'actuadores/luces', val: state.luces, unit: '' },
              { label: 'actuadores/alarma', val: state.alarma, unit: '' },
              { label: 'estado/global', val: state.estadoGlobal, unit: '' },
            ].map(t => {
              const hasVal = t.val !== null && t.val !== undefined
              const display = typeof t.val === 'boolean' ? (t.val ? 'ON' : 'OFF') : (hasVal ? `${t.val}${t.unit ? ' ' + t.unit : ''}` : '—')
              return (
                <div key={t.label} style={s.topicRow}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ ...s.topicDot, background: hasVal && state.mqttConnected ? '#5a9a2a' : '#c4c0b6' }} />
                    <span style={s.topicName}>invernadero/G9/{t.label}</span>
                  </div>
                  <span style={{ ...s.topicVal, color: hasVal ? '#1a1c16' : '#8a9280' }}>{display}</span>
                </div>
              )
            })}
          </div>
        </Panel>

        <Panel title="Historial de comandos" icon="ti-terminal-2" id="comandos">
          {state.comandos.length === 0
            ? <div style={{ textAlign: 'center', color: '#8a9280', fontSize: 12, padding: '20px 0' }}>Sin comandos enviados aun</div>
            : (
              <div style={{ overflowY: 'auto', maxHeight: 300 }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, fontFamily: 'DM Sans,system-ui,sans-serif' }}>
                  <thead>
                    <tr>
                      {['Hora', 'Actuador', 'Cmd', 'Origen'].map(h => (
                        <th key={h} style={{ textAlign: 'left', padding: '5px 8px', color: '#8a9280', fontSize: 10, textTransform: 'uppercase', borderBottom: '1px solid rgba(26,28,22,0.08)' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {state.comandos.map(c => (
                      <tr key={c.id} style={{ borderBottom: '1px solid rgba(26,28,22,0.05)' }}>
                        <td style={{ padding: '6px 8px', fontFamily: 'DM Mono,monospace', color: '#8a9280', fontSize: 11 }}>{c.hora}</td>
                        <td style={{ padding: '6px 8px', color: '#4a5240' }}>{c.actuador}</td>
                        <td style={{ padding: '6px 8px' }}>
                          <span style={{ fontSize: 10, padding: '2px 7px', borderRadius: 20, fontFamily: 'DM Mono,monospace', fontWeight: 500, ...getCmdStyle(c.cmd) }}>
                            {c.cmd}
                          </span>
                        </td>
                        <td style={{ padding: '6px 8px', color: '#8a9280', fontSize: 11 }}>{c.origen}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          }
        </Panel>
      </div>

    </div>
  )
}

/*  Estilos  */
const s = {
  secLabel: { fontSize: 11, color: '#8a9280', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8, fontFamily: 'DM Sans,system-ui,sans-serif' },
  row6: { display: 'grid', gridTemplateColumns: 'repeat(6,1fr)', gap: 10 },
  row4: { display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 8 },
  row2: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 },
  row2ctrl: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 7 },
  scard: { background: '#f5f2eb', border: '1px solid rgba(26,28,22,0.08)', borderRadius: 10, padding: '12px 14px' },
  scardLabel: { fontSize: 10, color: '#8a9280', textTransform: 'uppercase', letterSpacing: '0.05em', fontFamily: 'DM Sans,system-ui,sans-serif' },
  scardVal: { fontFamily: 'Fraunces,Georgia,serif', fontSize: 26, fontWeight: 500, lineHeight: 1, letterSpacing: '-0.02em' },
  scardUnit: { fontSize: 11, color: '#8a9280', fontFamily: 'DM Mono,monospace' },
  panel: { background: '#ffffff', border: '1px solid rgba(26,28,22,0.08)', borderRadius: 12, overflow: 'hidden' },
  panelHead: { padding: '10px 16px', borderBottom: '1px solid rgba(26,28,22,0.07)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  panelTitle: { fontSize: 13, fontWeight: 500, color: '#1a1c16', fontFamily: 'DM Sans,system-ui,sans-serif' },
  panelBody: { padding: '14px 16px' },
  suelo: { display: 'flex', flexDirection: 'column' },
  barTrack: { height: 6, background: '#ede8dc', borderRadius: 3, overflow: 'hidden' },
  barFill: { height: '100%', borderRadius: 3 },
  rBtn: { display: 'flex', alignItems: 'center', gap: 5, padding: '4px 12px', borderRadius: 20, border: '1px solid', background: 'transparent', cursor: 'pointer', fontSize: 11, fontFamily: 'DM Sans,system-ui,sans-serif', transition: 'opacity 0.15s' },
  abtn: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, padding: '10px 6px', borderRadius: 10, border: '1px solid', cursor: 'pointer', transition: 'all 0.2s', fontFamily: 'DM Sans,system-ui,sans-serif' },
  abtnIcon: { width: 34, height: 34, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  abtnLabel: { fontSize: 10, color: '#4a5240', textAlign: 'center' },
  abtnBadge: { fontSize: 9, padding: '1px 7px', borderRadius: 20, fontWeight: 500, fontFamily: 'DM Mono,monospace' },
  ctrlBtn: { display: 'flex', alignItems: 'center', gap: 6, padding: '8px 10px', borderRadius: 7, border: '1px solid', background: 'transparent', cursor: 'pointer', fontSize: 11, fontFamily: 'DM Sans,system-ui,sans-serif', fontWeight: 500, transition: 'background 0.15s' },
  lcd: { background: '#1a2e0a', borderRadius: 6, padding: '12px 16px', border: '2px solid #2a4010' },
  lcdLine: { fontFamily: 'DM Mono,monospace', fontSize: 13, color: '#7ec84a', letterSpacing: '0.04em', lineHeight: 1.8, whiteSpace: 'pre' },
  chartLabel: { fontSize: 11, color: '#8a9280', marginBottom: 6, fontFamily: 'DM Sans,system-ui,sans-serif' },
  chartEmpty: { fontSize: 11, color: '#8a9280', textAlign: 'center', padding: '20px 0', fontFamily: 'DM Sans,system-ui,sans-serif', fontStyle: 'italic' },
  evItem: { display: 'flex', alignItems: 'flex-start', gap: 7, padding: '6px 8px', borderRadius: 5, background: '#f5f2eb' },
  evDot: { width: 6, height: 6, borderRadius: '50%', marginTop: 4, flexShrink: 0 },
  evText: { flex: 1, fontSize: 12, color: '#1a1c16', fontFamily: 'DM Sans,system-ui,sans-serif', lineHeight: 1.4 },
  evHora: { fontSize: 10, color: '#8a9280', fontFamily: 'DM Mono,monospace', whiteSpace: 'nowrap' },
  armCard: { background: '#f5f2eb', border: '1px solid rgba(26,28,22,0.08)', borderRadius: 8, padding: '10px 12px' },
  armFile: { fontSize: 10, color: '#8a9280', fontFamily: 'DM Mono,monospace' },
  armBadge: { fontSize: 9, padding: '1px 7px', borderRadius: 20, fontWeight: 500, fontFamily: 'DM Mono,monospace' },
  armTitulo: { fontSize: 12, fontWeight: 500, color: '#1a1c16', fontFamily: 'DM Sans,system-ui,sans-serif' },
  topicRow: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 8px', borderRadius: 5, background: '#f5f2eb' },
  topicDot: { width: 5, height: 5, borderRadius: '50%', flexShrink: 0, transition: 'all 0.3s' },
  topicName: { fontSize: 10, color: '#8a9280', fontFamily: 'DM Mono,monospace' },
  topicVal: { fontSize: 11, fontWeight: 500, fontFamily: 'DM Mono,monospace' },
}
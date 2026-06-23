import {
  createContext,
  useContext,
  useReducer,
  useEffect,
  useRef,
  useCallback
} from 'react'
import mqtt from 'mqtt'
import { MQTT_CONFIG, TOPICS, BASE } from '../lib/config'


// Estado inicial 
const initialState = {
  mqttConnected: false,
  mqttStatus:    'Desconectado',

  temp:   null,
  hum:    null,
  luz:    null,
  gas:    null,
  suelo1: null,
  suelo2: null,

  riego1:     false,
  riego2:     false,
  ventilador: false,
  luces:      false,
  alarma:     false,

  estadoGlobal: 'NORMAL',
  modo:         'AUTOMATICO',

  histTemp:   [],
  histHum:    [],
  histSuelo1: [],
  histSuelo2: [],
  histLuz:    [],
  histGas:    [],
  histLabels: [],

  eventos:   [],
  comandos:  [],

  // ARM64 — ahora cada modulo guarda tambien que columna se uso
  arm64: {
    media:      null,
    varianza:   null,
    anomalias:  null,
    prediccion: null,
    tendencia:  null,
  },
  arm64Ejecutando: null, // { modulo, columna } mientras espera resultado

  totalLecturas: 0,
  ultimaLectura: null,
}

//  Reducer 
function reducer(state, action) {
  switch (action.type) {

    case 'MQTT_STATUS':
      return { ...state, mqttConnected: action.connected, mqttStatus: action.status }

    case 'SENSOR': {
      const { key, valor } = action
      const hKey   = 'hist' + key.charAt(0).toUpperCase() + key.slice(1)
      const now    = new Date().toLocaleTimeString('es-GT', { hour:'2-digit', minute:'2-digit', second:'2-digit' })
      const addToHist = (arr) => arr.length >= 30 ? [...arr.slice(1), valor] : [...arr, valor]
      const addLabel  = (arr) => arr.length >= 30 ? [...arr.slice(1), now]   : [...arr, now]
      return {
        ...state,
        [key]:         valor,
        [hKey]:        addToHist(state[hKey] || []),
        histLabels:    addLabel(state.histLabels),
        totalLecturas: state.totalLecturas + 1,
        ultimaLectura: now,
      }
    }

    case 'ACTUADOR':
      return { ...state, [action.key]: action.valor }

    case 'ESTADO_GLOBAL':
      return {
        ...state,
        estadoGlobal: action.estado,
        modo: action.modo || state.modo,
      }

    case 'MODO':
      return { ...state, modo: action.modo }

    case 'EVENTO': {
      const evs = [action.evento, ...state.eventos].slice(0, 30)
      return { ...state, eventos: evs }
    }

    case 'COMANDO': {
      const cmds = [action.comando, ...state.comandos].slice(0, 30)
      return { ...state, comandos: cmds }
    }

    case 'ARM64':
      return {
        ...state,
        arm64: { ...state.arm64, ...action.data },
        arm64Ejecutando: null,
      }

    case 'ARM64_EJECUTANDO':
      return { ...state, arm64Ejecutando: action.payload }

    default:
      return state
  }
}

//  Context 
const Ctx = createContext(null)

export function InvernaderoProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState)
  const clientRef         = useRef(null)

  const addEvento = useCallback((texto, tipo = 'ok') => {
    dispatch({
      type:   'EVENTO',
      evento: {
        id:   Date.now(),
        texto,
        tipo,
        hora: new Date().toLocaleTimeString('es-GT', { hour:'2-digit', minute:'2-digit' }),
      },
    })
  }, [])

  // Publicar comando MQTT generico 
  const publicar = useCallback((actuador, cmd) => {
    const client = clientRef.current
    if (!client?.connected) {
      console.warn('[MQTT] Sin conexion — comando no enviado:', actuador, cmd)
      return
    }

    const payload = JSON.stringify({
      actuador,
      cmd,
      origen: 'dashboard',
      ts:     Date.now(),
    })

    client.publish(TOPICS.REMOTO, payload)

    dispatch({
      type:    'COMANDO',
      comando: {
        id:       Date.now(),
        hora:     new Date().toLocaleTimeString('es-GT', { hour:'2-digit', minute:'2-digit', second:'2-digit' }),
        actuador,
        cmd,
        origen:  'Dashboard',
      },
    })

    addEvento(`Comando enviado: ${actuador} → ${cmd}`, 'ok')
  }, [addEvento])

  // Publicar solicitud de ejecucion ARM64 
  const publicarArm64 = useCallback((modulo, columna) => {
    const client = clientRef.current
    if (!client?.connected) {
      console.warn('[MQTT] Sin conexion — ARM64 no enviado')
      return
    }

    const payload = JSON.stringify({
      modulo,
      columna,
      origen: 'dashboard',
      ts:     Date.now(),
    })

    client.publish(TOPICS.ARM64_REQUEST, payload)

    dispatch({ type: 'ARM64_EJECUTANDO', payload: { modulo, columna } })

    dispatch({
      type:    'COMANDO',
      comando: {
        id:       Date.now(),
        hora:     new Date().toLocaleTimeString('es-GT', { hour:'2-digit', minute:'2-digit', second:'2-digit' }),
        actuador: modulo,
        cmd:      `COL=${columna}`,
        origen:  'Dashboard ARM64',
      },
    })

    addEvento(`Ejecutando ${modulo} sobre columna ${columna}`, 'ok')
  }, [addEvento])

  // Parsear mensajes MQTT entrantes 
  const parseMensaje = useCallback((topic, payload) => {
    let data
    try   { data = JSON.parse(payload) }
    catch { data = { valor: payload }  }

    const sub = topic.replace(BASE + '/', '')

    switch (sub) {

      case 'sensores/temperatura':
        dispatch({ type: 'SENSOR', key: 'temp', valor: data.valor })
        if (data.estado === 'ALTA') addEvento(`Temperatura alta: ${data.valor}°C`, 'warn')
        break

      case 'sensores/humedad_ambiente':
        dispatch({ type: 'SENSOR', key: 'hum', valor: data.valor })
        break

      case 'sensores/humedad_suelo_area1':
        dispatch({ type: 'SENSOR', key: 'suelo1', valor: data.valor })
        if (data.estado === 'SECO') addEvento(`Suelo Area 1 SECO (${data.valor}%) — riego activado`, 'warn')
        break

      case 'sensores/humedad_suelo_area2':
        dispatch({ type: 'SENSOR', key: 'suelo2', valor: data.valor })
        if (data.estado === 'SECO') addEvento(`Suelo Area 2 SECO (${data.valor}%) — riego activado`, 'warn')
        break

      case 'sensores/luz':
        dispatch({ type: 'SENSOR', key: 'luz', valor: data.valor })
        break

      case 'sensores/gas':
        dispatch({ type: 'SENSOR', key: 'gas', valor: data.valor })
        if (data.estado === 'GAS_EMERGENCIA')   addEvento(`GAS EMERGENCIA: ${data.valor} ppm`, 'danger')
        else if (data.estado === 'GAS_ADVERTENCIA') addEvento(`Gas advertencia: ${data.valor} ppm`, 'warn')
        break

      case 'actuadores/riego_area1':
        dispatch({ type: 'ACTUADOR', key: 'riego1', valor: data.bomba === true || data.estado === 'ON' })
        if (data.bomba) addEvento('Bomba Area 1 activada', 'ok')
        if (data.estado === 'BLOQUEADO_POR_SATURACION') addEvento('Riego Area 1 bloqueado — suelo saturado', 'warn')
        break

      case 'actuadores/riego_area2':
        dispatch({ type: 'ACTUADOR', key: 'riego2', valor: data.bomba === true || data.estado === 'ON' })
        if (data.bomba) addEvento('Bomba Area 2 activada', 'ok')
        if (data.estado === 'BLOQUEADO_POR_SATURACION') addEvento('Riego Area 2 bloqueado — suelo saturado', 'warn')
        break

      case 'actuadores/ventilador':
        dispatch({ type: 'ACTUADOR', key: 'ventilador', valor: data.activo === true || ['ON','VENTILACION_ON','VENTILACION_MANUAL','VENTILACION_EMERGENCIA'].includes(data.estado) })
        if (data.estado === 'VENTILACION_EMERGENCIA') addEvento('Ventilador en modo EMERGENCIA', 'danger')
        break

      case 'actuadores/luces':
        dispatch({ type: 'ACTUADOR', key: 'luces', valor: data.activo === true || data.estado === 'ON' })
        break

      case 'actuadores/alarma':
        dispatch({ type: 'ACTUADOR', key: 'alarma', valor: data.buzzer === true || data.estado === 'ON' })
        if (data.estado === 'ON')        addEvento('ALARMA activada', 'danger')
        if (data.estado === 'SILENCIADA') addEvento('Alarma silenciada', 'ok')
        break

      case 'estado/global':
        dispatch({ type: 'ESTADO_GLOBAL', estado: data.estado || data, modo: data.modo })
        break

      default:
        //  Resultados ARM64 
        // Topic: invernadero/G9/arm64/modulo_X_nombre
        if (sub.startsWith('arm64/')) {
          const mod = data.MODULE || ''
          const arm = {}
          const meta = { columna: data.COLUMNA || data.COLUMN || null }

          if (mod === 'WEIGHTED_MEAN')     arm.media      = { val: data.WEIGHTED_MEAN, sum: data.SUM_X, pesos: data.WEIGHT_SUM, ...meta }
          if (mod === 'VARIANCE')          arm.varianza   = { media: data.MEAN, varianza: data.VARIANCE, desv: data.STD_DEV, ...meta }
          if (mod === 'ANOMALY_DETECTION') arm.anomalias  = { cantidad: data.ANOMALIES, riesgo: data.SYSTEM_RISK, media: data.MEAN, ...meta }
          if (mod === 'PREDICTION')        arm.prediccion = { inicial: data.INITIAL_VALUE, final: data.FINAL_VALUE, siguiente: data.NEXT_VALUE, cambio: data.AVG_CHANGE, ...meta }
          if (mod === 'ADVANCED_TREND')    arm.tendencia  = { trend: data.TREND, incrementos: data.INCREMENTS, decrementos: data.DECREMENTS, racha: data.MAX_UP_STREAK, acum: data.ACCUM_DIFF, ...meta }

          if (Object.keys(arm).length) {
            dispatch({ type: 'ARM64', data: arm })
            addEvento(`Resultado ARM64 recibido: ${mod}`, 'ok')
          }
        }
    }
  }, [addEvento])

  // Conectar MQTT 
  useEffect(() => {
    dispatch({ type: 'MQTT_STATUS', connected: false, status: 'Conectando...' })

    const client = mqtt.connect(MQTT_CONFIG.broker, {
      clientId:        MQTT_CONFIG.clientId,
      username:        MQTT_CONFIG.user || undefined,
      password:        MQTT_CONFIG.pass || undefined,
      reconnectPeriod: 3000,
      connectTimeout:  10000,
    })

    client.on('connect', () => {
      dispatch({ type: 'MQTT_STATUS', connected: true, status: 'Conectado' })
      client.subscribe(`${BASE}/#`)
      addEvento('MQTT conectado a broker.emqx.io', 'ok')
    })

    client.on('message', (topic, payload) => {
      parseMensaje(topic, payload.toString())
    })

    client.on('error', (err) => {
      console.error('[MQTT] Error:', err)
      dispatch({ type: 'MQTT_STATUS', connected: false, status: 'Error de conexion' })
    })

    client.on('close', () => {
      dispatch({ type: 'MQTT_STATUS', connected: false, status: 'Reconectando...' })
    })

    clientRef.current = client
    return () => { client.end() }
  }, [parseMensaje, addEvento])

  const setModo = useCallback((modo) => {
    publicar('modo', modo)
    dispatch({ type: 'MODO', modo })
  }, [publicar])

  // Objeto cmd con UNA funcion por accion
  const cmd = {
    riegoArea1On:    () => publicar('riego_area1',  'ON'),
    riegoArea1Off:   () => publicar('riego_area1',  'OFF'),
    riegoArea2On:    () => publicar('riego_area2',  'ON'),
    riegoArea2Off:   () => publicar('riego_area2',  'OFF'),
    toggleRiego1:    () => publicar('riego_area1',  state.riego1 ? 'OFF' : 'ON'),
    toggleRiego2:    () => publicar('riego_area2',  state.riego2 ? 'OFF' : 'ON'),

    ventiladorOn:    () => publicar('ventilador',   'ON'),
    ventiladorOff:   () => publicar('ventilador',   'OFF'),
    toggleVentilador:() => publicar('ventilador',   state.ventilador ? 'OFF' : 'ON'),

    lucesOn:         () => publicar('luces',        'ON'),
    lucesOff:        () => publicar('luces',        'OFF'),
    toggleLuces:     () => publicar('luces',        state.luces ? 'OFF' : 'ON'),

    alarmaOn:        () => publicar('alarma',       'ON'),
    alarmaOff:       () => publicar('alarma',       'OFF'),
    alarmaSilenciar: () => publicar('alarma',       'SILENCIAR'),

    modoAutomatico:  () => setModo('AUTOMATICO'),
    modoManual:      () => setModo('MANUAL'),

    resetEstado:     () => publicar('global',       'RESET'),

    ejecutarArm64:   (modulo, columna) => publicarArm64(modulo, columna),
  }

  return (
    <Ctx.Provider value={{ state, cmd, publicar, setModo, addEvento }}>
      {children}
    </Ctx.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export const useInvernadero = () => useContext(Ctx)
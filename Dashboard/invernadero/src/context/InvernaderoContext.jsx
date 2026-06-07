import {
  createContext,
  useReducer,
  useEffect,
  useRef,
  useCallback,
} from 'react'
import mqtt from 'mqtt'
import { MQTT_CONFIG, TOPICS, BASE } from '../lib/config'

/* 
   Estado inicial
    */
const initialState = {
  // Conexion
  mqttConnected: false,
  mqttStatus:    'Desconectado',

  // Sensores
  temp:   null,
  hum:    null,
  luz:    null,
  gas:    null,
  suelo1: null,
  suelo2: null,

  // Actuadores
  riego1:     false,
  riego2:     false,
  ventilador: false,
  luces:      false,
  alarma:     false,
  bomba:      false,

  // Estado global
  estadoGlobal: 'NORMAL',
  modo:         'AUTOMATICO',

  // Historico (max 30 puntos)
  histTemp:   [],
  histHum:    [],
  histSuelo1: [],
  histSuelo2: [],
  histLuz:    [],
  histGas:    [],
  histLabels: [],

  // Eventos y comandos
  eventos:   [],
  comandos:  [],

  // ARM64
  arm64: {
    media:    null,
    varianza: null,
    anomalias: null,
    prediccion: null,
    tendencia: null,
  },

  // Contador
  totalLecturas: 0,
  ultimaLectura: null,
}

/* 
   Reducer
    */
function reducer(state, action) {
  switch (action.type) {

    case 'MQTT_STATUS':
      return { ...state, mqttConnected: action.connected, mqttStatus: action.status }

    case 'SENSOR': {
      const { key, valor } = action
      const now    = new Date().toLocaleTimeString('es-GT', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      const hKey   = 'hist' + key.charAt(0).toUpperCase() + key.slice(1)
      const labels = state.histLabels.length >= 30
        ? [...state.histLabels.slice(1), now]
        : [...state.histLabels, now]
      const hist = state[hKey]
        ? (state[hKey].length >= 30 ? [...state[hKey].slice(1), valor] : [...state[hKey], valor])
        : [valor]

      return {
        ...state,
        [key]:          valor,
        [hKey]:         hist,
        histLabels:     labels,
        totalLecturas:  state.totalLecturas + 1,
        ultimaLectura:  now,
      }
    }

    case 'ACTUADOR':
      return { ...state, [action.key]: action.valor }

    case 'ESTADO_GLOBAL':
      return { ...state, estadoGlobal: action.estado, modo: action.modo || state.modo }

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
      return { ...state, arm64: { ...state.arm64, ...action.data } }

    default:
      return state
  }
}

/*  
   Context
    */
   
const Ctx = createContext(null)

export function InvernaderoProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState)
  const clientRef         = useRef(null)

  /*  Helpers  */
  const addEvento = useCallback((texto, tipo = 'ok') => {
    dispatch({
      type: 'EVENTO',
      evento: {
        id:     Date.now(),
        texto,
        tipo,
        hora:   new Date().toLocaleTimeString('es-GT', { hour: '2-digit', minute: '2-digit' }),
      },
    })
  }, [])

  /* sParsear mensaje MQTT  */
  const parseMensaje = useCallback((topic, payload) => {
    let data
    try   { data = JSON.parse(payload) }
    catch { data = { valor: payload }  }

    const sub = topic.replace(BASE + '/', '')

    // Sensores
    if (sub === 'sensores/temperatura')          { dispatch({ type: 'SENSOR', key: 'temp',   valor: data.valor }); if (data.estado === 'ALTA') addEvento(`Temperatura alta: ${data.valor}°C`, 'warn') }
    else if (sub === 'sensores/humedad_ambiente'){ dispatch({ type: 'SENSOR', key: 'hum',    valor: data.valor }) }
    else if (sub === 'sensores/luz')             { dispatch({ type: 'SENSOR', key: 'luz',    valor: data.valor }) }
    else if (sub === 'sensores/gas')             {
      dispatch({ type: 'SENSOR', key: 'gas', valor: data.valor })
      if (data.estado === 'GAS_EMERGENCIA') addEvento(`Gas EMERGENCIA: ${data.valor} ppm`, 'danger')
      else if (data.estado === 'GAS_ADVERTENCIA') addEvento(`Gas ADVERTENCIA: ${data.valor} ppm`, 'warn')
    }
    else if (sub === 'sensores/humedad_suelo_area1') { dispatch({ type: 'SENSOR', key: 'suelo1', valor: data.valor }); if (data.estado === 'SECO') addEvento('Suelo Area 1 SECO — activando riego', 'warn') }
    else if (sub === 'sensores/humedad_suelo_area2') { dispatch({ type: 'SENSOR', key: 'suelo2', valor: data.valor }); if (data.estado === 'SECO') addEvento('Suelo Area 2 SECO — activando riego', 'warn') }

    // Actuadores
    else if (sub === 'actuadores/riego_area1')  { dispatch({ type: 'ACTUADOR', key: 'riego1',     valor: data.bomba === true || data.estado === 'ON' }); if (data.bomba) addEvento('Riego Area 1 activado', 'ok') }
    else if (sub === 'actuadores/riego_area2')  { dispatch({ type: 'ACTUADOR', key: 'riego2',     valor: data.bomba === true || data.estado === 'ON' }); if (data.bomba) addEvento('Riego Area 2 activado', 'ok') }
    else if (sub === 'actuadores/ventilador')   { dispatch({ type: 'ACTUADOR', key: 'ventilador', valor: data.activo === true || data.estado === 'ON' }) }
    else if (sub === 'actuadores/luces')        { dispatch({ type: 'ACTUADOR', key: 'luces',      valor: data.activo === true || data.estado === 'ON' }) }
    else if (sub === 'actuadores/alarma')       { dispatch({ type: 'ACTUADOR', key: 'alarma',     valor: data.buzzer === true || data.estado === 'ON' }); if (data.buzzer) addEvento('ALARMA activada', 'danger') }

    // Estado global
    else if (sub === 'estado/global') {
      dispatch({ type: 'ESTADO_GLOBAL', estado: data.estado || data, modo: data.modo })
    }

    // ARM64
    else if (sub.startsWith('arm64/')) {
      const mod = data.MODULE || ''
      const arm = {}
      if (mod === 'WEIGHTED_MEAN')     arm.media     = { val: data.WEIGHTED_MEAN, sum: data.SUM_X, pesos: data.WEIGHT_SUM }
      if (mod === 'VARIANCE')          arm.varianza  = { media: data.MEAN, varianza: data.VARIANCE, desv: data.STD_DEV }
      if (mod === 'ANOMALY_DETECTION') arm.anomalias = { cantidad: data.ANOMALIES, riesgo: data.SYSTEM_RISK, media: data.MEAN }
      if (mod === 'PREDICTION')        arm.prediccion = { inicial: data.INITIAL_VALUE, final: data.FINAL_VALUE, siguiente: data.NEXT_VALUE, cambio: data.AVG_CHANGE }
      if (mod === 'ADVANCED_TREND')    arm.tendencia  = { trend: data.TREND, incrementos: data.INCREMENTS, decrementos: data.DECREMENTS, racha: data.MAX_UP_STREAK, acum: data.ACCUM_DIFF }
      if (Object.keys(arm).length) dispatch({ type: 'ARM64', data: arm })
    }
  }, [addEvento])

  /* Conectar MQTT  */
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

    client.on('error', () => {
      dispatch({ type: 'MQTT_STATUS', connected: false, status: 'Error de conexion' })
    })

    client.on('disconnect', () => {
      dispatch({ type: 'MQTT_STATUS', connected: false, status: 'Reconectando...' })
    })

    clientRef.current = client
    return () => { client.end() }
  }, [parseMensaje, addEvento])

  /* Publicar comando  */
  const publicar = useCallback((actuador, cmd) => {
    const client = clientRef.current
    if (!client?.connected) return

    const payload = JSON.stringify({
      actuador,
      cmd,
      origen: 'dashboard',
      ts:     Date.now(),
    })
    client.publish(TOPICS.REMOTO, payload)

    dispatch({
      type: 'COMANDO',
      comando: {
        id:       Date.now(),
        hora:     new Date().toLocaleTimeString('es-GT', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        actuador,
        cmd,
        origen:  'Dashboard',
      },
    })
    addEvento(`Comando: ${actuador} → ${cmd}`, 'ok')
  }, [addEvento])

  const setModo = useCallback((modo) => {
    publicar('modo', modo)
    dispatch({ type: 'MODO', modo })
  }, [publicar])

  return (
    <Ctx.Provider value={{ state, publicar, setModo, addEvento }}>
      {children}
    </Ctx.Provider>
  )
}

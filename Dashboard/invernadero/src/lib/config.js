
export const MQTT_CONFIG = {
  broker:   'wss://broker.emqx.io:8084/mqtt',
  clientId: 'G9_dashboard_' + Math.random().toString(36).slice(2, 8),
  user:     '',
  pass:     '',
}

export const BASE  = 'invernadero/G9'

export const TOPICS = {
  // Sensores
  TEMP:    `${BASE}/sensores/temperatura`,
  HUM:     `${BASE}/sensores/humedad_ambiente`,
  SUELO1:  `${BASE}/sensores/humedad_suelo_area1`,
  SUELO2:  `${BASE}/sensores/humedad_suelo_area2`,
  LUZ:     `${BASE}/sensores/luz`,
  GAS:     `${BASE}/sensores/gas`,

  // Actuadores
  RIEGO:   `${BASE}/actuadores/riego`,
  RIEGO1:  `${BASE}/actuadores/riego_area1`,
  RIEGO2:  `${BASE}/actuadores/riego_area2`,
  VENT:    `${BASE}/actuadores/ventilador`,
  LUCES:   `${BASE}/actuadores/luces`,
  ALARMA:  `${BASE}/actuadores/alarma`,

  // Estado y control
  GLOBAL:  `${BASE}/estado/global`,
  REMOTO:  `${BASE}/control/remoto`,
  MANUAL:  `${BASE}/control/manual`,
  ARM64:   `${BASE}/arm64`,
}

export const THRESHOLDS = {
  TEMP_ALTA:   30,
  HUM_BAJA:    40,
  HUM_ALTA:    80,
  LUZ_BAJA:    300,
  GAS_WARN:    200,
  GAS_EMRG:    400,
  SUELO_SECO:  35,
  SUELO_SAT:   80,
}
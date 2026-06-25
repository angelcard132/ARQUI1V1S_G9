const int LUZ_PIN             = A0;
const int GAS_PIN             = A1;
const int SUELO_PIN           = A2;
const int PIN_RELE_BOMBA      = 7;
const int PIN_RELE_VENTILADOR = 8;
const int PIN_BUZZER          = 9;

const int NUM_MUESTRAS = 10;
bool calentamientoListo = false;  // Flag de calentamiento

int leerPromedio(int pin, int muestras) {
  long suma = 0;
  for (int i = 0; i < muestras; i++) {
    suma += analogRead(pin);
    delay(10);
  }
  return suma / muestras;
}

void setup() {
  Serial.begin(9600);

  pinMode(PIN_RELE_BOMBA,      OUTPUT);
  pinMode(PIN_RELE_VENTILADOR, OUTPUT);
  pinMode(PIN_BUZZER,          OUTPUT);

  digitalWrite(PIN_RELE_BOMBA,      HIGH);
  digitalWrite(PIN_RELE_VENTILADOR, HIGH);
  digitalWrite(PIN_BUZZER,          LOW);

  // ── CALENTAMIENTO SENSOR DE GAS (2 minutos) ──
  Serial.println("CALENTANDO_GAS");
  unsigned long inicio = millis();
  unsigned long duracion = 120000; // 2 minutos en ms

  while (millis() - inicio < duracion) {
    // Seguir atendiendo comandos durante el calentamiento
    while (Serial.available() > 0) {
      char cmd = Serial.read();
      switch (cmd) {
        case 'A': digitalWrite(PIN_RELE_BOMBA, LOW);        Serial.println("BOMBA:ON");        break;
        case 'B': digitalWrite(PIN_RELE_BOMBA, HIGH);       Serial.println("BOMBA:OFF");       break;
        case 'C': digitalWrite(PIN_RELE_VENTILADOR, LOW);   Serial.println("VENTILADOR:ON");   break;
        case 'D': digitalWrite(PIN_RELE_VENTILADOR, HIGH);  Serial.println("VENTILADOR:OFF");  break;
        case 'E': tone(PIN_BUZZER, 1000);                   Serial.println("BUZZER:ON");       break;
        case 'F': noTone(PIN_BUZZER);                       Serial.println("BUZZER:OFF");      break;
      }
    }

    // Reportar tiempo restante cada 10 segundos
    unsigned long transcurrido = millis() - inicio;
    unsigned long restante = (duracion - transcurrido) / 1000;
    if (transcurrido % 10000 < 100) {
      Serial.print("CALENTANDO:");
      Serial.print(restante);
      Serial.println("s");
    }

    delay(100);
  }

  calentamientoListo = true;
  Serial.println("LISTO");
}

void loop() {
  // ── COMANDOS DESDE RASPBERRY PI ──
  while (Serial.available() > 0) {
    char cmd = Serial.read();
    switch (cmd) {
      case 'A':
        digitalWrite(PIN_RELE_BOMBA, LOW);
        Serial.println("BOMBA:ON");
        break;
      case 'B':
        digitalWrite(PIN_RELE_BOMBA, HIGH);
        Serial.println("BOMBA:OFF");
        break;
      case 'C':
        digitalWrite(PIN_RELE_VENTILADOR, LOW);
        Serial.println("VENTILADOR:ON");
        break;
      case 'D':
        digitalWrite(PIN_RELE_VENTILADOR, HIGH);
        Serial.println("VENTILADOR:OFF");
        break;
      case 'E':
        tone(PIN_BUZZER, 1000);
        Serial.println("BUZZER:ON");
        break;
      case 'F':
        noTone(PIN_BUZZER);
        Serial.println("BUZZER:OFF");
        break;
    }
  }

  // ── LECTURA Y REPORTE DE SENSORES ──
  int luz   = leerPromedio(LUZ_PIN,   NUM_MUESTRAS);
  int gas   = leerPromedio(GAS_PIN,   NUM_MUESTRAS);
  int suelo = leerPromedio(SUELO_PIN, NUM_MUESTRAS);

  Serial.print("LUZ:");
  Serial.print(luz);
  Serial.print(",GAS:");
  Serial.print(gas);
  Serial.print(",SUELO:");
  Serial.println(suelo);

  delay(500);
}
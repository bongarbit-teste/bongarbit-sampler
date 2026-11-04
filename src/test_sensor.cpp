/*
 * IR reflective distance sensor diagnostic sketch (env: sensor_test) -
 * no audio, no SD, no buttons.
 *
 * Reads the sensor's analog output on GPIO8 (ADC1_CH7, safe with Wi-Fi) and
 * prints, every PRINT_INTERVAL_MS:
 *
 *   t:<ms since boot>,raw:<0-4095>,avg:<0-4095>,mv:<millivolts>,min:<..>,max:<..>
 *
 *  - t:   milliseconds since boot (the time axis for tools/plot_sensor.py)
 *  - raw: a single ADC reading
 *  - avg: mean of AVG_SAMPLES readings (smooths the noise)
 *  - mv:  avg converted to millivolts using the chip's ADC calibration
 *  - min/max: lowest/highest avg seen since boot (send any char over Serial
 *    to reset them) - handy to find the range between "far" and "touching"
 *
 * The "name:value,name:value" format also works directly in a serial
 * plotter. Record + plot each test with: python3 tools/plot_sensor.py
 * Build/upload: pio run -e sensor_test -t upload
 */
#include <Arduino.h>

#define SENSOR_PIN        8
#define AVG_SAMPLES       16
#define PRINT_INTERVAL_MS 50

uint16_t minAvg = 4095, maxAvg = 0;

void setup() {
  Serial.begin(115200);
  // Native USB CDC: wait (up to 3 s) for the monitor, else the first lines are lost
  uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 3000) delay(10);
  delay(200);
  analogSetPinAttenuation(SENSOR_PIN, ADC_11db); // full ~0-3.1 V range
  Serial.printf("Sensor test ready: reading GPIO%d every %d ms.\n", SENSOR_PIN, PRINT_INTERVAL_MS);
}

void loop() {
  static uint32_t lastPrint = 0;
  if (millis() - lastPrint < PRINT_INTERVAL_MS) return;
  lastPrint = millis();

  if (Serial.available()) { // any key resets the range
    while (Serial.available()) Serial.read();
    minAvg = 4095; maxAvg = 0;
  }

  uint16_t raw = analogRead(SENSOR_PIN);
  uint32_t sum = 0;
  for (uint8_t i = 0; i < AVG_SAMPLES; i++) sum += analogRead(SENSOR_PIN);
  uint16_t avg = sum / AVG_SAMPLES;
  if (avg < minAvg) minAvg = avg;
  if (avg > maxAvg) maxAvg = avg;

  Serial.printf("t:%lu,raw:%u,avg:%u,mv:%u,min:%u,max:%u\n",
                (unsigned long)millis(), raw, avg,
                (unsigned)analogReadMilliVolts(SENSOR_PIN), minAvg, maxAvg);
}

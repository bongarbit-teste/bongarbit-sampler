/*
 * Piezo diagnostic sketch (env: piezo_test) - no audio, no SD.
 *
 * Pressing button i (GPIO 6/5/4 = B1/B2/B3) records every ADC reading of
 * piezo i (GPIO 7/2/1 = P1/P2/P3) for PIEZO_WINDOW_MS, then dumps them as CSV
 * over Serial once the window closes (dumping earlier would delay sampling):
 *
 *   PZ,<piezo>,<hit>,<t_us>,<value>      one line per reading
 *   PZEND,<piezo>,<hit>,<n_samples>      end of that window
 *
 * Plot with: python3 tools/plot_piezo.py /dev/cu.usbmodemXXXX
 * Build/upload: pio run -e piezo_test -t upload
 */
#include <Arduino.h>
#include <Bounce2.h>

#define BUTTON_COUNT 3
#define BUTTON_DEBOUNCE_MS 30
#define PIEZO_WINDOW_MS 30
#define PIEZO_MAX_SAMPLES 2048

const uint8_t buttonPins[BUTTON_COUNT] = {6, 5, 4};  // B1, B2, B3
const uint8_t piezoPins[BUTTON_COUNT]  = {7, 2, 1};  // P1, P2, P3 (ADC1: safe with Wi-Fi)

Bounce   buttonBounce[BUTTON_COUNT];
bool     piezoSampling[BUTTON_COUNT] = {false, false, false};
uint32_t piezoStartUs[BUTTON_COUNT]  = {0, 0, 0};
uint16_t piezoMax[BUTTON_COUNT]      = {0, 0, 0};
uint32_t piezoT[BUTTON_COUNT][PIEZO_MAX_SAMPLES];
uint16_t piezoV[BUTTON_COUNT][PIEZO_MAX_SAMPLES];
uint16_t piezoN[BUTTON_COUNT]        = {0, 0, 0};
uint32_t piezoHit[BUTTON_COUNT]      = {0, 0, 0};

void setup() {
  Serial.begin(115200);
  delay(1000);
  for (uint8_t i = 0; i < BUTTON_COUNT; i++) {
    buttonBounce[i].attach(buttonPins[i], INPUT_PULLUP);
    buttonBounce[i].interval(BUTTON_DEBOUNCE_MS);
  }
  Serial.println("Piezo test ready: press button 1/2/3 to capture piezo 1/2/3.");
}

void loop() {
  for (uint8_t i = 0; i < BUTTON_COUNT; i++) {
    buttonBounce[i].update();
    if (piezoSampling[i]) {
      uint16_t v = analogRead(piezoPins[i]);
      uint32_t t = micros() - piezoStartUs[i];
      if (v > piezoMax[i]) piezoMax[i] = v;
      if (piezoN[i] < PIEZO_MAX_SAMPLES) {
        piezoT[i][piezoN[i]] = t;
        piezoV[i][piezoN[i]] = v;
        piezoN[i]++;
      }
      if (t >= PIEZO_WINDOW_MS * 1000UL) {
        piezoSampling[i] = false;
        for (uint16_t k = 0; k < piezoN[i]; k++) {
          Serial.printf("PZ,%u,%lu,%lu,%u\n", i + 1, (unsigned long)piezoHit[i],
                        (unsigned long)piezoT[i][k], piezoV[i][k]);
        }
        Serial.printf("PZEND,%u,%lu,%u\n", i + 1, (unsigned long)piezoHit[i], piezoN[i]);
        Serial.printf("Piezo %u (GPIO%u): max = %u in %u ms after button %u\n",
                      i + 1, piezoPins[i], piezoMax[i], PIEZO_WINDOW_MS, i + 1);
      }
    }
    if (buttonBounce[i].fell()) {
      piezoN[i]        = 0;
      piezoHit[i]++;
      piezoMax[i]      = 0;
      piezoStartUs[i]  = micros();
      piezoSampling[i] = true;
    }
  }
}

#include <Adafruit_NeoPixel.h>
#include <iarduino_VCC.h>
#include "hsv.h"

#define LED_PIN 6
#define LED_COUNT 12
#define LED_BRIGHTNESS 10           // Set to 0 for darkest and 255 for brightest

#define MEASURE_GP2Y10_PIN 0        // Pin A0
#define LED_GP2Y10_PIN 7            // Pin D7
#define SAMPLING_TIME_GP2Y10 280
#define DELTA_TIME_GP2Y10 40
#define SLEEP_TIME_GP2Y10 9680

#define FIX_POWER_VOLTAGE 5.103

float dustDensity = 0;

bool loading_work = true;
int position = 0;

int requestCounter = 0;

Adafruit_NeoPixel strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  Serial.begin(115200);
  strip.setBrightness(LED_BRIGHTNESS);
  strip.begin();
  strip.show();

  pinMode(LED_GP2Y10_PIN, OUTPUT);

  float inVoltage = analogCalc_1V1(FIX_POWER_VOLTAGE);
  analogSave_1V1( inVoltage );

  TCCR1A = 0;
  TCCR1B = 0;
  TCCR1B = bit(CS12) | bit(CS10);       // Set prescalar of timer 1 to 1024  
  TIMSK1 = bit(OCIE1A);                 // Enable compare match A on timer 1
  OCR1A = 15624;
  sei();                                // Enable back the interrupts
}

void updateDustInfo() {
  // Info from http://www.howmuchsnow.com/arduino/airquality/

  digitalWrite(LED_GP2Y10_PIN, LOW); // Power on the LED
  delayMicroseconds(SAMPLING_TIME_GP2Y10);

  float voMeasured = analogRead(MEASURE_GP2Y10_PIN); // Read the dust value

  delayMicroseconds(DELTA_TIME_GP2Y10);
  digitalWrite(LED_GP2Y10_PIN, HIGH); // Turn the LED off
  delayMicroseconds(SLEEP_TIME_GP2Y10);

  // 0 - 5V mapped to 0 - 1023 integer values
  // Recover voltage
  float vRef = analogRead_VCC();
  float calcVoltage = voMeasured * (vRef / 1024.0);
  dustDensity = 170 * calcVoltage - 0.1; // ug/m3

  // Serial.print(calcVoltage);
  // Serial.print(" ");
  //Serial.println(dustDensity);

  //Serial.println( "volts: " +  String(calcVoltage) + " mg/m3: " + String(dustDensity) );
}

int getRignIndex(int index) {
  if (index >= 0) {
    return index;
  } else {
    return LED_COUNT - abs(index);
  }
}

void loading() {
  int led[] = {255, 224, 193, 162, 131, 100, 69, 38, 7, 0, 0, 0};
  for (int k = 0; k < LED_COUNT; k++) {
    for (int i = 0; i < LED_COUNT; i++) {
      uint8_t color_r = strip.gamma8(i * (255 / LED_COUNT));
      strip.setPixelColor((i + position) % LED_COUNT, getPixelColorHsv(i, 255*2, 255, color_r));
    }
    strip.show();
    position++;
    position %= LED_COUNT;
    delay(50);
  }
}

void heil() {
  int smooth = 10;
  for (int k = 0; k < smooth; k++) {
    for (int i = 0; i < LED_COUNT; i++) {
      strip.setPixelColor(i, 0, 255 * k / smooth, 0);
    }
    strip.show();
    delay(50);
  }
  for (int k = smooth; k > 0; k--) {
    for (int i = 0; i < LED_COUNT; i++) {
      strip.setPixelColor(i, 0, 255 * k / smooth, 0);
    }
    strip.show();
    delay(50);
  }
}

void clear() {
  strip.clear();
  strip.show();
}

void loop() {
  if (loading_work == true) {
    loading();
    clear();
  }

  if (Serial.available() > 0) {
    String incomingMessage = Serial.readString();
    //Serial.print(incomingMessage);

    incomingMessage.replace("\r\n", "");

    if (incomingMessage == "loading_end") {
      loading_work = false;
    } else if (incomingMessage == "loading") {
      loading();
    } else if (incomingMessage == "heil") {
      heil();
    } else if (incomingMessage == "data") {
      requestCounter++;
      Serial.println("{\"request_number\":" + String(requestCounter) + ",\"dust\":" + String(dustDensity) + "}");
      //Serial.write("{\"request_number\":2,\"dust\":409.78}");
    }

    clear();
  }
}

ISR(TIMER1_COMPA_vect) {
  TCNT1 = 0;  // Reset the counter
  updateDustInfo();
}
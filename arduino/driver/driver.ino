#include <Adafruit_NeoPixel.h>
#include "hsv.h"

#define LED_PIN 6
#define LED_COUNT 12
#define LED_BRIGHTNESS 10     // Set to 0 for darkest and 255 for brightest

bool loading_work = true;
int position = 0;

Adafruit_NeoPixel strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  Serial.begin(9600);
  strip.setBrightness(LED_BRIGHTNESS);
  strip.begin();
  strip.show();

  //loading();
  //clear();
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
    Serial.print(incomingMessage);

    incomingMessage.replace("\r\n", "");

    if (incomingMessage == "loading_end") {
      loading_work = false;
    } else if (incomingMessage == "loading") {
      loading();
    } else if (incomingMessage == "heil") {
      heil();
    } else if (incomingMessage == "data") {
      Serial.write("null");
    }

    clear();
  }
}
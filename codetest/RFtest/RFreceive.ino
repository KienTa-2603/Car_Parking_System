#include <SPI.h>
#include <nRF24L01.h>
#include <RF24.h>

RF24 radio(15, 14); // CE, CSN pins (ESP32 uses hardware SPI)
const uint8_t address[6] = "00001";

void setup() {
  Serial.begin(115200);
  radio.begin();
  radio.openReadingPipe(0, address);
  radio.setChannel(100);
  radio.setDataRate(RF24_2MBPS);
  radio.enableDynamicPayloads();
  radio.startListening();
}

void loop() {
  if (radio.available()) {
    char msg[32];
    radio.read(&msg, sizeof(msg));
    Serial.println(msg);
  }
}
#include <SPI.h>
#include <nRF24L01.h>
#include <RF24.h>
RF24 radio(7, 8);
const uint8_t address[6] = "00001";

void setup() {
  radio.begin();
  radio.openWritingPipe(address);
  radio.setChannel(100);
  radio.setDataRate(RF24_2MBPS);
  radio.enableDynamicPayloads();
  radio.stopListening();
}

void loop() {
  char msg[] = "Test Message";
  radio.write(&msg, sizeof(msg));
  delay(1000);
}
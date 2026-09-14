#include <Wire.h>
#define QMC5883L_ADDRESS 0x0D

void setup() {
  Serial.begin(115200);
  Wire.begin();
  if(!qmc5883lInit()) {
    Serial.println("QMC5883L initialization failed!");
    while(1);
  }
}

bool qmc5883lInit() {
  byte id = readRegister(0x0F);
  return id == 0x48;
}

int16_t readRegister(uint8_t reg) {
  Wire.beginTransmission(QMC5883L_ADDRESS);
  Wire.write(reg);
  Wire.endTransmission(); 
  Wire.requestFrom(QMC5883L_ADDRESS, 2);
  return (Wire.read() << 8) | Wire.read();
}

void loop() {
  int16_t x = readRegister(0x00);
  int16_t y = readRegister(0x02);
  int16_t z = readRegister(0x04);
  Serial.printf("X: %d, Y: %d, Z: %d\n", x, y, z);
  delay(100);
}
#include <Arduino.h>
#include <Wire.h>
#include <MPU6050_light.h>
#include <ArduinoJson.h>

MPU6050 mpu(Wire);

const char* device_id = "MPU6050_001";

void setupMPU();
void transmitData();

void setup(){
  Serial.begin(9600);
  delay(2000); // wait for serial to initialize
  Wire.begin();
  setupMPU();
}

void loop(){
  mpu.update();
  transmitData();
  delay(1000);
}

void setupMPU(){
  byte status = mpu.begin();
  if (status != 0) {
    Serial.println("{\"error\":\"MPU6050 not connected\"}");
    while (true){
      delay(1000);
    }
  }
  mpu.calcOffsets();
}

void transmitData(){
  float angle = mpu.getAccAngleX(); // REMEMBER TO CHANGE IF WRONG RIRECTION

  if (isnan(angle)) {
    Serial.println("{\"error\":\"Failed to read angle\"}");
    return;
  }

  StaticJsonDocument<200> doc;
  doc["timestamp"] = millis();
  doc["angle"] = angle;
  doc["device_id"] = device_id;

  serializeJson(doc, Serial);
  Serial.println();
}

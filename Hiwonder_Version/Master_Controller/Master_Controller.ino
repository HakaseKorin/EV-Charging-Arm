#include "Config.h"
#include "Hiwonder.hpp"
#include "Robot_arm.hpp"
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>
#include <string>

#define SERVICE_UUID        "12345678-1234-5678-1234-56789abcdef0"
#define CHARACTERISTIC_UUID "12345678-1234-5678-1234-56789abcdef1"

LeArm_t arm;

BusServo_t claw;          // servo 1
BusServo_t joint;         // servo 4
BusServo_t claw_joint;    // servo 2
BusServo_t claw_swivel;   // servo 3
BusServo_t base;          // servo 5
BusServo_t base_swivel;   // servo 6
Button_t button;

#define SERVOSTEP         15
int claw_angle =          0;  //1
int joint_angle =         0;  //4
int claw_joint_angle =    0;  //2
int claw_swivel_angle =   0;  //3
int base_angle =          0;  //5
int base_swivel_angle =   0;  //6

volatile uint8_t pendingCommand = 0;
String correction = "";

class MyCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *pCharacteristic) {

    String rx = pCharacteristic->getValue();

    if (rx.length() == 0) return;

    Serial.print("Received data: ");
    Serial.println(rx.c_str());

    if (rx.length() == 1) {
      pendingCommand = rx[0];
      Serial.printf("Stored command: %d\n", pendingCommand);
    } else {
      Serial.println("Multi-byte command detected");
      correction = rx;
      Serial.println(correction);
    }
  }
};

void setup() {
  delay(1000);
  pinMode(IO_BLE_CTL, OUTPUT);
  digitalWrite(IO_BLE_CTL, LOW);  // Set the Bluetooth control pin to low to cut off the Bluetooth module power (设置蓝牙控制引脚为低电平时，断开蓝牙模块电源)
  
  arm.init();
  Serial1.begin(115200 ,SERIAL_8N1 , BUS_RX , BUS_TX);
  claw.init(&Serial1);
  joint.init(&Serial1);
  claw_joint.init(&Serial1);
  claw_swivel.init(&Serial1);
  base.init(&Serial1);
  base_swivel.init(&Serial1);
  button.init();
  
  Serial.begin(9600);

  // BLE SERVER initializes Server
  BLEDevice::init("ESP32_Server");
  BLEServer *pServer = BLEDevice::createServer();
  BLEService *pService = pServer->createService(SERVICE_UUID);

  BLECharacteristic *pCharacteristic = pService->createCharacteristic(
    CHARACTERISTIC_UUID,
    BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_READ
  );

  pCharacteristic->setCallbacks(new MyCallbacks());

  pService->start();
  BLEDevice::startAdvertising();

  Serial.println("BLE Server Ready. Waiting for client writes...");

  delay(2000);
}

void coord_movement(int x, int y, int z) {
  // uint8_t coordinate_set(float target_x,float target_y,float target_z,float pitch,float min_pitch,float max_pitch,uint32_t time);
  arm.coordinate_set(x,y,z,0,-90,180,1000);
  delay(2000);
}

void pickup(int x, int y) {
  // claw occasionally doesnt completely close or open, best guess is a faulty wire/connection
  arm.coordinate_set(x,y,-6,0,-90,90,1000);
  delay(3000);
  claw.set_angle(1,180,100);
  delay(6000); // extra delay is to ensure that its able to grab the object
  arm.coordinate_set(x,y,20,0,-90,90,1000);
  delay(3000);
}

void pickup_from_sensor(int x, int y) {
  arm.coordinate_set(x,y,0,0,-90,90,1000);
  delay(3000);
  claw.set_angle(1,180,100);
  delay(6000); // extra delay is to ensure that its able to grab the object
  arm.coordinate_set(x,y,20,0,-90,90,1000);
  delay(3000);
}

void dropoff(int x, int y) {
  arm.coordinate_set(x,y,20,0,-90,90,1000);
  delay(3000);
  arm.coordinate_set(x,y,-5,0,-90,90,1000);
  delay(3000);
  claw.set_angle(1,0,100);
  delay(3000);
  arm.coordinate_set(x,y,20,0,-90,90,1000);
  delay(3000);
}

void retrive(int x, int y) {
  pickup(x,y);
  dropoff(10,0);
}

int getCurrent(int servo_ch) {
  switch(servo_ch) {
    case 1: return claw_angle;
    case 2: return claw_joint_angle;
    case 3: return claw_swivel_angle;
    case 4: return joint_angle;
    case 5: return base_angle;
    case 6: return base_swivel_angle;
    default: return -1;
  }
}

void setCurrent(int servo_ch, int angle) {
  switch(servo_ch) {
    case 1: claw_angle = angle; return; 
    case 2: claw_joint_angle = angle; return;
    case 3: claw_swivel_angle = angle; return;
    case 4: joint_angle = angle; return;
    case 5: base_angle = angle; return;
    case 6: base_swivel_angle = angle; return;
    default:  return;
  }
}

void movementStepper(int servo_ch, int target_angle) { // !! requires live test
  int current_angle = getCurrent(servo_ch);

  if (current_angle == -1) return; // in case of invalid input

  if (current_angle >= target_angle) {
    for (current_angle >= target_angle; current_angle -= 1;) {
      
      claw_joint.set_angle(servo_ch, current_angle, 100);
      delay(SERVOSTEP);

      if (current_angle == target_angle) { //jank fix
        setCurrent(servo_ch, target_angle);
        return;
      }
    }
    claw_joint.set_angle(servo_ch, target_angle, 100);
    return;
  } else {
    for (current_angle < target_angle; current_angle += 1;) {
      claw_joint.set_angle(servo_ch, current_angle, 100);
      delay(SERVOSTEP);

      if (current_angle == target_angle) { //jank fix
        setCurrent(servo_ch, target_angle);
        return;
      }
    }
    setCurrent(servo_ch, target_angle);
    return;
  }
}

void servoTest() {
  arm.coordinate_set(20,0,20,0,-90,90,1000);
    delay(2000);
    //claw.set_angle(1,180,100);
    arm.coordinate_set(10,0,10,0,-90,90,1000);
    delay(2000);

    arm.coordinate_set(15,0,10,0,-90,90,1000);
    delay(1000);

    arm.coordinate_set(20,0,10,0,-90,90,1000);
    delay(1000);

    arm.coordinate_set(25,0,10,0,-90,90,1000);
    delay(1000);

    arm.coordinate_set(30,0,10,0,-90,90,1000);
    delay(1000);

    arm.coordinate_set(35,0,10,0,-90,90,1000);
    delay(2000);
}

void loop() {
  //arm.coordinate_set(float target_x, float target_y, float target_z, float pitch, float min_pitch, float max_pitch, uint32_t time)
  
  //for opening and closing the claw
  /*
  claw.set_angle(1,0,100);
  delay(2000);
  claw.set_angle(1,180,100);
  delay(6000);
  */
  //servoTest();
  //Serial.println("loop is running..");
  

  if (pendingCommand != 0) {
    uint8_t cmd = pendingCommand;
    Serial.println(pendingCommand);
    pendingCommand = 0;
  }

  if (correction != "" ) {
    int offset = std::atoi(correction.c_str());
    arm.coordinate_set(20,0,20,0,-90,90,1000);
    delay(2000);
    //claw.set_angle(1,180,100);
    arm.coordinate_set(10,0,10,0,-90,90,1000);
    delay(2000);
    
    arm.coordinate_set(15,0,10+offset,0,-90,90,1000);
    delay(1000);

    arm.coordinate_set(20,0,10+offset,0,-90,90,1000);
    delay(1000);

    arm.coordinate_set(25,0,10+offset,0,-90,90,1000);
    delay(1000);

    arm.coordinate_set(30,0,10+offset,0,-90,90,1000);
    delay(1000);

    while (true) {
      arm.coordinate_set(35,0,10+offset,0,-90,90,1000);
      delay(2000);  
    }

  }



  delay(10); // Keeps BLE alive
  

}

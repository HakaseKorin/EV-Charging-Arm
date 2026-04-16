#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

#define SMIN_00         165
#define SMAX_00         430
#define SMIN_01         170
#define SMAX_01         430
#define SMIN_02         75
#define SMAX_02         455

#define SERVO_FREQ      50
#define SERVOSTEP       15

// Tracks current angle pos
int shoulder_angle =    0; // channels 0, 1 servos, 0 is towards upside down claw
int elbow_angle =       0; // channel 2
int wrist_vert =        0; // channel 3
int wrist_horz =        0; // channel 4
int claw =              0; // channel 5

void setup() {
  Serial.begin(9600);
  Serial.println("8 channel Servo test!");

  pwm.begin();

  pwm.setOscillatorFrequency(27000000);
  pwm.setPWMFreq(SERVO_FREQ);  // Analog servos run at ~50 Hz updates

  delay(10);
}

int getCurrent_Servo_Angles(int servo_ch) {
  switch(servo_ch) {
    case 1: return shoulder_angle;
    case 2: return elbow_angle;
    case 3: return wrist_vert;
    case 4: return wrist_horz;
    case 5: return claw;
    default: return -1;
  }
}

void setCurrent_Servo_Angles(int servo_ch, int angle) {
  switch(servo_ch) {
    case 1: shoulder_angle = angle; return;
    case 2: elbow_angle = angle; return;
    case 3: wrist_vert = angle; return;
    case 4: wrist_horz = angle; return;
    case 5: claw = angle; return;
    default:  return;
  }
}

int angleToPulse(int angle, int16_t min, int16_t max) {
  return map(angle, 0, 180, min, max); 
  // lowest 75, highest 525
  //SERVO 1 min 175, max 450 v2, min 165 max 430
  //SERVO 2 min 175 max 455 v2 min 170, max 430
  //SERVO 3 min 75, max 455
}

void readSerial() {
  char c = Serial.read();

  if (c == '<') {
    inputBuffer = "";       // Start new frame
  } 
  else if (c == '>') {
    processMessage(inputBuffer);
  } 
  else {
    inputBuffer += c;
  }
}

bool isNumber(String str) {
  if (str.length() == 0) return false;

  int start = 0;
  if (str[0] == '-') { // negative numbers
    if (str.length() == 1) return false; // only "-" is invalid
    start = 1;
  }

  for (int i = start; i < str.length(); i++) {
    if (!isDigit(str[i])) return false;
  }

  return true;
}

void processMessage(String msg) {
  int sep = msg.indexOf('|');
  String command = msg.substring(0, sep);
  String value   = msg.substring(sep + 1);

  if (command == "MOVE") {
    if (value == "FORWARD") {
      thrustForward();
      Serial.println("<ACK|FORWARD>");
      return;
    } 
  }
  if (command == "SCAN") {
    if (value == "TRUE") {
      thrustForward();
      Serial.println("Socket Detected..")
      Serial.println("<ACK|SCAN>");
      return;
    }
    if (value == "FALSE") {
      Serial.println("No Socket Detected..")
      Serial.println("<ACK|SCAN>");
      return;
    } 
  }
  if (command == "STATE") {
    if (value == "RESET") {
      default_servo();
      Serial.println("<ACK|RESET>");
      return;
    }
    if (value == "SCAN") {
      Serial.println("<REQ|SCAN>");
      return;
    }
  }
  if (command == "ROTATE") {
    if (isNumber(value)) {
      float data = value.toFloat();
      baseRotation(data);
      Serial.println("<ACK|ROTATE>");
      return;
    } 
  }
  if (command == "X") {
    if (isNumber(value)) {
      value = value.toInt();
      Serial.println("<ACK|TRANSFORM>");
      return;
    } 
  }
  if (command == "Y") {
    if (isNumber(value)) {
      value = value.toInt();
      Serial.println("<ACK|TRANSFORM>");
      return;
    } 
  }
  if (command == "CLAW") {
    if (value == "OPEN") {
        //pwm.setPWM(5,0,angleToPulse(90));
      Serial.println("<ACK|GRAB>");
      return;
    }
    if (value == "CLOSE") {
      //pwm.setPWM(5,0,angleToPulse(0));
      Serial.println("<ACK|RELEASE>");
      return;
    }
  }
  
  Serial.println("<ERR|INVALID_INPUT>");
  return;

}

void init_servo() {
  shoulder_angle = 160;
  pwm.setPWM(1, 0, angleToPulse(shoulder_angle, SMIN_00, SMAX_00));

  elbow_angle =       90; // channel 2
  pwm.setPWM(2, 0, angleToPulse(elbow_angle)); // range 0 ~ 165, 0 moves towards claw servo

  wrist_vert =        90; // channel 3
  pwm.setPWM(3, 0, angleToPulse(wrist_vert)); // range 0 ~ 165, 0 moves away from claw servo

  wrist_horz =        87; // channel 4
  pwm.setPWM(4, 0, angleToPulse(wrist_horz)); // range 0 ~ 165, 0 moves towards claw servo

  claw =              0; // channel 5
  //pwm.setPWM(5, 0, angleToPulse(claw)); // 90 is enough to open claw, can go to 180, 0 to close
}

void default_servo() { // 01-50,2-40,3-140,5-90 >> Default pose.
  pwm.setPWM(0, 0, angleToPulse(50, SMIN_00, SMAX_00));
  pwm.setPWM(2, 0, angleToPulse(20, SMIN_02, SMAX_02);
  //pwm.setPWM(3,160); // Servo becomes inactive after using this function
  pwm.setPWM(3, 0, angleToPulse(165, SMIN_02, SMAX_02));
  //pwm.setPWM(4,90);
  //pwm.setPWM(5,90);
}

void maintain_servo() {
  pwm.setPWM(1, 0, angleToPulse(shoulder_angle, SMIN_00, SMAX_00));
  pwm.setPWM(2, 0, angleToPulse(elbow_angle));
  pwm.setPWM(3, 0, angleToPulse(wrist_vert));
  pwm.setPWM(4, 0, angleToPulse(wrist_horz));
  //pwm.setPWM(5, 0, angleToPulse(claw));
}


void servo_test() {
  pwm.setPWM(0, 0, angleToPulse(90, SMIN_00, SMAX_00));
  // Servo 1 is a backup for servo 0
  //pwm.setPWM(1, 0, angleToPulse(90, SMIN_01, SMAX_01));
  pwm.setPWM(2, 0, angleToPulse(90, SMIN_02, SMAX_02));
  pwm.setPWM(3, 0, angleToPulse(0, SMIN_02, SMAX_02));
}

void loop() {
  init_servo();
  delay(5000);
  
  default_servo();
  delay(5000);

  while (true){
    maintain_servo();
    //readSerial();
    delay(3000);
  }

}
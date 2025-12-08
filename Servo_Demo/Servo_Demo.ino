#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// Create PCA9685 object at default address 0x40
Adafruit_PWMServoDriver pca = Adafruit_PWMServoDriver();

// Servo pulse lengths (adjust these for your servos)
#define SERVOMIN        150   // Minimum pulse (0°)
#define SERVOMAX        600   // Maximum pulse (180°)
#define SERVOSTEP       15    // Determines how fast the servos will move

#define L1              18.5  // place holder values for the length of the arms
#define L2              11.5
#define L3              18.5

#define LED             3 // digital pin
#define STEP_PIN 6
#define DIR_PIN  5
#define EN_PIN   7
#define POT_PIN A0

long STEPS_PER_REV = 3200;  // 1/16 microstepping

// Pot rotates 2.25 times for every 1 motor rotation
// So motor_angle = pot_angle / 2.25
float GEAR_RATIO = 1.0 / 2.25;   // = 0.444444...

bool err =              false;
// Tracks current angle pos
int shoulder_angle =    0; // channels 0, 1 servos, 0 is towards upside down claw
int elbow_angle =       0; // channel 2
int wrist_vert =        0; // channel 3
int wrist_horz =        0; // channel 4
int claw =              0; // channel 5

// inverse kinematics variables
float shoulder_theta =  0; // theta1
float elbow_theta =     0; // theta2
float wrist_theta =     0; // theta3

String inputBuffer = "";

bool inverseKinematics(float x, float y, float phi_deg,
float &theta1_deg, float &theta2_deg, float &theta3_deg)
{
float phi = phi_deg * (PI / 180.0); // convert to radians

// 1. Compute wrist position
float wristX = x - L3 * cos(phi);
float wristY = y - L3 * sin(phi);

// 2. Compute D
float D = (wristX*wristX + wristY*wristY - L1*L1 - L2*L2) / (2.0 * L1 * L2);

if (abs(D) > 1.0) return false; // unreachable point

// Two possible elbow angles
float theta2_options[2] = {
    atan2(sqrt(1 - D*D), D),  // elbow-down
    atan2(-sqrt(1 - D*D), D)  // elbow-up
};

for (int i = 0; i < 2; i++) {
    float theta2 = theta2_options[i];

    // 3. Shoulder angle
    float k1 = L1 + L2 * cos(theta2);
    float k2 = L2 * sin(theta2);
    float theta1 = atan2(wristY, wristX) - atan2(k2, k1);

    // 4. Wrist angle
    float theta3 = phi - (theta1 + theta2);

    // Convert to degrees
    float th1_deg = theta1 * 180.0 / PI;
    float th2_deg = theta2 * 180.0 / PI;
    float th3_deg = theta3 * 180.0 / PI;

    // Check servo limits
    if (th1_deg >= 10 && th1_deg <= 160 &&
        th2_deg >= 0  && th2_deg <= 165 &&
        th3_deg >= 0  && th3_deg <= 165) 
    {
        theta1_deg = th1_deg;
        theta2_deg = th2_deg;
        theta3_deg = th3_deg;
        return true;  // valid solution found
    }
}

return false; // no valid solution within limits

}



  void errLight() {
    if (err) digitalWrite(LED, HIGH);
  }

void setup() {
  pinMode(LED, OUTPUT);
  pinMode(STEP_PIN, OUTPUT);
  pinMode(DIR_PIN, OUTPUT);
  pinMode(EN_PIN, OUTPUT);

  digitalWrite(EN_PIN, LOW); // enable driver
  
  Serial.begin(9600);

  pca.begin();
  pca.setPWMFreq(50);  // Standard servo frequency (50 Hz)
  delay(10);
}

long degreesToSteps(float deg) {
  return round((deg / 360.0) * STEPS_PER_REV);
}

void baseRotation(float deg) {
  long steps = degreesToSteps(deg);

  bool dir = steps > 0;
  if (steps < 0) steps = -steps;

  digitalWrite(DIR_PIN, dir ? HIGH : LOW);

  for (long i = 0; i < steps; i++) {
    digitalWrite(STEP_PIN, HIGH);
    delayMicroseconds(800);
    digitalWrite(STEP_PIN, LOW);
    delayMicroseconds(800);
  }
}

// Read real motor angle using pot + gear ratio
float getMotorAngle() {
  int raw = analogRead(POT_PIN);

  // Pot itself rotates 0–360° per rotation
  float potAngle = (raw / 1023.0) * 360.0;

  // Because pot does 2.25 rotations per motor rotation:
  float motorAngle = potAngle * GEAR_RATIO;

  // Keep angle between 0–360
  motorAngle = fmod(motorAngle, 360.0);
  if (motorAngle < 0) motorAngle += 360.0;

  return motorAngle;
}

// Convert angle (0–180°) to PCA9685 pulse width
int angleToPulse(int angle) {
  return map(angle, 0, 180, SERVOMIN, SERVOMAX);
}

int syncR_Base(int angle) {
  int OFFSET = 10; // deviation for certain ranges
  int L_REF = 90; // Servo Channel 0 vertical Angle
  int R_REF = 90; // Servo Channel 1 vertical Angle, issue when completely vertical starts to jitter
  if (angle >= 35)
    OFFSET = 7;
  if (angle >= 85)
    OFFSET = 4;
  if (angle >= 95)
    OFFSET = 0;
    
  return ((R_REF - OFFSET) + (L_REF - angle));
}

int syncL_Base(int angle) {
  int OFFSET = 0; // deviation for certain ranges
  //if (angle >= 80) OFFSET = 0;
  return angle - OFFSET;
}

// moveBase uses servo channels 0 & 1 DO NOT use setPWM on servos 0/1 when fully assembled
void moveBase(int l_servo) { //  range 10~160
  int r_servo = syncR_Base(l_servo);

  if (l_servo > 65)
    l_servo = syncL_Base(l_servo);

  pca.setPWM(0, 0, angleToPulse(l_servo)); 
  pca.setPWM(1, 0, angleToPulse(r_servo));
}

int getCurrent(int servo_ch) {
  switch(servo_ch) {
    case 1: return shoulder_angle;
    case 2: return elbow_angle;
    case 3: return wrist_vert;
    case 4: return wrist_horz;
    case 5: return claw;
    default: return -1;
  }
}

void setCurrent(int servo_ch, int angle) {
  switch(servo_ch) {
    case 1: shoulder_angle = angle; return;
    case 2: elbow_angle = angle; return;
    case 3: wrist_vert = angle; return;
    case 4: wrist_horz = angle; return;
    case 5: claw = angle; return;
    default:  return;
  }
}

void movementStepper(int servo_ch, int target_angle) { // !! requires live test
  int current_angle = getCurrent(servo_ch);

  if (current_angle == -1) return; // in case of invalid input

  if (servo_ch == 1) {
    if (current_angle >= target_angle) {
    for (current_angle >= target_angle; current_angle -= 1;) {
      moveBase(current_angle);
      delay(SERVOSTEP);

      if (current_angle == target_angle) { //jank fix
        setCurrent(servo_ch, target_angle);
        return;
      }
    }
    setCurrent(servo_ch, target_angle);
    return;
  } else {
    for (current_angle < target_angle; current_angle += 1;) {
      moveBase(current_angle);
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

  if (current_angle >= target_angle) {
    for (current_angle >= target_angle; current_angle -= 1;) {
      pca.setPWM(servo_ch, 0, angleToPulse(current_angle));
      delay(SERVOSTEP);

      if (current_angle == target_angle) { //jank fix
        setCurrent(servo_ch, target_angle);
        return;
      }
    }
    setCurrent(servo_ch, target_angle);
    return;
  } else {
    for (current_angle < target_angle; current_angle += 1;) {
      pca.setPWM(servo_ch, 0, angleToPulse(current_angle));
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

void moveArmSimultaneous(int shoulder_target, int elbow_target, int wrist_target, int claw_target) {
// Compute step counts for each servo
int shoulder_steps = abs(shoulder_target - shoulder_angle);
int elbow_steps    = abs(elbow_target - elbow_angle);
int wrist_steps    = abs(wrist_target - wrist_vert);
int claw_steps     = abs(claw_target - claw);

int max_steps = max(shoulder_steps, max(elbow_steps, max(wrist_steps, claw_steps)));

if (max_steps == 0) return; // already at target

// Compute incremental step for each servo
float shoulder_inc = float(shoulder_target - shoulder_angle) / max_steps;
float elbow_inc    = float(elbow_target - elbow_angle) / max_steps;
float wrist_inc    = float(wrist_target - wrist_vert) / max_steps;
float claw_inc     = float(claw_target - claw) / max_steps;

// Move in small increments
for (int i = 1; i <= max_steps; i++) {
    int s = round(shoulder_angle + shoulder_inc * i);
    int e = round(elbow_angle + elbow_inc * i);
    int w = round(wrist_vert + wrist_inc * i);
    int c = round(claw + claw_inc * i);

    // Move each servo
    moveBase(s);                  // shoulder channels 0 & 1
    pca.setPWM(2, 0, angleToPulse(e)); // elbow
    pca.setPWM(3, 0, angleToPulse(w)); // wrist vertical
    pca.setPWM(5, 0, angleToPulse(c)); // claw

    delay(SERVOSTEP); // small delay for smooth motion
}

// Update current angles
shoulder_angle = shoulder_target;
elbow_angle    = elbow_target;
wrist_vert     = wrist_target;
claw           = claw_target;

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

bool isNumber(const std::string& str) {
    try {
        std::stod(str);  // for double; use std::stoi for int
        return true;
    } catch (std::invalid_argument&) {
        return false;
    } catch (std::out_of_range&) {
        return false;
    }
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
  if (command == "STATE") {
    if (value == "RESET") {
      default_servo();
      Serial.println("<ACK|RESET>");
      return;
    }
    if (value == "SCAN") {
      Serial.println("<ACK|SCAN>");
      return;
    }
  }
  if (command == "ROTATE") {
    if (isNumber(value)) {
      baseRotation(value);
      Serial.println("<ACK|ROTATE>");
      return;
    } 
  }
  if (command == "X") {
    if (isNumber(value)) {
      Serial.println("<ACK|TRANSFORM>");
      return;
    } 
  }
  if (command == "Y") {
    if (isNumber(value)) {
      Serial.println("<ACK|TRANSFORM>");
      return;
    } 
  }
  if (command == "CLAW") {
    if (value == "OPEN") {
      pca.setPWM(5,0,angleToPulse(90));
      Serial.println("<ACK|GRAB>");
      return;
    }
    if (value == "CLOSE") {
      pca.setPWM(5,0,angleToPulse(0));
      Serial.println("<ACK|RELEASE>");
      return;
    }
  }
  
  Serial.println("<ERR|INVALID_INPUT>");
  return;

}

void moveKinematics() {
  //movementStepper(1,shoulder_theta);
  //movementStepper(2,elbow_theta);
  //wrist_vert = wrist_theta;
  //pca.setPWM(3, 0, angleToPulse(wrist_vert));
  moveArmSimultaneous(shoulder_theta,elbow_theta,wrist_theta,90);

}

void init_servo() {
  shoulder_angle = 160;
  moveBase(shoulder_angle);

  elbow_angle =       90; // channel 2
  pca.setPWM(2, 0, angleToPulse(elbow_angle)); // range 0 ~ 165, 0 moves towards claw servo

  wrist_vert =        90; // channel 3
  pca.setPWM(3, 0, angleToPulse(wrist_vert)); // range 0 ~ 165, 0 moves away from claw servo

  wrist_horz =        87; // channel 4
  pca.setPWM(4, 0, angleToPulse(wrist_horz)); // range 0 ~ 165, 0 moves towards claw servo

  claw =              0; // channel 5
  pca.setPWM(5, 0, angleToPulse(claw)); // 90 is enough to open claw, can go to 180, 0 to close
}

void default_servo() { // 01-50,2-40,3-140,5-90 >> Default pose.
  movementStepper(1,50);
  movementStepper(2,20);
  //movementStepper(3,160); // Servo becomes inactive after using this function
  wrist_vert = 165;
  pca.setPWM(3, 0, angleToPulse(wrist_vert));
  //movementStepper(4,90);
  movementStepper(5,90);

}

void maintain_servo() {
  moveBase(shoulder_angle);
  pca.setPWM(2, 0, angleToPulse(elbow_angle));
  pca.setPWM(3, 0, angleToPulse(wrist_vert));
  pca.setPWM(4, 0, angleToPulse(wrist_horz));
  pca.setPWM(5, 0, angleToPulse(claw));
}

void thrustForward() {
  //movementStepper(3,90);
  //movementStepper(1,100);
  //movementStepper(2,45);
  moveArmSimultaneous(100,45,90,90);
}

void loop() {

  init_servo();
  delay(5000);
  
  default_servo();
  delay(5000);
  //baseRotation(10); // rotating shoulder
  //delay(10000);
  // moves towards 00, cant move if arm is extended outwards?

  thrustForward();

  // inverse kinematics conclusion, coordinates.. are really weird??
  /*Serial.println("starting kinematics");
  if(inverseKinematics(-23,9,235,shoulder_theta, elbow_theta, wrist_theta)) { // similar to thrustforward
    moveKinematics();
    Serial.println("IK Solution:");
    Serial.print("Theta1 = "); Serial.println(degrees(shoulder_theta));
    Serial.print("Theta2 = "); Serial.println(degrees(elbow_theta));
    Serial.print("Theta3 = "); Serial.println(degrees(wrist_theta));
  } else {
    Serial.println("out of range");
    Serial.print("Theta1 = "); Serial.println(degrees(shoulder_theta));
    Serial.print("Theta2 = "); Serial.println(degrees(elbow_theta));
    Serial.print("Theta3 = "); Serial.println(degrees(wrist_theta));
  }*/
  
  while (true){
    maintain_servo();
    //bool inverseKinematics(float x, float y, float phi_deg,
    //                   float &theta1_deg, float &theta2_deg, float &theta3_deg)

  }
}
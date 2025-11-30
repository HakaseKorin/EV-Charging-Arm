#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// Create PCA9685 object at default address 0x40
Adafruit_PWMServoDriver pca = Adafruit_PWMServoDriver();

// Servo pulse lengths (adjust these for your servos)
#define SERVOMIN        150   // Minimum pulse (0°)
#define SERVOMAX        600   // Maximum pulse (180°)
#define SERVOSTEP       15    // Determines how fast the servos will move

#define L1              10.0  // place holder values for the length of the arms
#define L2              8.0
#define L3              6.0

#define LED             3 // digital pin

bool err =              false;
// Tracks current angle pos
int shoulder_angle =    0; // channels 0, 1 servos
int elbow_angle =       0; // channel 2
int wrist_vert =        0; // channel 3
int wrist_horz =        0; // channel 4
int claw =              0; // channel 5
int shoulder_rot =      0; // later when implemented

// inverse kinematics variables
float shoulder_theta =  0; // theta1
float elbow_theta =     0; // theta2
float wrist_theta =     0; // theta3

bool inverseKinematics(float x, float y, float phi, float &theta1, float &theta2, float &theta3) { // ! requires live test
  // Wrist position
  float wristX = x - L3 * cos(phi);
  float wristY = y - L3 * cos(phi);

  float D = ( (wristX * wristX) +
              (wristY * wristY) -
              (L1 * L1) -
              (L2 * L2) )
            / (2.0 * L1 * L2);
  
  // if |D| > 1 -> no valid solution
  if (abs(D) > 1.0) return false;

  // computing Elbow Theta
  float sinTheta2 = sqrt(1.0 - (D * D));
  float cosTheta2 = D;
  theta2 = atan2(sinTheta2, cosTheta2);

  // computing shoulder theta
  float k1 = L1 + L2 * cos(theta2);
  float k2 = L2 * sin(theta2);

  theta1 = atan2(wristY, wristX) - atan2(k2, k1);

  // computing wrist theta
  theta3 = phi - (theta1 + theta2);

  return true;
}

  void errLight() {
    if (err) digitalWrite(LED, HIGH);
  }

void setup() {
  pinMode(LED, OUTPUT);
  
  Serial.begin(9600);

  pca.begin();
  pca.setPWMFreq(50);  // Standard servo frequency (50 Hz)
  delay(10);
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
void moveBase(int l_servo) { // 160 ~ 10
  int r_servo = syncR_Base(l_servo);

  if (l_servo > 65)
    l_servo = syncL_Base(l_servo);

  pca.setPWM(0, 0, angleToPulse(l_servo)); 
  pca.setPWM(1, 0, angleToPulse(r_servo));
}

void movementStepper(int servo_ch, int current_angle, int target_angle) { // !! requires live test
  if (servo_ch == 0 || servo_ch == 1) {
    if (current_angle >= target_angle) {
    for (current_angle >= target_angle; current_angle -= 1;) {
      moveBase(current_angle);
      delay(SERVOSTEP);
    }
    return;
  } else {
    for (current_angle < target_angle; current_angle += 1;) {
      moveBase(current_angle);
      delay(SERVOSTEP);
    }
    return;
  }
  }

  if (current_angle >= target_angle) {
    for (current_angle >= target_angle; current_angle -= 1;) {
      pca.setPWM(servo_ch, 0, angleToPulse(current_angle));
      delay(SERVOSTEP);
    }
    return;
  } else {
    for (current_angle < target_angle; current_angle += 1;) {
      pca.setPWM(servo_ch, 0, angleToPulse(current_angle));
      delay(SERVOSTEP);
    }
    return;
  }
}

void loop() {

  // inverse kinematics requires test
  // movementStepper requires test
  moveBase(70);
  //delay(5000);

  // Check for the inversed motor
  pca.setPWM(2, 0, angleToPulse(40));  // 165 ~ 0
  pca.setPWM(3, 0, angleToPulse(130));  // 165 ~ 0
  pca.setPWM(4, 0, angleToPulse(90));
  pca.setPWM(5, 0, angleToPulse(0));

}
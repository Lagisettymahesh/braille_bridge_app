// ESP32 + PCA9685: drives one 6-dot Braille cell (dots 1..6 on PCA9685 channels 0..5).
// Receives one byte per cell over USB serial (bits 0..5 = dots 1..6). Needs the
// Adafruit PWM Servo Driver library. Angles must be calibrated for the printed linkage.
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);
const uint16_t SERVO_MIN = 150, SERVO_MAX = 600;   // PWM ticks at 50 Hz
const uint8_t  ANGLE_DOWN[6] = {20, 20, 20, 20, 20, 20};
const uint8_t  ANGLE_UP[6]   = {70, 70, 70, 70, 70, 70};
const uint8_t  BTN_NEXT = 32, BUZZER = 25;

uint16_t angleToTicks(uint8_t a) { return map(a, 0, 180, SERVO_MIN, SERVO_MAX); }

void showCell(uint8_t code) {
  for (uint8_t d = 0; d < 6; d++) {                // stagger moves to limit peak current
    bool up = (code >> d) & 1;
    pwm.setPWM(d, 0, angleToTicks(up ? ANGLE_UP[d] : ANGLE_DOWN[d]));
    delay(40);
  }
}

void setup() {
  Serial.begin(115200);
  Wire.begin();
  pwm.begin();
  pwm.setPWMFreq(50);
  pinMode(BTN_NEXT, INPUT_PULLUP);
  pinMode(BUZZER, OUTPUT);
  showCell(0);                                     // all pins down
}

void loop() {
  if (Serial.available()) {
    uint8_t code = Serial.read() & 0x3F;
    showCell(code);
    tone(BUZZER, 1000, 60);                        // short beep on each new cell
  }
  if (digitalRead(BTN_NEXT) == LOW) {              // tell the PC to send the next cell
    Serial.println("NEXT");
    delay(300);
  }
}

// ==============================================================================
// BRAILLE BRIDGE: ESP32 + PCA9685 1-Cell Refreshable Braille Cell Firmware
// ==============================================================================
// Hardware Architecture:
// - Microcontroller: ESP32 (30-pin / 38-pin DevKit v1)
// - PWM Driver: PCA9685 16-Channel 12-Bit I2C PWM Controller (I2C Address: 0x40)
// - Actuators: 6x Micro-servos (TowerPro SG90 / MG90S) driving tactile dots 1 to 6
//     Channel 0: Dot 1 (Top-Left)
//     Channel 1: Dot 2 (Middle-Left)
//     Channel 2: Dot 3 (Bottom-Left)
//     Channel 3: Dot 4 (Top-Right)
//     Channel 4: Dot 5 (Middle-Right)
//     Channel 5: Dot 6 (Bottom-Right)
// - Input: Tactile advance push-button on GPIO 32 (active LOW with internal pull-up)
// - Output: Tactile feedback buzzer on GPIO 25
//
// ELECTRICAL WARNING:
// - Servos require significant instantaneous stall current (up to 2.5A total).
// - NEVER power the PCA9685 V+ servo rail directly from the ESP32 3.3V or 5V pin!
// - Connect an external 5V / 3A DC regulated power supply to PCA9685 V+ and GND.
// - Ensure ESP32 GND and External 5V Power Supply GND are tied together (Common Ground).
// ==============================================================================

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// I2C Pins for standard ESP32
#define I2C_SDA 21
#define I2C_SCL 22

// Peripherals
#define BTN_NEXT 32
#define BUZZER   25

// PCA9685 instance (default address 0x40)
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

// Servo Calibration Constants (at 50 Hz PWM, 20ms period)
const uint16_t SERVO_MIN = 150; // 0 degrees (~0.75 ms pulse)
const uint16_t SERVO_MAX = 600; // 180 degrees (~2.25 ms pulse)

// Calibrated angles for tactile pin DOWN (retracted) and UP (raised)
const uint8_t ANGLE_DOWN[6] = {20, 20, 20, 20, 20, 20};
const uint8_t ANGLE_UP[6]   = {70, 70, 70, 70, 70, 70};

// Button debouncing state
unsigned long lastButtonPressTime = 0;
const unsigned long DEBOUNCE_DELAY_MS = 250;

uint16_t angleToTicks(uint8_t angle) {
  return map(angle, 0, 180, SERVO_MIN, SERVO_MAX);
}

void showCell(uint8_t code) {
  for (uint8_t d = 0; d < 6; d++) {
    bool up = (code >> d) & 1;
    pwm.setPWM(d, 0, angleToTicks(up ? ANGLE_UP[d] : ANGLE_DOWN[d]));
    delay(35); // Stagger movements to prevent current spikes
  }
}

void resetAllDots() {
  for (uint8_t d = 0; d < 6; d++) {
    pwm.setPWM(d, 0, angleToTicks(ANGLE_DOWN[d]));
  }
}

void runSelfTest() {
  Serial.println("STATUS:RUNNING_SELF_TEST");
  resetAllDots();
  delay(200);

  // Test each dot individually from Dot 1 to Dot 6
  for (uint8_t d = 0; d < 6; d++) {
    tone(BUZZER, 1200 + (d * 100), 50);
    pwm.setPWM(d, 0, angleToTicks(ANGLE_UP[d]));
    delay(300);
    pwm.setPWM(d, 0, angleToTicks(ANGLE_DOWN[d]));
    delay(100);
  }

  // Flash all dots simultaneously
  showCell(0x3F); // All 6 dots up (dots 1..6)
  tone(BUZZER, 1800, 150);
  delay(600);
  resetAllDots();
  Serial.println("STATUS:SELF_TEST_PASSED");
}

void setup() {
  Serial.begin(115200);
  Wire.begin(I2C_SDA, I2C_SCL);
  pwm.begin();
  pwm.setPWMFreq(50); // Standard 50Hz servo refresh rate

  pinMode(BTN_NEXT, INPUT_PULLUP);
  pinMode(BUZZER, OUTPUT);

  resetAllDots();
  tone(BUZZER, 1500, 100); // Power-on confirmation beep
  Serial.println("BRAILLE_BRIDGE_ESP32_READY");
}

void loop() {
  // 1. Process incoming commands from Host PC
  if (Serial.available()) {
    int b = Serial.read();
    if (b < 0) return;

    if (b == 'P' || b == 'p') {
      // Handshake / Ping
      Serial.println("BRAILLE_BRIDGE_ESP32_OK");
    } else if (b == 'T' || b == 't') {
      // Hardware Self-Test
      runSelfTest();
    } else if (b == 'R' || b == 'r') {
      // Reset all pins
      resetAllDots();
      Serial.println("STATUS:RESET_OK");
    } else if (b == 'B' || b == 'b') {
      // Audio alert
      tone(BUZZER, 1200, 100);
    } else if (b == 'C') {
      // Framed cell command: 'C' followed by cell byte
      while (!Serial.available()) delay(1);
      uint8_t code = Serial.read() & 0x3F;
      showCell(code);
      tone(BUZZER, 1000, 40);
    } else if (b <= 0x3F) {
      // Legacy raw cell code byte (0..63)
      showCell((uint8_t)b);
      tone(BUZZER, 1000, 40);
    }
  }

  // 2. Hardware push-button with debouncing to advance to next character
  if (digitalRead(BTN_NEXT) == LOW) {
    unsigned long now = millis();
    if (now - lastButtonPressTime > DEBOUNCE_DELAY_MS) {
      lastButtonPressTime = now;
      tone(BUZZER, 2000, 30);
      Serial.println("NEXT");
    }
  }
}

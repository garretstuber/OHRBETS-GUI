// hardware_test.ino
// Direct Hardware Test for OHRBETS System
// Version: 2025-03-26
// Last updated: March 26, 2025
//
// This file provides direct hardware control functions that bypass
// the state machine to test solenoid functionality with precise timing.
// It uses blocking delay() statements for exact timing control.

// Hardware Pin Definitions (Same as main controller)
#define LED_PIN     13  // Built-in LED for status indication
#define ODOR_PIN    17  // Single solenoid for odor delivery
#define REWARD_PIN  4   // Solenoid for reward delivery
#define LICK_PIN    5   // Optional lick detector input

// Exact timing parameters (milliseconds)
#define ODOR_DURATION        2000  // Exactly 2 seconds
#define REWARD_PULSE1        40    // First reward pulse duration
#define REWARD_PAUSE         140   // Delay between reward pulses
#define REWARD_PULSE2        40    // Second reward pulse duration

// Function for direct odor test (blocking)
void directOdorTest() {
  Serial.println("DIRECT_ODOR_TEST_START");
  
  // Turn on odor solenoid
  digitalWrite(LED_PIN, HIGH);  // LED indicator
  digitalWrite(ODOR_PIN, HIGH);
  Serial.println("ODOR_ON");
  
  // Wait exactly 2 seconds
  delay(ODOR_DURATION);
  
  // Turn off odor solenoid
  digitalWrite(ODOR_PIN, LOW);
  digitalWrite(LED_PIN, LOW);
  Serial.println("ODOR_OFF");
  
  Serial.println("DIRECT_ODOR_TEST_COMPLETE");
}

// Function for direct reward test (blocking)
void directRewardTest() {
  Serial.println("DIRECT_REWARD_TEST_START");
  
  // First pulse (40ms)
  digitalWrite(LED_PIN, HIGH);
  digitalWrite(REWARD_PIN, HIGH);
  Serial.println("REWARD_PULSE1_ON");
  delay(REWARD_PULSE1);
  
  // Inter-pulse delay (140ms)
  digitalWrite(REWARD_PIN, LOW);
  digitalWrite(LED_PIN, LOW);
  Serial.println("REWARD_PULSE1_OFF");
  delay(REWARD_PAUSE);
  
  // Second pulse (40ms)
  digitalWrite(LED_PIN, HIGH);
  digitalWrite(REWARD_PIN, HIGH);
  Serial.println("REWARD_PULSE2_ON");
  delay(REWARD_PULSE2);
  
  // Turn off
  digitalWrite(REWARD_PIN, LOW);
  digitalWrite(LED_PIN, LOW);
  Serial.println("REWARD_PULSE2_OFF");
  
  Serial.println("DIRECT_REWARD_TEST_COMPLETE");
}

// Function for manual odor control
void setOdor(bool state) {
  digitalWrite(ODOR_PIN, state ? HIGH : LOW);
  digitalWrite(LED_PIN, state ? HIGH : LOW);
  Serial.print("MANUAL_ODOR_");
  Serial.println(state ? "ON" : "OFF");
}

// Function for manual reward control
void setReward(bool state) {
  digitalWrite(REWARD_PIN, state ? HIGH : LOW);
  digitalWrite(LED_PIN, state ? HIGH : LOW);
  Serial.print("MANUAL_REWARD_");
  Serial.println(state ? "ON" : "OFF");
}

// Process serial commands
void processCommand(const String& command) {
  if (command == "TEST_ODOR") {
    directOdorTest();
  } 
  else if (command == "TEST_REWARD") {
    directRewardTest();
  }
  else if (command == "ODOR_ON") {
    setOdor(true);
  }
  else if (command == "ODOR_OFF") {
    setOdor(false);
  }
  else if (command == "REWARD_ON") {
    setReward(true);
  }
  else if (command == "REWARD_OFF") {
    setReward(false);
  }
  else if (command == "STATUS") {
    Serial.print("STATUS:");
    Serial.print("ODOR=");
    Serial.print(digitalRead(ODOR_PIN) == HIGH ? "ON" : "OFF");
    Serial.print(",REWARD=");
    Serial.println(digitalRead(REWARD_PIN) == HIGH ? "ON" : "OFF");
  }
  else if (command == "RESET") {
    digitalWrite(ODOR_PIN, LOW);
    digitalWrite(REWARD_PIN, LOW);
    digitalWrite(LED_PIN, LOW);
    Serial.println("ALL_PINS_RESET");
  }
  else if (command == "HELP") {
    Serial.println("Available commands:");
    Serial.println("TEST_ODOR - Run odor test (2s exactly)");
    Serial.println("TEST_REWARD - Run reward test (40ms-140ms-40ms)");
    Serial.println("ODOR_ON - Turn odor valve on");
    Serial.println("ODOR_OFF - Turn odor valve off");
    Serial.println("REWARD_ON - Turn reward valve on");
    Serial.println("REWARD_OFF - Turn reward valve off");
    Serial.println("STATUS - Show current pin states");
    Serial.println("RESET - Turn all pins off");
    Serial.println("HELP - Show this help");
  }
  else {
    Serial.print("Unknown command: ");
    Serial.println(command);
    Serial.println("Type HELP for available commands");
  }
}

void setup() {
  // Initialize pins
  pinMode(LED_PIN, OUTPUT);
  pinMode(ODOR_PIN, OUTPUT);
  pinMode(REWARD_PIN, OUTPUT);
  pinMode(LICK_PIN, INPUT_PULLUP);
  
  // Ensure all outputs are off
  digitalWrite(LED_PIN, LOW);
  digitalWrite(ODOR_PIN, LOW);
  digitalWrite(REWARD_PIN, LOW);
  
  // Initialize serial communication
  Serial.begin(115200);
  Serial.println("HARDWARE_TEST_READY");
  Serial.println("Type HELP for available commands");
}

String inputBuffer = "";

void loop() {
  // Process serial commands
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n') {
      if (inputBuffer.length() > 0) {
        processCommand(inputBuffer);
        inputBuffer = "";
      }
    } else if (c != '\r') {
      inputBuffer += c;
    }
  }
} 
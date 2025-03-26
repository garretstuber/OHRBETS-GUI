// fsm_pavlovian_odor.ino
// Finite State Machine for Pavlovian Odor Conditioning

// Configuration - Hardware Pins (Hardwired)
#define LED_PIN     13  // Built-in LED for status indication
#define ODOR1_PIN   2   // Solenoid for CS+ odor
#define ODOR2_PIN   3   // Solenoid for CS- odor
#define REWARD_PIN  4   // Solenoid for reward delivery
#define LICK_PIN    5   // Optional lick detector input

// Event codes for data logging
#define EVENT_TRIAL_START    1
#define EVENT_TRIAL_END      2
#define EVENT_ODOR_ON        3
#define EVENT_ODOR_OFF       4
#define EVENT_REWARD_ON      5
#define EVENT_REWARD_OFF     6
#define EVENT_LICK           7

// Reward delivery pattern
#define REWARD_PULSE1_DURATION  40    // First reward pulse (ms)
#define REWARD_DELAY_DURATION   140   // Delay between pulses (ms)
#define REWARD_PULSE2_DURATION  40    // Second reward pulse (ms) - changed from 20 to 40

// Manual test durations
#define TEST_ODOR_DURATION    1000    // 1 second for manual odor test
#define TEST_REWARD_DURATION  220     // Combined duration of reward sequence (40+140+40)

// Timing precision: use microseconds for all timestamps
// State machine: use non-blocking design with millis() for state transitions

class PavlovianController {
private:
    // State machine states
    enum State {
        IDLE,
        INTERTRIAL,
        ODOR,
        REWARD_PULSE1,
        REWARD_DELAY,
        REWARD_PULSE2,
        POST_REWARD,
        COMPLETE,
        // Test states
        TEST_ODOR1,
        TEST_ODOR2,
        TEST_REWARD1,
        TEST_REWARD_DELAY,
        TEST_REWARD2
    };
    
    State state = IDLE;
    unsigned long stateStartTime = 0;
    unsigned long nextStateTime = 0;
    
    // Trial parameters
    int* trialSequence = NULL;
    int numTrials = 0;
    int currentTrial = 0;
    int currentTrialType = 0;
    
    // Timing parameters (milliseconds)
    int intertrialInterval = 5000;  // Configurable
    int odorDuration = 2000;        // Configurable
    int rewardDuration = 500;       // Total reward phase duration (configurable)
    
    // LED blink timing (non-blocking)
    unsigned long ledOffTime = 0;
    bool ledBlinking = false;
    
    // Odor state tracking
    bool odor1Active = false;
    bool odor2Active = false;
    
    // Reward state tracking
    bool rewardActive = false;
    
    // Lick sensor tracking
    unsigned long lastLickTime = 0;
    int lickCount = 0;
    
    // Methods for hardware control
    void setOdor(int type, bool state) {
        // Ensure proper pin control based on trial type
        if (type == 1) {  // CS+
            digitalWrite(ODOR1_PIN, state ? HIGH : LOW);
            odor1Active = state;
            // Ensure the other odor is off
            if (state) {
                digitalWrite(ODOR2_PIN, LOW);
                odor2Active = false;
            }
        } else {  // CS-
            digitalWrite(ODOR2_PIN, state ? HIGH : LOW);
            odor2Active = state;
            // Ensure the other odor is off
            if (state) {
                digitalWrite(ODOR1_PIN, LOW);
                odor1Active = false;
            }
        }
        
        // Log event only after hardware has been set
        logEvent(state ? EVENT_ODOR_ON : EVENT_ODOR_OFF);
    }
    
    void setReward(bool state) {
        // Directly control the reward pin
        digitalWrite(REWARD_PIN, state ? HIGH : LOW);
        rewardActive = state;
        
        // Log the event
        logEvent(state ? EVENT_REWARD_ON : EVENT_REWARD_OFF);
        
        // Debug output
        Serial.print("REWARD_");
        Serial.println(state ? "ON" : "OFF");
    }
    
    void logEvent(int eventCode) {
        // Get timestamp first for accuracy
        unsigned long timestamp = micros();  // Microsecond precision
        
        // Send data without delays
        Serial.print("DATA:");
        Serial.print(eventCode);
        Serial.print(",");
        Serial.println(timestamp);
        Serial.flush();
        
        // Trigger LED blink (non-blocking)
        digitalWrite(LED_PIN, HIGH);
        ledBlinking = true;
        ledOffTime = millis() + 2; // 2ms blink
    }
    
    void updateLED() {
        // Non-blocking LED blink
        if (ledBlinking && millis() >= ledOffTime) {
            digitalWrite(LED_PIN, LOW);
            ledBlinking = false;
        }
    }
    
    void emergencyStop() {
        // Turn off all outputs
        digitalWrite(ODOR1_PIN, LOW);
        digitalWrite(ODOR2_PIN, LOW);
        digitalWrite(REWARD_PIN, LOW);
        odor1Active = false;
        odor2Active = false;
        rewardActive = false;
    }
    
    // Test reward with 2-pulse pattern
    void startTestReward() {
        // First pulse
        state = TEST_REWARD1;
        stateStartTime = millis();
        nextStateTime = stateStartTime + REWARD_PULSE1_DURATION;
        setReward(true);
        Serial.println("TEST_REWARD_START");
    }

public:
    void begin() {
        // Initialize hardware
        pinMode(LED_PIN, OUTPUT);
        pinMode(ODOR1_PIN, OUTPUT);
        pinMode(ODOR2_PIN, OUTPUT);
        pinMode(REWARD_PIN, OUTPUT);
        pinMode(LICK_PIN, INPUT_PULLUP);
        
        // Turn everything off
        digitalWrite(LED_PIN, LOW);
        digitalWrite(ODOR1_PIN, LOW);
        digitalWrite(ODOR2_PIN, LOW);
        digitalWrite(REWARD_PIN, LOW);
        
        // Initialize state variables
        odor1Active = false;
        odor2Active = false;
        rewardActive = false;
        
        // Initialize serial
        Serial.begin(115200);
        Serial.println("READY");
    }
    
    void update() {
        // Update LED state (non-blocking)
        updateLED();
        
        // Non-blocking state machine
        unsigned long currentTime = millis();
        
        // Only proceed if in active state and time has elapsed
        if (state != IDLE && state != COMPLETE && currentTime >= nextStateTime) {
            switch (state) {
                case INTERTRIAL:
                    // Transition to odor presentation
                    state = ODOR;
                    stateStartTime = currentTime;
                    nextStateTime = currentTime + odorDuration;
                    setOdor(currentTrialType, true);
                    break;
                    
                case ODOR:
                    // Turn off odor and transition to reward sequence (for CS+) or post-reward (for CS-)
                    setOdor(currentTrialType, false);
                    
                    if (currentTrialType == 1) {  // CS+
                        // First reward pulse
                        state = REWARD_PULSE1;
                        stateStartTime = currentTime;
                        nextStateTime = currentTime + REWARD_PULSE1_DURATION;
                        setReward(true);
                    } else {  // CS-
                        // Skip reward and go to post-reward phase
                        state = POST_REWARD;
                        stateStartTime = currentTime;
                        nextStateTime = currentTime + rewardDuration;
                    }
                    break;
                    
                case REWARD_PULSE1:
                    // Turn off reward and start delay
                    setReward(false);
                    state = REWARD_DELAY;
                    stateStartTime = currentTime;
                    nextStateTime = currentTime + REWARD_DELAY_DURATION;
                    break;
                    
                case REWARD_DELAY:
                    // Second reward pulse
                    state = REWARD_PULSE2;
                    stateStartTime = currentTime;
                    nextStateTime = currentTime + REWARD_PULSE2_DURATION;
                    setReward(true);
                    break;
                    
                case REWARD_PULSE2:
                    // Turn off reward and go to post-reward phase
                    setReward(false);
                    state = POST_REWARD;
                    stateStartTime = currentTime;
                    // Calculate remaining time in reward phase
                    unsigned long totalElapsed = currentTime - (stateStartTime - REWARD_PULSE1_DURATION - REWARD_DELAY_DURATION);
                    unsigned long remainingTime = (totalElapsed >= rewardDuration) ? 0 : (rewardDuration - totalElapsed);
                    nextStateTime = currentTime + remainingTime;
                    break;
                    
                case POST_REWARD:
                    // Log trial end
                    logEvent(EVENT_TRIAL_END);
                    
                    // Move to next trial or end session
                    currentTrial++;
                    if (currentTrial >= numTrials) {
                        state = COMPLETE;
                        Serial.println("SESSION_COMPLETE");
                    } else {
                        // Start next trial
                        currentTrialType = trialSequence[currentTrial];
                        state = INTERTRIAL;
                        stateStartTime = currentTime;
                        nextStateTime = currentTime + intertrialInterval;
                        logEvent(EVENT_TRIAL_START);
                    }
                    break;
                
                // Test states for hardware validation
                case TEST_ODOR1:
                    // Turn off odor after test duration
                    digitalWrite(ODOR1_PIN, LOW);
                    odor1Active = false;
                    state = IDLE;
                    Serial.println("TEST_ODOR1_COMPLETE");
                    break;
                    
                case TEST_ODOR2:
                    // Turn off odor after test duration
                    digitalWrite(ODOR2_PIN, LOW);
                    odor2Active = false;
                    state = IDLE;
                    Serial.println("TEST_ODOR2_COMPLETE");
                    break;
                
                // New test states for reward with explicit state transitions
                case TEST_REWARD1:
                    // End of first pulse - turn off solenoid
                    setReward(false);
                    // Transition to delay
                    state = TEST_REWARD_DELAY;
                    stateStartTime = currentTime;
                    nextStateTime = currentTime + REWARD_DELAY_DURATION;
                    break;
                    
                case TEST_REWARD_DELAY:
                    // End of delay - start second pulse
                    setReward(true);
                    state = TEST_REWARD2;
                    stateStartTime = currentTime;
                    nextStateTime = currentTime + REWARD_PULSE2_DURATION;
                    break;
                    
                case TEST_REWARD2:
                    // End of second pulse
                    setReward(false);
                    state = IDLE;
                    Serial.println("TEST_REWARD_COMPLETE");
                    break;
                    
                default:
                    break;
            }
        }
        
        // Check for lick events if using lick detector
        static bool lastLickState = HIGH;
        bool currentLickState = digitalRead(LICK_PIN);
        if (currentLickState != lastLickState && currentLickState == LOW) {
            // Lick detected (falling edge)
            lastLickTime = millis();
            lickCount++;
            logEvent(EVENT_LICK);
        }
        lastLickState = currentLickState;
        
        // Safety check - ensure reward is not stuck on
        if (rewardActive && state != REWARD_PULSE1 && state != REWARD_PULSE2 
            && state != TEST_REWARD1 && state != TEST_REWARD2) {
            // If reward is on but we're not in a reward pulse state, turn it off
            setReward(false);
        }
    }
    
    void processCommand(const String& command) {
        // Handle commands from Python GUI
        if (command.startsWith("SET_TIMING:")) {
            // Format: SET_TIMING:iti,odor,reward
            // Example: SET_TIMING:5000,2000,500
            int comma1 = command.indexOf(',', 11);
            int comma2 = command.indexOf(',', comma1 + 1);
            
            if (comma1 > 0 && comma2 > 0) {
                intertrialInterval = command.substring(11, comma1).toInt();
                odorDuration = command.substring(comma1 + 1, comma2).toInt();
                rewardDuration = command.substring(comma2 + 1).toInt();
                
                Serial.print("TIMING_SET:");
                Serial.print(intertrialInterval);
                Serial.print(",");
                Serial.print(odorDuration);
                Serial.print(",");
                Serial.println(rewardDuration);
            }
        }
        else if (command.startsWith("SEQUENCE:")) {
            // Parse trial sequence
            String sequenceStr = command.substring(9);
            
            // Count trials and allocate memory
            int commaCount = 0;
            for (int i = 0; i < sequenceStr.length(); i++) {
                if (sequenceStr.charAt(i) == ',') commaCount++;
            }
            numTrials = commaCount + 1;
            
            // Free old sequence if exists
            if (trialSequence != NULL) {
                free(trialSequence);
            }
            
            // Allocate and parse new sequence
            trialSequence = (int*)malloc(numTrials * sizeof(int));
            
            int index = 0;
            int startPos = 0;
            for (int i = 0; i <= sequenceStr.length(); i++) {
                if (i == sequenceStr.length() || sequenceStr.charAt(i) == ',') {
                    if (index < numTrials) {
                        trialSequence[index++] = sequenceStr.substring(startPos, i).toInt();
                    }
                    startPos = i + 1;
                }
            }
            
            Serial.print("SEQUENCE_RECEIVED:");
            Serial.println(numTrials);
        }
        else if (command == "START") {
            // Only start if in IDLE state and not running tests
            if (state == IDLE && numTrials > 0) {
                // Start session
                currentTrial = 0;
                currentTrialType = trialSequence[0];
                state = INTERTRIAL;
                stateStartTime = millis();
                nextStateTime = stateStartTime + intertrialInterval;
                logEvent(EVENT_TRIAL_START);
                Serial.println("SESSION_STARTED");
            }
        }
        else if (command == "ABORT") {
            // Emergency stop
            emergencyStop();
            state = IDLE;
            Serial.println("SESSION_ABORTED");
        }
        else if (command == "STATUS") {
            // Report current status
            Serial.print("STATUS:");
            Serial.print(state);
            Serial.print(",");
            Serial.print(currentTrial);
            Serial.print("/");
            Serial.print(numTrials);
            Serial.print(",O1:");
            Serial.print(odor1Active ? "ON" : "OFF");
            Serial.print(",O2:");
            Serial.print(odor2Active ? "ON" : "OFF");
            Serial.print(",Reward:");
            Serial.print(rewardActive ? "ON" : "OFF");
            Serial.print(",Licks:");
            Serial.print(lickCount);
            Serial.print(",LastLick:");
            Serial.println(lastLickTime);
        }
        else if (command == "TEST_ODOR1") {
            // Only allow test if in IDLE state
            if (state == IDLE) {
                // Turn on Odor 1 for testing
                digitalWrite(ODOR1_PIN, HIGH);
                odor1Active = true;
                digitalWrite(ODOR2_PIN, LOW);
                odor2Active = false;
                logEvent(EVENT_ODOR_ON);
                
                // Set timer to turn off after test duration
                state = TEST_ODOR1;
                stateStartTime = millis();
                nextStateTime = stateStartTime + TEST_ODOR_DURATION;
                Serial.println("TEST_ODOR1_START");
            } else {
                Serial.println("ERROR:BUSY");
            }
        }
        else if (command == "TEST_ODOR2") {
            // Only allow test if in IDLE state
            if (state == IDLE) {
                // Turn on Odor 2 for testing
                digitalWrite(ODOR2_PIN, HIGH);
                odor2Active = true;
                digitalWrite(ODOR1_PIN, LOW);
                odor1Active = false;
                logEvent(EVENT_ODOR_ON);
                
                // Set timer to turn off after test duration
                state = TEST_ODOR2;
                stateStartTime = millis();
                nextStateTime = stateStartTime + TEST_ODOR_DURATION;
                Serial.println("TEST_ODOR2_START");
            } else {
                Serial.println("ERROR:BUSY");
            }
        }
        else if (command == "TEST_REWARD") {
            // Only allow test if in IDLE state
            if (state == IDLE) {
                startTestReward();
            } else {
                Serial.println("ERROR:BUSY");
            }
        }
        else if (command == "MANUAL_REWARD_ON") {
            // Directly control reward for manual testing
            if (state == IDLE) {
                setReward(true);
                Serial.println("MANUAL_REWARD:ON");
            } else {
                Serial.println("ERROR:BUSY");
            }
        }
        else if (command == "MANUAL_REWARD_OFF") {
            // Directly control reward for manual testing
            setReward(false);
            Serial.println("MANUAL_REWARD:OFF");
        }
        else if (command == "TEST_LICK") {
            // Reset lick counter and report current status
            lickCount = 0;
            lastLickTime = 0;
            Serial.println("LICK_TEST:MONITORING");
        }
        else if (command == "RESET_LICK_COUNT") {
            // Reset lick counter
            lickCount = 0;
            Serial.println("LICK_COUNT_RESET");
        }
    }
};

PavlovianController controller;
String inputBuffer = "";

void setup() {
    randomSeed(analogRead(0));
    controller.begin();
}

void loop() {
    // Process serial commands
    while (Serial.available() > 0) {
        char c = Serial.read();
        if (c == '\n') {
            controller.processCommand(inputBuffer);
            inputBuffer = "";
        } else {
            inputBuffer += c;
        }
    }
    
    // Update state machine
    controller.update();
} 
// fsm_pavlovian_odor.ino
// Finite State Machine for Pavlovian Odor Conditioning
// Version: 2025-03-26 
// Last updated: March 26, 2025
// 
// Updates:
// - Fixed odor valve timing (exactly 2s with direct delay)
// - Fixed reward pattern timing (40ms-140ms-40ms with direct control)
// - Added safety timeouts and additional debugging
// - Switched to millisecond precision for timestamps
// - Added timestamp logging for events
// - Added loop delay detection
// - Fixed state transition issues with test states
// - Implemented hardcoded timing for critical components

// Configuration - Hardware Pins (Hardwired)
#define LED_PIN     13  // Built-in LED for status indication
#define ODOR_PIN    17  // Single solenoid for odor delivery
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
#define REWARD_PULSE2_DURATION  40    // Second reward pulse (ms)

// Default timing parameters (configurable via commands)
#define DEFAULT_ITI_DURATION   5000   // Default inter-trial interval (ms)
#define DEFAULT_ODOR_DURATION  2000   // Default odor presentation duration (ms)
#define DEFAULT_REWARD_DURATION 500   // Default total reward phase duration (ms)

// Manual test durations
#define TEST_ODOR_DURATION    2000    // 2 seconds for manual odor test - same as default trial duration
#define TEST_REWARD_DURATION  220     // Combined duration of reward sequence (40+140+40)

// Timeout for stuck states (ms) - reset to IDLE if a state lasts too long
#define STATE_TIMEOUT 10000  // Increased from 5000ms to 10000ms

// Timing precision: use milliseconds for all timestamps and state transitions
// State machine: use non-blocking design with millis() for state transitions

class PavlovianController {
private:
    // State machine states
    enum State {
        IDLE,
        INTERTRIAL,
        ODOR,
        REWARD,
        POST_REWARD,
        COMPLETE,
        // Test states
        TEST_ODOR,
        TEST_REWARD,
        // Manual control states
        MANUAL_ODOR_CONTROL,
        MANUAL_REWARD_CONTROL
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
    int intertrialInterval = DEFAULT_ITI_DURATION;
    int odorDuration = DEFAULT_ODOR_DURATION;
    int rewardDuration = DEFAULT_REWARD_DURATION;
    
    // LED blink timing (non-blocking)
    unsigned long ledOffTime = 0;
    bool ledBlinking = false;
    
    // Odor state tracking
    bool odorActive = false;
    
    // Reward state tracking
    bool rewardActive = false;
    
    // Lick sensor tracking
    unsigned long lastLickTime = 0;
    int lickCount = 0;
    
    // Manual control flags
    bool inManualControl = false;

    // Add timestamp reference variable
    unsigned long timestampReference = 0;

    // Helper method to print state transitions for debugging
    void printStateTransition(State fromState, State toState) {
        Serial.print("STATE_CHANGE:");
        Serial.print(fromState);
        Serial.print("->");
        Serial.println(toState);
        
        // Also print timing for better debugging
        Serial.print("TIME:");
        Serial.print(millis());
        Serial.print(",NextState:");
        Serial.println(nextStateTime);
    }
    
    // Methods for hardware control
    void setOdor(bool state) {
        // Control the odor pin directly
        digitalWrite(ODOR_PIN, state ? HIGH : LOW);
        odorActive = state;
        
        // Log event only after hardware has been set
        logEvent(state ? EVENT_ODOR_ON : EVENT_ODOR_OFF);
        
        // Debug output
        Serial.print("ODOR_");
        Serial.println(state ? "ON" : "OFF");
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
        // Get timestamp with millisecond precision, subtract reference time
        unsigned long currentTime = millis();
        unsigned long timestamp = currentTime - timestampReference;
        
        // Send data without delays
        Serial.print("DATA:");
        Serial.print(eventCode);
        Serial.print(",");
        Serial.println(timestamp);
        Serial.flush();
        
        // Trigger LED blink (non-blocking)
        digitalWrite(LED_PIN, HIGH);
        ledBlinking = true;
        ledOffTime = currentTime + 2; // 2ms blink
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
        digitalWrite(ODOR_PIN, LOW);
        digitalWrite(REWARD_PIN, LOW);
        odorActive = false;
        rewardActive = false;
        inManualControl = false;
        
        // Reset state to IDLE
        State oldState = state;
        state = IDLE;
        printStateTransition(oldState, state);
        Serial.println("EMERGENCY_STOP");
    }
    
    // Set state with proper transition logging
    void setState(State newState) {
        State oldState = state;
        state = newState;
        stateStartTime = millis(); // Reset state timer
        printStateTransition(oldState, newState);
        
        // If entering IDLE state, ensure all outputs are off
        if (newState == IDLE) {
            if (odorActive) {
                setOdor(false);
            }
            if (rewardActive) {
                setReward(false);
            }
            inManualControl = false;
        }
        
        // Set manual control flag for manual states
        if (newState == MANUAL_ODOR_CONTROL || newState == MANUAL_REWARD_CONTROL) {
            inManualControl = true;
        }
    }
    
    // Direct odor test with precise timing
    void directOdorTest() {
        Serial.println("DIRECT_ODOR_TEST_START");
        
        // Set state to TEST_ODOR
        setState(TEST_ODOR);
        
        // Turn on odor solenoid
        digitalWrite(LED_PIN, HIGH);  // LED indicator
        setOdor(true);
        
        // Wait exactly 2 seconds with blocking delay
        delay(odorDuration);
        
        // Turn off odor solenoid
        setOdor(false);
        digitalWrite(LED_PIN, LOW);
        
        // Return to idle state
        setState(IDLE);
        Serial.println("DIRECT_ODOR_TEST_COMPLETE");
    }
    
    // Direct reward test with precise timing for the pattern
    void directRewardTest() {
        Serial.println("DIRECT_REWARD_TEST_START");
        
        // Set state to TEST_REWARD
        setState(TEST_REWARD);
        
        // First pulse (40ms)
        digitalWrite(LED_PIN, HIGH);
        setReward(true);
        Serial.println("REWARD_PULSE1_ON");
        delay(REWARD_PULSE1_DURATION);
        
        // Inter-pulse delay (140ms)
        setReward(false);
        digitalWrite(LED_PIN, LOW);
        Serial.println("REWARD_PULSE1_OFF");
        delay(REWARD_DELAY_DURATION);
        
        // Second pulse (40ms)
        digitalWrite(LED_PIN, HIGH);
        setReward(true);
        Serial.println("REWARD_PULSE2_ON");
        delay(REWARD_PULSE2_DURATION);
        
        // Turn off
        setReward(false);
        digitalWrite(LED_PIN, LOW);
        Serial.println("REWARD_PULSE2_OFF");
        
        // Return to idle state
        setState(IDLE);
        Serial.println("DIRECT_REWARD_TEST_COMPLETE");
    }
    
    // Direct reward sequence for CS+ trials with precise timing
    void deliverReward() {
        // First pulse (40ms)
        setReward(true);
        delay(REWARD_PULSE1_DURATION);
        
        // Inter-pulse delay (140ms)
        setReward(false);
        delay(REWARD_DELAY_DURATION);
        
        // Second pulse (40ms)
        setReward(true);
        delay(REWARD_PULSE2_DURATION);
        
        // Turn off
        setReward(false);
    }

public:
    void begin() {
        // Initialize hardware
        pinMode(LED_PIN, OUTPUT);
        pinMode(ODOR_PIN, OUTPUT);
        pinMode(REWARD_PIN, OUTPUT);
        pinMode(LICK_PIN, INPUT_PULLUP);
        
        // Turn everything off
        digitalWrite(LED_PIN, LOW);
        digitalWrite(ODOR_PIN, LOW);
        digitalWrite(REWARD_PIN, LOW);
        
        // Initialize state variables
        odorActive = false;
        rewardActive = false;
        inManualControl = false;
        
        // Initialize serial
        Serial.begin(115200);
        Serial.println("READY");
    }
    
    void update() {
        // Update LED state (non-blocking)
        updateLED();
        
        // Non-blocking state machine
        unsigned long currentTime = millis();
        
        // Check for state timeout - prevent stuck states
        // Only apply timeout to non-manual states
        if (state != IDLE && !inManualControl && (currentTime - stateStartTime) > STATE_TIMEOUT) {
            Serial.print("STATE_TIMEOUT:");
            Serial.print(state);
            Serial.print(",Started:");
            Serial.print(stateStartTime);
            Serial.print(",Current:");
            Serial.println(currentTime);
            emergencyStop();
            return;
        }
        
        // Only proceed if in active state and time has elapsed
        if (state != IDLE && state != COMPLETE && currentTime >= nextStateTime) {
            switch (state) {
                case INTERTRIAL:
                    // Transition to odor presentation
                    setState(ODOR);
                    
                    // Direct odor control with precise timing
                    // Turn on odor
                    setOdor(true);
                    
                    // Calculate next state time
                    nextStateTime = currentTime + odorDuration;
                    break;
                    
                case ODOR:
                    // Turn off odor and transition to reward sequence (for CS+) or post-reward (for CS-)
                    setOdor(false);
                    
                    if (currentTrialType == 1) {  // CS+
                        // Use reward state for CS+ trials
                        setState(REWARD);
                        
                        // Deliver reward with direct timing control
                        deliverReward();
                        
                        // Calculate time remaining in reward phase
                        unsigned long totalRewardTime = 
                            REWARD_PULSE1_DURATION + REWARD_DELAY_DURATION + REWARD_PULSE2_DURATION;
                        unsigned long remainingTime = 
                            (totalRewardTime >= rewardDuration) ? 0 : (rewardDuration - totalRewardTime);
                        
                        // Set next state time
                        nextStateTime = currentTime + remainingTime;
                        
                    } else {  // CS-
                        // Skip reward and go to post-reward phase
                        setState(POST_REWARD);
                        nextStateTime = currentTime + rewardDuration;
                    }
                    break;
                    
                case REWARD:
                    // Move to post-reward phase after waiting any remaining time
                    setState(POST_REWARD);
                    nextStateTime = currentTime;  // Immediate transition
                    break;
                    
                case POST_REWARD:
                    // Log trial end
                    logEvent(EVENT_TRIAL_END);
                    
                    // Move to next trial or end session
                    currentTrial++;
                    if (currentTrial >= numTrials) {
                        setState(COMPLETE);
                        Serial.println("SESSION_COMPLETE");
                    } else {
                        // Start next trial
                        currentTrialType = trialSequence[currentTrial];
                        setState(INTERTRIAL);
                        nextStateTime = currentTime + intertrialInterval;
                        logEvent(EVENT_TRIAL_START);
                    }
                    break;
                
                case COMPLETE:
                    // Move back to IDLE state when complete
                    setState(IDLE);
                    break;
                
                default:
                    // Unknown state - reset to IDLE
                    setState(IDLE);
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
        
        // Safety checks - ensure solenoids are not stuck on
        // Skip safety checks for manual control or test states
        
        // Reward solenoid safety check - force close if not in a reward pulse state or manual control
        if (rewardActive && 
            !inManualControl &&
            state != REWARD && 
            state != TEST_REWARD) {
            // If reward is on but we're not in a reward state, turn it off
            setReward(false);
            Serial.println("SAFETY:REWARD_OFF");
        }
        
        // Odor solenoid safety check - force close if not in an odor state or manual control
        if (odorActive && 
            !inManualControl &&
            state != ODOR && 
            state != TEST_ODOR) {
            // If odor is on but we're not in an appropriate state, turn it off
            setOdor(false);
            Serial.println("SAFETY:ODOR_OFF");
        }
    }
    
    void processCommand(const String& command) {
        // Handle commands from Python GUI
        if (command == "RESET") {
            // Force reset the state machine to IDLE
            emergencyStop();
            return;
        }
        
        if (command.startsWith("SET_TIMING:")) {
            // Format: SET_TIMING:iti,odor,reward
            // Example: SET_TIMING:5000,2000,500
            // Note: Only ITI is configurable now, odor and reward are hardcoded
            int comma1 = command.indexOf(',', 11);
            
            if (comma1 > 0) {
                intertrialInterval = command.substring(11, comma1).toInt();
                
                // Keep odor and reward duration hardcoded but acknowledge receipt
                Serial.print("TIMING_SET:ITI=");
                Serial.print(intertrialInterval);
                Serial.println("ms (Odor and Reward timing are hardcoded)");
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
                // Reset timestamp reference when starting new session
                timestampReference = millis();
                
                // Start session
                currentTrial = 0;
                currentTrialType = trialSequence[0];
                setState(INTERTRIAL);
                nextStateTime = millis() + intertrialInterval;
                logEvent(EVENT_TRIAL_START);
                Serial.println("SESSION_STARTED");
            } else {
                Serial.println("ERROR:BUSY");
            }
        }
        else if (command == "ABORT") {
            // Emergency stop
            emergencyStop();
        }
        else if (command == "STATUS") {
            // Report current status
            Serial.print("STATUS:");
            Serial.print(state);
            Serial.print(",");
            Serial.print(currentTrial);
            Serial.print("/");
            Serial.print(numTrials);
            Serial.print(",Odor:");
            Serial.print(odorActive ? "ON" : "OFF");
            Serial.print(",Reward:");
            Serial.print(rewardActive ? "ON" : "OFF");
            Serial.print(",Licks:");
            Serial.print(lickCount);
            Serial.print(",LastLick:");
            Serial.println(lastLickTime);
        }
        else if (command == "TEST_ODOR") {
            // Only allow test if in IDLE state
            if (state == IDLE) {
                // Use direct timing method instead of state machine
                directOdorTest();
            } else {
                Serial.println("ERROR:BUSY");
            }
        }
        else if (command == "TEST_REWARD") {
            // Only allow test if in IDLE state
            if (state == IDLE) {
                // Use direct timing method instead of state machine
                directRewardTest();
            } else {
                Serial.println("ERROR:BUSY");
            }
        }
        else if (command == "MANUAL_REWARD_ON") {
            // Directly control reward for manual testing
            if (state == IDLE || inManualControl) {
                setState(MANUAL_REWARD_CONTROL);
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
            
            // Return to IDLE if in manual control
            if (inManualControl) {
                setState(IDLE);
            }
        }
        else if (command == "MANUAL_ODOR_ON") {
            // Directly control odor for manual testing
            if (state == IDLE || inManualControl) {
                setState(MANUAL_ODOR_CONTROL);
                setOdor(true);
                Serial.println("MANUAL_ODOR:ON");
            } else {
                Serial.println("ERROR:BUSY");
            }
        }
        else if (command == "MANUAL_ODOR_OFF") {
            // Directly control odor for manual testing
            setOdor(false);
            Serial.println("MANUAL_ODOR:OFF");
            
            // Return to IDLE if in manual control
            if (inManualControl) {
                setState(IDLE);
            }
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
        else if (command == "DEBUG_STATE") {
            // Output debug information about current state
            Serial.print("DEBUG_STATE:");
            Serial.print(state);
            Serial.print(",Time:");
            Serial.print(millis());
            Serial.print(",StateStart:");
            Serial.print(stateStartTime);
            Serial.print(",NextState:");
            Serial.print(nextStateTime);
            Serial.print(",Manual:");
            Serial.println(inManualControl);
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
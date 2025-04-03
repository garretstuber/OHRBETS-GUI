// Finite State Machine for Pavlovian Odor Conditioning
// Version: 2025-04-01 
// Last updated: April 2, 2025 at 340pm
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
// - Integrated MPR121 capacitive touch sensor for lick detection

#include <Wire.h>
#include "Adafruit_MPR121.h"

// Configuration - Hardware Pins (Hardwired)
#define LED_PIN     13  // Built-in LED for status indication
#define ODOR_PIN    17  // Single solenoid for odor delivery
#define REWARD_PIN  4   // Solenoid for reward delivery
// LICK_PIN removed as we're using MPR121 capacitive sensor

// Event codes for data logging
#define EVENT_TRIAL_START    1
#define EVENT_TRIAL_END      2
#define EVENT_ODOR_ON        3
#define EVENT_ODOR_OFF       4
#define EVENT_REWARD_ON      5
#define EVENT_REWARD_OFF     6
#define EVENT_LICK           7
#define EVENT_SESSION_START  8  // New event code for session start

// Reward delivery pattern
#define REWARD_PULSE1_DURATION  40    // First reward pulse (ms)
#define REWARD_DELAY_DURATION   140   // Delay between pulses (ms)
#define REWARD_PULSE2_DURATION  40    // Second reward pulse (ms)

// Lick detection parameters
#define MIN_INTERLICK_INTERVAL  67    // Minimum time between licks (ms) - mice cannot lick faster than ~15 Hz

// Trial timing parameters
#define DEFAULT_ITI_DURATION   5000   // Default inter-trial interval (ms)
#define DEFAULT_ODOR_DURATION  2000   // Default odor presentation duration (ms)
#define DEFAULT_REWARD_DURATION 500   // Default total reward phase duration (ms)
#define TRIAL_INIT_DURATION    5000   // 5 second wait after trial start
#define TRACE_INTERVAL_DURATION 1000  // 1 second trace interval
#define CONSUMATORY_DURATION   5000   // 5 second consumatory period

// Manual test durations
#define TEST_ODOR_DURATION    2000    // 2 seconds for manual odor test
#define TEST_REWARD_DURATION  220     // Combined duration of reward sequence (40+140+40)

// Timeout for stuck states (ms)
#define STATE_TIMEOUT 10000

// Lick detector configuration
#define LICK_SIGNAL_INVERTED false  // Set to false if lick gives LOW signal

// Timing precision: use milliseconds for all timestamps and state transitions
// State machine: use non-blocking design with millis() for state transitions

class PavlovianController {
private:
    // State machine states
    enum State {
        IDLE,
        ITI,               // 1. ITI period
        TRIAL_INIT,       // 2. Trial start + 5s wait
        ODOR_PERIOD,      // 3. 2s odor presentation
        TRACE_INTERVAL,   // 4. 1s trace interval
        REWARD_SEQUENCE,  // 5. Reward solenoid pattern
        CONSUMATORY,      // 6. 5s consumatory period
        TRIAL_OFF,        // 7. End trial and loop back
        COMPLETE,         // Session complete
        // Test states
        TEST_ODOR,
        TEST_REWARD,
        LICK_TEST,        // Added state for lick testing
        // Manual control states
        MANUAL_ODOR_CONTROL,
        MANUAL_REWARD_CONTROL
    };
    
    State state = IDLE;
    unsigned long stateStartTime = 0;
    unsigned long nextStateTime = 0;
    
    // MPR121 capacitive sensor
    Adafruit_MPR121 cap;
    uint16_t lasttouched = 0;
    uint16_t currtouched = 0;
    bool lickDetected = false;
    
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

    // Pin state tracking
    bool lastPinState = HIGH;  // Added for lick detection state tracking

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
        
        // If entering IDLE state, ensure all outputs are off and reset flags
        if (newState == IDLE) {
            if (odorActive) {
                setOdor(false);
            }
            if (rewardActive) {
                setReward(false);
            }
            inManualControl = false;
            // Reset lick test state if it was active
            if (oldState == LICK_TEST) {
                lickCount = 0;
                lastLickTime = 0;
            }
        }
        
        // Set manual control flag for manual states
        if (newState == MANUAL_ODOR_CONTROL || newState == MANUAL_REWARD_CONTROL) {
            inManualControl = true;
        }
        
        // Debug output for state change
        Serial.print("DEBUG:State=");
        Serial.print(newState);
        Serial.print(",Manual=");
        Serial.print(inManualControl);
        Serial.print(",Time=");
        Serial.println(millis());
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
        Serial.println("REWARD_DELIVERY_START");
        
        // First pulse (40ms)
        setReward(true);
        Serial.println("REWARD_PULSE1_ON");
        delay(REWARD_PULSE1_DURATION);
        
        // Inter-pulse delay (140ms)
        setReward(false);
        Serial.println("REWARD_PULSE1_OFF");
        delay(REWARD_DELAY_DURATION);
        
        // Second pulse (40ms)
        setReward(true);
        Serial.println("REWARD_PULSE2_ON");
        delay(REWARD_PULSE2_DURATION);
        
        // Turn off
        setReward(false);
        Serial.println("REWARD_PULSE2_OFF");
        
        Serial.println("REWARD_DELIVERY_COMPLETE");
    }

    void initializeHardware() {
        // Initialize pins
        pinMode(LED_PIN, OUTPUT);
        pinMode(ODOR_PIN, OUTPUT);
        pinMode(REWARD_PIN, OUTPUT);
        
        // Initialize MPR121
        if (!cap.begin(0x5A)) {
            Serial.println("MPR121 not detected!");
            while (1); // Halt if sensor not found
        }
        cap.setThresholds(9, 4); // Medium sensitivity (was 12,6)
        delay(50); // Allow sensor to stabilize
        
        // Turn everything off
        digitalWrite(LED_PIN, LOW);
        digitalWrite(ODOR_PIN, LOW);
        digitalWrite(REWARD_PIN, LOW);
        
        Serial.begin(115200);
        Serial.println("READY");
    }

    void checkLicks() {
        currtouched = cap.touched();
        
        // Check for touch onset on first sensor (index 0)
        if ((currtouched & _BV(0)) && !(lasttouched & _BV(0))) {
            // Valid lick detected - check timing
            unsigned long currentTime = millis();
            if (currentTime - lastLickTime >= MIN_INTERLICK_INTERVAL) {
                lastLickTime = currentTime;
                lickCount++;
                logEvent(EVENT_LICK);
                
                // Debug print for lick detection
                Serial.println("LICK_DETECTED");
            }
        }
        
        // Save current state for next comparison
        lasttouched = currtouched;
    }

public:
    void begin() {
        initializeHardware();
    }
    
    void update() {
        // Update LED state (non-blocking)
        updateLED();
        
        // Non-blocking state machine
        unsigned long currentTime = millis();
        
        // Check for licks
        checkLicks();
        
        // Check for state timeout - prevent stuck states
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
                case ITI:
                    // ITI complete, start new trial sequence
                    setState(TRIAL_INIT);
                    // Log trial start with current trial type
                    logEvent(EVENT_TRIAL_START);
                    nextStateTime = currentTime + TRIAL_INIT_DURATION;
                    break;

                case TRIAL_INIT:
                    // Start odor period
                    setState(ODOR_PERIOD);
                    setOdor(true);
                    nextStateTime = currentTime + odorDuration;  // 2s odor
                    break;

                case ODOR_PERIOD:
                    // End odor, start trace interval
                    setOdor(false);
                    setState(TRACE_INTERVAL);
                    nextStateTime = currentTime + TRACE_INTERVAL_DURATION;
                    break;

                case TRACE_INTERVAL:
                    Serial.print("DEBUG:Transitioning from TRACE_INTERVAL to REWARD_SEQUENCE, Trial=");
                    Serial.print(currentTrial);
                    Serial.print(", Type=");
                    Serial.println(currentTrialType);
                    
                    setState(REWARD_SEQUENCE);
                    if (currentTrialType == 1) {  // CS+
                        deliverReward();  // This handles the precise reward pattern timing
                    }
                    nextStateTime = currentTime + rewardDuration;
                    break;

                case REWARD_SEQUENCE:
                    Serial.print("DEBUG:Transitioning from REWARD_SEQUENCE to CONSUMATORY, Trial=");
                    Serial.print(currentTrial);
                    Serial.print(", Type=");
                    Serial.println(currentTrialType);
                    
                    setState(CONSUMATORY);
                    nextStateTime = currentTime + CONSUMATORY_DURATION;
                    break;

                case CONSUMATORY:
                    Serial.print("DEBUG:Transitioning from CONSUMATORY to TRIAL_OFF, Trial=");
                    Serial.print(currentTrial);
                    Serial.print(", Type=");
                    Serial.println(currentTrialType);
                    
                    setState(TRIAL_OFF);
                    logEvent(EVENT_TRIAL_END);
                    
                    // Prepare for next trial
                    currentTrial++;
                    
                    // Check if we've completed all trials
                    if (currentTrial >= numTrials) {
                        Serial.println("DEBUG:All trials completed, transitioning to COMPLETE");
                        setState(COMPLETE);
                        Serial.println("SESSION_COMPLETE");
                    } else {
                        // Get next trial type and start ITI
                        // Check for memory corruption
                        if (currentTrial < 0 || currentTrial >= numTrials || trialSequence == NULL) {
                            Serial.println("ERROR:MEMORY_CORRUPTION");
                            emergencyStop();
                            return;
                        }
                        
                        currentTrialType = trialSequence[currentTrial];
                        Serial.print("DEBUG:Starting next trial, Trial=");
                        Serial.print(currentTrial);
                        Serial.print(", Type=");
                        Serial.println(currentTrialType);
                        
                        setState(ITI);
                        nextStateTime = currentTime + intertrialInterval;
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
    }
    
    void processCommand(const String& command) {
        // Handle commands from Python GUI
        if (command == "RESET") {
            // Force reset the state machine to IDLE
            emergencyStop();
            return;
        }
        
        else if (command == "FORCE_IDLE") {
            // Force state machine to IDLE regardless of current state
            setState(IDLE);
            Serial.println("FORCED_TO_IDLE");
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
            
            // Parse sequence into array
            int index = 0;
            int startPos = 0;
            for (int i = 0; i <= sequenceStr.length(); i++) {
                if (i == sequenceStr.length() || sequenceStr.charAt(i) == ',') {
                    if (index < numTrials) {
                        int trialType = sequenceStr.substring(startPos, i).toInt();
                        // Validate trial type (must be 1 or 2)
                        if (trialType != 1 && trialType != 2) {
                            trialType = 1;  // Default to CS+ if invalid
                        }
                        trialSequence[index++] = trialType;
                    }
                    startPos = i + 1;
                }
            }
            
            // Reset trial counter
            currentTrial = 0;
            
            // Set initial trial type
            if (numTrials > 0) {
                currentTrialType = trialSequence[0];
            }
            
            Serial.print("SEQUENCE_RECEIVED:");
            Serial.print(numTrials);
            Serial.print(" trials (");
            
            // Count trial types
            int csPlus = 0;
            int csMinus = 0;
            for (int i = 0; i < numTrials; i++) {
                if (trialSequence[i] == 1) csPlus++;
                else if (trialSequence[i] == 2) csMinus++;
            }
            Serial.print(csPlus);
            Serial.print(" CS+, ");
            Serial.print(csMinus);
            Serial.println(" CS-)");
        }
        else if (command == "TEST_LICK") {
            // Only allow test if in IDLE state
            if (state == IDLE) {
                setState(LICK_TEST);
                Serial.println("LICK_TEST:MONITORING");
            } else {
                Serial.println("ERROR:BUSY");
            }
        }
        else if (command == "STOP_LICK_TEST") {
            // Return to IDLE state from lick test
            if (state == LICK_TEST) {
                setState(IDLE);
                Serial.println("LICK_TEST:STOPPED");
            }
        }
        else if (command == "START") {
            // Only start if in IDLE state and not running tests
            if (state == IDLE && numTrials > 0) {
                // Reset timestamp reference when starting new session
                timestampReference = millis();
                
                // Start session - send session start event first
                Serial.println("SESSION_STARTED");
                logEvent(EVENT_SESSION_START);
                
                // Initialize session
                currentTrial = 0;
                currentTrialType = trialSequence[0];
                setState(ITI);
                nextStateTime = millis() + intertrialInterval;
            } else {
                // Provide detailed error information
                Serial.print("ERROR:BUSY (State=");
                Serial.print(state);
                Serial.print(", Trials=");
                Serial.print(numTrials);
                Serial.println(")");
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
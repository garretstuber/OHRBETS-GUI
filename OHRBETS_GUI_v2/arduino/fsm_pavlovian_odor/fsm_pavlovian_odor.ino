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

// Timeout for stuck states (ms) - reset to IDLE if a state lasts too long
#define STATE_TIMEOUT 60000  // Increased to 60 seconds (was 10000ms) to accommodate long ITIs

// Lick detector configuration
#define LICK_SIGNAL_INVERTED false  // Set to false if lick gives LOW signal

// Timing precision: use milliseconds for all timestamps and state transitions
// State machine: use non-blocking design with millis() for state transitions

// --- Reward Timing --- 
// Default values, now configurable via serial command
int rewardPulse1Duration = 40;    // First reward pulse (ms)
int rewardDelayDuration = 140;   // Delay between pulses (ms)
int rewardPulse2Duration = 40;    // Second reward pulse (ms)

class PavlovianController {
private:
    // State machine states
    enum State {
        IDLE,
        ITI,
        TRIAL_INIT,
        ODOR_PERIOD,
        TRACE_INTERVAL,
        // Reward sequence states (non-blocking)
        REWARD_PULSE1, 
        REWARD_DELAY, 
        REWARD_PULSE2,
        // -- End Reward Sequence --
        CONSUMATORY,
        TRIAL_OFF,
        COMPLETE,
        // Test states (blocking test functions are used now)
        TEST_ODOR, 
        TEST_REWARD, 
        LICK_TEST,
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
    unsigned long iti_min_ms = DEFAULT_ITI_DURATION;
    unsigned long iti_max_ms = DEFAULT_ITI_DURATION + 5000;
    int odorDuration = DEFAULT_ODOR_DURATION;
    // Reward timings are global variables now
    
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
        // Prevent setting state if currently in a blocking test function
        if (state == TEST_ODOR || state == TEST_REWARD) {
            Serial.println("WARNING: Attempted state change during blocking test.");
            return; 
        }
        state = newState;
        stateStartTime = millis(); // Reset state timer
        printStateTransition(oldState, newState);
        
        // If entering IDLE state, ensure all outputs are off and reset flags
        if (newState == IDLE) {
            if (odorActive) setOdor(false);
            if (rewardActive) setReward(false);
            inManualControl = false;
            if (oldState == LICK_TEST) {
                lickCount = 0;
                lastLickTime = 0;
            }
        }
        
        // Set manual control flag for manual states
        if (newState == MANUAL_ODOR_CONTROL || newState == MANUAL_REWARD_CONTROL) {
            inManualControl = true;
        }
        // Clear manual control flag when exiting manual states
        else {
             inManualControl = false;
        }
    }
    
    // Direct odor test with precise timing (Uses global odorDuration)
    void directOdorTest() {
        Serial.println("DIRECT_ODOR_TEST_START");
        digitalWrite(LED_PIN, HIGH);
        setOdor(true);
        delay(odorDuration); // Use variable
        setOdor(false);
        digitalWrite(LED_PIN, LOW);
        Serial.println("DIRECT_ODOR_TEST_COMPLETE");
    }
    
    // Direct reward test uses global variables for duration
    void directRewardTest() {
        Serial.println("DIRECT_REWARD_TEST_START");
        digitalWrite(LED_PIN, HIGH);
        setReward(true);
        Serial.println("REWARD_PULSE1_ON");
        delay(rewardPulse1Duration); // Use variable
        setReward(false);
        digitalWrite(LED_PIN, LOW);
        Serial.println("REWARD_PULSE1_OFF");
        delay(rewardDelayDuration); // Use variable
        digitalWrite(LED_PIN, HIGH);
        setReward(true);
        Serial.println("REWARD_PULSE2_ON");
        delay(rewardPulse2Duration); // Use variable
        setReward(false);
        digitalWrite(LED_PIN, LOW);
        Serial.println("REWARD_PULSE2_OFF");
        Serial.println("DIRECT_REWARD_TEST_COMPLETE");
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

    // Function to generate random ITI in ms, sampled in 1s steps
    unsigned long getRandomITI() {
        // Ensure min <= max
        if (iti_min_ms > iti_max_ms) {
           iti_max_ms = iti_min_ms; // Or swap them, depending on desired behavior
        }
        unsigned long range_steps = (iti_max_ms - iti_min_ms) / 1000;
        unsigned long random_step = random(range_steps + 1);
        unsigned long duration = iti_min_ms + (random_step * 1000);
        Serial.print("DEBUG:Generated ITI Duration = ");
        Serial.println(duration);
        return duration;
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
        
        // Check for licks (less frequently during ITI)
        static unsigned long lastLickCheckTime = 0;
        // Check every 10ms normally, but only every 100ms during ITI
        unsigned long lickCheckInterval = (state == ITI) ? 100 : 10; 
        if (currentTime - lastLickCheckTime >= lickCheckInterval) {
            checkLicks();
            lastLickCheckTime = currentTime;
        }
        
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
        if (state != IDLE && state != COMPLETE && !inManualControl && currentTime >= nextStateTime) {
            switch (state) {
                case ITI:
                    // ITI duration has elapsed
                    Serial.print("DEBUG: Exiting ITI state at "); 
                    Serial.println(currentTime);
                    setState(TRIAL_INIT);
                    logEvent(EVENT_TRIAL_START); // Log START *after* ITI
                    nextStateTime = currentTime + TRIAL_INIT_DURATION;
                    break;

                case TRIAL_INIT:
                    setState(ODOR_PERIOD);
                    setOdor(true);
                    nextStateTime = currentTime + odorDuration;
                    break;

                case ODOR_PERIOD:
                    setOdor(false);
                    setState(TRACE_INTERVAL);
                    nextStateTime = currentTime + TRACE_INTERVAL_DURATION;
                    break;

                case TRACE_INTERVAL:
                    if (currentTrialType == 1) { // CS+
                        setState(REWARD_PULSE1);
                        setReward(true);
                        nextStateTime = currentTime + rewardPulse1Duration;
                    } else { // CS-
                        setState(CONSUMATORY);
                        nextStateTime = currentTime + CONSUMATORY_DURATION;
                    }
                    break;

                // Non-blocking reward sequence states
                case REWARD_PULSE1:
                    setReward(false);
                    setState(REWARD_DELAY);
                    nextStateTime = currentTime + rewardDelayDuration;
                    break;
                
                case REWARD_DELAY:
                    setReward(true);
                    setState(REWARD_PULSE2);
                    nextStateTime = currentTime + rewardPulse2Duration;
                    break;
                
                case REWARD_PULSE2:
                    setReward(false);
                    setState(CONSUMATORY);
                    nextStateTime = currentTime + CONSUMATORY_DURATION;
                    break;

                case CONSUMATORY:
                    setState(TRIAL_OFF);
                    logEvent(EVENT_TRIAL_END);
                    nextStateTime = currentTime;
                    break;
                    
                case TRIAL_OFF:
                    currentTrial++;
                    if (currentTrial >= numTrials) {
                        setState(COMPLETE);
                        Serial.println("SESSION_COMPLETE");
                    } else {
                        if (currentTrial < 0 || currentTrial >= numTrials || trialSequence == NULL) {
                            Serial.println("ERROR:MEMORY_CORRUPTION");
                            emergencyStop();
                            return;
                        }
                        currentTrialType = trialSequence[currentTrial];
                        unsigned long nextITI = getRandomITI(); 
                        setState(ITI); 
                        nextStateTime = currentTime + nextITI; 
                        Serial.print("DEBUG: Entering ITI state for Trial ");
                        Serial.print(currentTrial + 1);
                        Serial.print(", Type=");
                        Serial.print(currentTrialType);
                        Serial.print(", Duration=");
                        Serial.println(nextITI);
                    }
                    break;

                case COMPLETE:
                    setState(IDLE);
                    break;

                default:
                    setState(IDLE);
                    break;
            }
        }
        
        // Check for lick events (non-blocking)
        checkLicks(); 
        
        // Safety checks (non-blocking)
        if (rewardActive && !inManualControl && 
            state != REWARD_PULSE1 && state != REWARD_PULSE2) { 
            setReward(false);
            Serial.println("SAFETY:REWARD_OFF");
        }
        
        if (odorActive && !inManualControl && 
            state != ODOR_PERIOD && state != TEST_ODOR) {
            setOdor(false);
            Serial.println("SAFETY:ODOR_OFF");
        }
    }
    
    void processCommand(const String& command) {
        // Handle commands from Python GUI
        if (command == "RESET") {
            emergencyStop();
            return;
        }
        else if (command == "FORCE_IDLE") {
            setState(IDLE);
            Serial.println("FORCED_TO_IDLE");
            return;
        }
        
        // --- Timing and Sequence Commands --- 
        if (command.startsWith("SET_ITI_RANGE:")) { // Command for ITI range
            int comma1 = command.indexOf(',', 14); // Index after "SET_ITI_RANGE:"
            if (comma1 > 0) {
                iti_min_ms = command.substring(14, comma1).toInt();
                iti_max_ms = command.substring(comma1 + 1).toInt();
                
                // Validation
                if (iti_min_ms < 1000) iti_min_ms = 1000;
                if (iti_max_ms < iti_min_ms) iti_max_ms = iti_min_ms;
                if (iti_max_ms > 60000) iti_max_ms = 60000; // Max 60s
                
                Serial.print("ITI_RANGE_SET:");
                Serial.print(iti_min_ms);
                Serial.print("-");
                Serial.print(iti_max_ms);
                Serial.println("ms");
            } else {
                 Serial.println("ERROR:INVALID_ITI_RANGE_FORMAT");
            }
        }
        else if (command.startsWith("SET_REWARD_TIMING:")) { // New command for reward timing
            // Format: SET_REWARD_TIMING:pulse1_ms,delay_ms,pulse2_ms
            int comma1 = command.indexOf(',', 18); // Index after "SET_REWARD_TIMING:"
            int comma2 = command.indexOf(',', comma1 + 1);
            
            if (comma1 > 0 && comma2 > 0) {
                // Parse values
                int p1 = command.substring(18, comma1).toInt();
                int d = command.substring(comma1 + 1, comma2).toInt();
                int p2 = command.substring(comma2 + 1).toInt();
                
                // Basic validation (ensure positive values)
                rewardPulse1Duration = (p1 > 0) ? p1 : REWARD_PULSE1_DURATION; // Keep default if invalid
                rewardDelayDuration = (d >= 0) ? d : REWARD_DELAY_DURATION; // Allow 0 delay
                rewardPulse2Duration = (p2 > 0) ? p2 : REWARD_PULSE2_DURATION; // Keep default if invalid
                
                Serial.print("REWARD_TIMING_SET:");
                Serial.print(rewardPulse1Duration);
                Serial.print(",");
                Serial.print(rewardDelayDuration);
                Serial.print(",");
                Serial.println(rewardPulse2Duration);
            } else {
                Serial.println("ERROR:INVALID_REWARD_TIMING_FORMAT");
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
        
        // --- Session Control Commands --- 
        else if (command == "START") {
            if (state == IDLE && numTrials > 0) {
                timestampReference = millis();
                Serial.println("SESSION_STARTED");
                logEvent(EVENT_SESSION_START);
                currentTrial = 0;
                currentTrialType = trialSequence[0];
                unsigned long firstITI = getRandomITI();
                setState(ITI);
                nextStateTime = millis() + firstITI; 
                Serial.print("DEBUG: Starting First ITI, Duration=");
                Serial.println(firstITI);
            } else {
                Serial.print("ERROR:BUSY (State=");
                Serial.print(state);
                Serial.print(", Trials=");
                Serial.print(numTrials);
                Serial.println(")");
            }
        }
        else if (command == "ABORT") {
            emergencyStop();
        }
        
        // --- Hardware Test Commands --- 
        else if (command == "TEST_ODOR") {
            if (state == IDLE) {
                directOdorTest();
            } else {
                Serial.println("ERROR:BUSY");
            }
        }
        else if (command == "TEST_REWARD") {
            if (state == IDLE) {
                directRewardTest();
            } else {
                Serial.println("ERROR:BUSY");
            }
        }
        
        // --- Manual Control Commands --- 
        else if (command == "MANUAL_REWARD_ON") {
            if (state == IDLE) {
                inManualControl = true; // Set flag BEFORE changing state
                setState(MANUAL_REWARD_CONTROL);
                setReward(true);
                Serial.println("MANUAL_REWARD:ON");
            } else {
                Serial.println("ERROR:BUSY (Cannot manually control while busy)");
            }
        }
        else if (command == "MANUAL_REWARD_OFF") {
            setReward(false);
            Serial.println("MANUAL_REWARD:OFF");
            // Always return to IDLE after manual off
            setState(IDLE);
        }
        else if (command == "MANUAL_ODOR_ON") {
            if (state == IDLE) {
                inManualControl = true; // Set flag BEFORE changing state
                setState(MANUAL_ODOR_CONTROL);
                setOdor(true);
                Serial.println("MANUAL_ODOR:ON");
            } else {
                Serial.println("ERROR:BUSY (Cannot manually control while busy)");
            }
        }
        else if (command == "MANUAL_ODOR_OFF") {
            setOdor(false);
            Serial.println("MANUAL_ODOR:OFF");
            // Always return to IDLE after manual off
            setState(IDLE);
        }
        
        // --- Lick Test Commands --- 
        else if (command == "TEST_LICK") {
            if (state == IDLE) {
                setState(LICK_TEST);
                Serial.println("LICK_TEST:MONITORING");
            } else {
                Serial.println("ERROR:BUSY");
            }
        }
        else if (command == "STOP_LICK_TEST") {
            if (state == LICK_TEST) {
                setState(IDLE);
                Serial.println("LICK_TEST:STOPPED");
            }
        }
        else if (command == "RESET_LICK_COUNT") {
            lickCount = 0;
            Serial.println("LICK_COUNT_RESET");
        }
        
        // --- Status and Debug Commands --- 
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
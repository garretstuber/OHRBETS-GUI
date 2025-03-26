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

// Timing precision: use microseconds for all timestamps
// State machine: use non-blocking design with millis() for state transitions

class PavlovianController {
private:
    // State machine states
    enum State {
        IDLE,
        INTERTRIAL,
        ODOR,
        REWARD,
        COMPLETE
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
    int rewardDuration = 500;       // Configurable
    
    // LED blink timing (non-blocking)
    unsigned long ledOffTime = 0;
    bool ledBlinking = false;
    
    // Methods for hardware control
    void setOdor(int type, bool state) {
        digitalWrite(type == 1 ? ODOR1_PIN : ODOR2_PIN, state ? HIGH : LOW);
        logEvent(state ? EVENT_ODOR_ON : EVENT_ODOR_OFF);
    }
    
    void setReward(bool state) {
        digitalWrite(REWARD_PIN, state ? HIGH : LOW);
        logEvent(state ? EVENT_REWARD_ON : EVENT_REWARD_OFF);
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
                    // Turn off odor and transition to reward
                    setOdor(currentTrialType, false);
                    state = REWARD;
                    stateStartTime = currentTime;
                    nextStateTime = currentTime + rewardDuration;
                    
                    // Only deliver reward for CS+ (type 1)
                    if (currentTrialType == 1) {
                        setReward(true);
                    }
                    break;
                    
                case REWARD:
                    // End of trial
                    if (currentTrialType == 1) {
                        setReward(false);
                    }
                    
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
                    
                default:
                    break;
            }
        }
        
        // Check for lick events if using lick detector
        static bool lastLickState = HIGH;
        bool currentLickState = digitalRead(LICK_PIN);
        if (currentLickState != lastLickState && currentLickState == LOW) {
            // Lick detected (falling edge)
            logEvent(EVENT_LICK);
        }
        lastLickState = currentLickState;
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
            setOdor(1, false);
            setOdor(2, false);
            setReward(false);
            state = IDLE;
            Serial.println("SESSION_ABORTED");
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
    
    // No delay needed - the Arduino loop is already fast enough
    // and we're using non-blocking timing throughout
} 
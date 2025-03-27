# OHRBETS GUI TODO List

## Completed
- [x] Implement hardware debouncing for lick detection (67ms minimum inter-lick interval)
- [x] Reorganize the state machine to follow logical trial flow
- [x] Update ITI settings to use random sampling between min-max range
- [x] Add condition fields and treatment field to GUI

## High Priority
- [ ] Add phase-specific lick counters for CS+ and CS- trials
  - [ ] Count licks during odor period (2s)
  - [ ] Count licks during trace interval (1s)
  - [ ] Count licks during consummatory period (5s)
  - [ ] Display separate counters for CS+ and CS- trials
  - [ ] Add average licks per phase per trial type

## Documentation
- [ ] Add comprehensive comments to app.py
  - [ ] Document event code system
  - [ ] Document ArduinoInterface class
  - [ ] Document session state management
  - [ ] Document metrics calculation
  - [ ] Document data handling system

- [ ] Add comprehensive comments to fsm_pavlovian_odor.ino
  - [ ] Document hardware pin configuration
  - [ ] Document timing parameters
  - [ ] Document state machine states
  - [ ] Document hardware control methods
  - [ ] Document safety features
  - [ ] Document event logging system

## Future Enhancements
- [ ] Add data visualization improvements
  - [ ] Real-time lick rate plots
  - [ ] Trial-by-trial analysis
  - [ ] Phase-specific analysis

- [ ] Add data export enhancements
  - [ ] Include metadata in CSV output
  - [ ] Add phase-specific lick counts
  - [ ] Add timing information for each phase

- [ ] Add hardware testing features
  - [ ] Automated solenoid testing
  - [ ] Lick sensor calibration
  - [ ] Timing verification

## Bug Fixes
- [ ] Verify ITI timing accuracy
- [ ] Check trial type determination logic
- [ ] Validate timestamp handling

## Known Issues
- [ ] Need to implement proper phase-specific lick counting
- [ ] Need to improve error handling in Arduino communication 
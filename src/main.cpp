#include <Arduino.h>

#define PPS_PIN 2
#define LED_PIN 13
#define SYNCHRONIZATION_RATE 10
#define alpha 0.3
#define beta 0.2
// #define alpha 1
// #define beta 1
#define FLIP_DELAY 500000

volatile float drift_coef = 1;
volatile float ema_drift_coef = 1;
volatile uint32_t last_sync_local_timestamp;
volatile uint32_t new_sync_local_timestamp;
volatile uint32_t last_sync_source_timestamp;
volatile uint32_t new_sync_source_timestamp;
volatile bool time_to_sync;

void interrupt_routine();
void sleep_until(uint32_t);
uint32_t time();
void flip_pin(int);
void check_sync();

void setup() {
    Serial.begin(115200);
    attachInterrupt(digitalPinToInterrupt(PPS_PIN), interrupt_routine, FALLING);

    pinMode(LED_PIN, OUTPUT);
    Serial.println("Setup complete");
}

void loop() {
    // Serial.println("Hey!");
    // delay(1000);
    flip_pin(LED_PIN);
    check_sync();

    // Tasks:
        // Get pps signal as interrupt
        // Calculate drift each SYNC_RATE seconds/pps signals
        // Make new time source available
        // In the main thread keep control of the application
            // Ask for sync (in case of mote)
            // Toggle pin
}

void interrupt_routine() {
    static long pps_counter = 0;
    uint32_t now = micros();

    pps_counter++;
    if (pps_counter % SYNCHRONIZATION_RATE == 0) {
        new_sync_local_timestamp = now;
        new_sync_source_timestamp = pps_counter * 1000000;
        time_to_sync = true;
    }
}

uint32_t time() {
    return (micros()-last_sync_local_timestamp)/drift_coef + last_sync_source_timestamp;
}

void flip_pin(int pin) {
    static const uint32_t DELTA = 10000000;

    static int counter;
    static bool led_status = false;
    static uint32_t next_wakeup = ((time()/1000000) % 1 + 1) * 1000000 + 100000; // added small offter of 100ms so that the sync routine doesn't happen at the same time as the flip

    if (time() - next_wakeup + DELTA > DELTA) { // This DELTA is needed because of the micros() rollover each ~71 minutes
        digitalWrite(LED_PIN, led_status);
        led_status = !led_status;
        next_wakeup += 500000;
        // Serial.print("Flip! ");
        // Serial.print(counter++);
        // Serial.print(" time: ");
        // Serial.println(time());
    }
}

void check_sync() {
    if (time_to_sync) {
        float instant_drift_coef;

        instant_drift_coef = (float (new_sync_local_timestamp - last_sync_local_timestamp)) / ((float)(new_sync_source_timestamp - last_sync_source_timestamp));
        ema_drift_coef = ema_drift_coef*(1-alpha) + instant_drift_coef*alpha;
        drift_coef     = ema_drift_coef*(1-beta)  + instant_drift_coef*beta;

        last_sync_local_timestamp = new_sync_local_timestamp;
        last_sync_source_timestamp = new_sync_source_timestamp;
        time_to_sync = false;

        // Serial.print("Drift: ");
        // Serial.println((drift_coef-1)*1000000);
    }
}

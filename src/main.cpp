#include <Arduino.h>

#define PPS_PIN 2
#define LED_PIN 13
#define SYNCHRONIZATION_RATE 10
#define alpha 0.3
#define beta 0.2
#define SLEEP_FACTOR 0.8
#define MINIMUM_SLEEP_TIME 0 // TODO: review this value
#define FLIP_DELAY 500000

volatile bool led_status = 0;
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

void setup() {
    Serial.begin(115200);
    attachInterrupt(digitalPinToInterrupt(PPS_PIN), interrupt_routine, FALLING);

    pinMode(LED_PIN, OUTPUT);
}

void loop() {
    // Serial.println("Hey!");
    // delay(1000);
    flip_pin(LED_PIN);

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

    pps_counter++;
    if (pps_counter % SYNCHRONIZATION_RATE == 0) {
        new_sync_local_timestamp = micros();
        new_sync_source_timestamp = pps_counter * 1000000;
        time_to_sync = true;
    }
}

void sleep_until(uint32_t wakeup_time) {
    uint32_t next_sleep_duration = uint32_t ((wakeup_time - micros())*SLEEP_FACTOR);
    while (next_sleep_duration > MINIMUM_SLEEP_TIME && wakeup_time > micros()){
        Serial.println(next_sleep_duration);
        delayMicroseconds(next_sleep_duration);
        next_sleep_duration = uint32_t (wakeup_time - micros())*SLEEP_FACTOR;
    }
}

uint32_t time() {
    return (micros()-last_sync_local_timestamp)/drift_coef + last_sync_source_timestamp;
}

void flip_pin(int pin) {
    static uint32_t next_wakeup = micros() + 500000;
    if (time() > next_wakeup) {
        digitalWrite(LED_PIN, led_status);
        led_status = !led_status;
        next_wakeup += 500000;
        Serial.print("Flip! ");
        Serial.println(led_status);
    }
}

#include <Arduino.h>

#define PPS_PIN 2
#define LED_PIN 13
#define SYNCHRONIZATION_RATE 10
#define alpha 0.3
#define beta 0.2
#define SLEEP_FACTOR 0.8
#define MINIMUM_SLEEP_TIME 0 // TODO: review this value

volatile bool led_status = 0;

void interrupt_routine();
void sleep_until(uint32_t);

void setup() {
    Serial.begin(115200);
    attachInterrupt(digitalPinToInterrupt(PPS_PIN), interrupt_routine, FALLING);

    pinMode(LED_PIN, OUTPUT);
}

void loop() {
    // Serial.println("Hey!");
    // delay(1000);
    static uint32_t next_wakeup = micros() + 500000;

    sleep_until(next_wakeup);
    next_wakeup += 500000;
    led_status = !led_status;
    Serial.print("Flip! ");
    Serial.println(led_status);
    digitalWrite(LED_PIN, led_status);

    // Tasks:
        // Get pps signal as interrupt
        // Calculate drift each SYNC_RATE seconds/pps signals
        // Make new time source available
        // In the main thread keep control of the application
            // Ask for sync (in case of mote)
            // Toggle pin
}

void interrupt_routine() {
    led_status = !led_status;
}

void sleep_until(uint32_t wakeup_time) {
    uint32_t next_sleep_duration = uint32_t ((wakeup_time - micros())*SLEEP_FACTOR);
    while (next_sleep_duration > MINIMUM_SLEEP_TIME && wakeup_time > micros()){
        Serial.println(next_sleep_duration);
        delayMicroseconds(next_sleep_duration);
        next_sleep_duration = uint32_t (wakeup_time - micros())*SLEEP_FACTOR;
    }
}

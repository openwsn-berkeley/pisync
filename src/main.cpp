#include <Arduino.h>

#define PPS_PIN 2
#define LED_PIN 13
#define SYNCHRONIZATION_RATE 10
#define alpha 0.3
#define beta 0.2

volatile bool led_status = 0;

void interrupt_routine();

void setup() {
    Serial.begin(115200);
    attachInterrupt(digitalPinToInterrupt(PPS_PIN), interrupt_routine, FALLING);

    pinMode(LED_PIN, OUTPUT);
}

void loop() {
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

#include <Arduino.h>
#include <DueTimer.h>
#include "NanoClock.h"

#define PPS_PIN 2
#define LED_PIN 13
#define SYNCHRONIZATION_RATE 10
#define alpha 0.3
#define beta 0.2
// #define alpha 1
// #define beta 1
#define FLIP_DELAY 500000

volatile double drift_coef = 0;
volatile double ema_drift_coef = 0;
volatile bool time_to_sync = false;
volatile bool led_pin_state = false;

volatile double local_delta;
volatile double source_delta;
volatile double flip_delay_mod;

NanoClock nano_clock = NanoClock();

void interrupt_routine();
void sleep_until(uint32_t);
uint32_t time();
void flip_pin_handler();
void check_sync();
void nanoClock_callback();
void setLedLow();
void setLedHigh();
void flip_reset();
// uint32_t micros_mod();

void setup() {
    Serial.begin(115200);
    attachInterrupt(digitalPinToInterrupt(PPS_PIN), interrupt_routine, FALLING); // PPS interrupt
    Timer3.attachInterrupt(flip_pin_handler).start(FLIP_DELAY); // Pin flip interrupt
    Timer4.attachInterrupt(flip_reset);
    Timer8.attachInterrupt(nanoClock_callback); // NanoClock callback
    nano_clock.start();
    pinMode(LED_PIN, OUTPUT);
    Serial.println("Setup complete\n\n");
}

void loop() {
    // flip_pin(LED_PIN);
    check_sync();
}

void nanoClock_callback() {
    // Serial.println("-- NanoClock callback");
}

void interrupt_routine() {
    uint32_t now = nano_clock.getClockTicks();
    static uint32_t pps_counter = 0;
    static uint32_t last_sync = 0;
    double elapsed_useconds_rounded;

    pps_counter++;
    if (pps_counter % SYNCHRONIZATION_RATE == 1) {
        if (last_sync == 0) {
            last_sync = now;
            return;
        }

        if (now - last_sync == 0) {
            return;
        }

        local_delta = nano_clock.ticksToNanos(static_cast<uint64_t> (now - last_sync))/1000.;
        source_delta = round(local_delta/1000000)*1000000;

        last_sync = now;
        time_to_sync = true;

    } else if (pps_counter % SYNCHRONIZATION_RATE == 2) {
        Timer4.start(250000*drift_coef);
    }
}

void flip_reset() {
    setLedLow();
    Timer3.start(flip_delay_mod);
    led_pin_state = false;
    Timer4.stop();
}

void flip_pin_handler() {
    led_pin_state = !led_pin_state;
    if (led_pin_state) {
        setLedHigh();
    } else {
        setLedLow();
    }

}

void setLedHigh() {
    REG_PIOB_SODR = 0x1 << 27; // set pin 13 HIGH
}

void setLedLow() {
    REG_PIOB_CODR = 0x1 << 27; // set pin 13 LOW
}

void check_sync() {
    if (time_to_sync) {
        time_to_sync = false;
        double instant_drift_coef;

        instant_drift_coef = local_delta / source_delta;
        if (abs(instant_drift_coef-1)*1000*1000 > 100) {
            return; // drift too big, something must have gone wrong
        }

        if (drift_coef == 0) { // this is the first sync
            ema_drift_coef = instant_drift_coef;
            drift_coef     = instant_drift_coef;
        } else {
            ema_drift_coef = ema_drift_coef*(1-alpha) + instant_drift_coef*alpha;
            drift_coef     = ema_drift_coef*(1-beta)  + instant_drift_coef*beta;
        }

        flip_delay_mod = FLIP_DELAY*drift_coef;

        // Serial.print("Instant drift: ");
        // Serial.println((instant_drift_coef-1)*1000000);
        // Serial.print("Smooth drift: ");
        // Serial.println((drift_coef-1)*1000000);
        // Serial.print("Local delta: ");
        // Serial.println(local_delta);
        // Serial.print("Source delta: ");
        // Serial.println(source_delta);
        // Serial.print("New delay: ");
        // Serial.println(FLIP_DELAY*drift_coef);

    }
}

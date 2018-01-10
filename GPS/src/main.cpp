#include <Arduino.h>
#include <DueTimer.h>

#define PPS_PIN 2
#define LED_PIN 13
#define SYNCHRONIZATION_RATE 5
#define alpha 0.3
#define beta 0.2
// #define alpha 1
// #define beta 1
#define FLIP_DELAY 500000

volatile double drift_coef = 1.0;
volatile double ema_drift_coef = 1.0;
volatile bool time_to_sync = false;
volatile bool led_pin_state = false;

volatile uint32_t local_delta;
volatile uint32_t source_delta;

void interrupt_routine();
void sleep_until(uint32_t);
uint32_t time();
void flip_pin_handler();
void check_sync();
uint32_t micros_mod();

void setup() {
    Serial.begin(115200);
    attachInterrupt(digitalPinToInterrupt(PPS_PIN), interrupt_routine, FALLING); // PPS interrupt
    Timer3.attachInterrupt(flip_pin_handler).start(FLIP_DELAY); // Pin flip interrupt
    pinMode(LED_PIN, OUTPUT);
    Serial.println("Setup complete\n\n");
}

void loop() {
    // flip_pin(LED_PIN);
    check_sync();
}

void interrupt_routine() {
    static uint32_t pps_counter = 0;
    static uint32_t last_sync = 0;
    uint32_t now = micros_mod();
    double elapsed_useconds_rounded;

    pps_counter++;
    if (pps_counter % SYNCHRONIZATION_RATE == 1) {
        if (last_sync == 0) {
            last_sync = now;
            return;
        }

        // DEBUGGING
        if (now < last_sync) {
            Serial.println("-- Did rollover");
        }

        elapsed_useconds_rounded = round(((now - last_sync))/1000000.)*1000000;

        if (elapsed_useconds_rounded == 0) {
            return;
        }

        // DEBUGGING
        Serial.print("Elapsed seconds: ");
        Serial.println(elapsed_useconds_rounded/1000000);

        local_delta = now - last_sync;
        source_delta = elapsed_useconds_rounded;

        last_sync = now;
        time_to_sync = true;

    } else if (pps_counter % SYNCHRONIZATION_RATE == 2) {
        Timer3.stop();
        Timer3.start(FLIP_DELAY*drift_coef);

        if (led_pin_state == true) {
            flip_pin_handler();
        }
        Serial.print("New delay: ");
        Serial.println(FLIP_DELAY*drift_coef);

    }
}

void flip_pin_handler() {
    static int counter = 0;
    counter++;

    led_pin_state = !led_pin_state;
    digitalWrite(LED_PIN, led_pin_state);
}

void check_sync() {
    if (time_to_sync) {
        double instant_drift_coef;

        instant_drift_coef = ((double) local_delta) / ((double) source_delta);
        ema_drift_coef = ema_drift_coef*(1-alpha) + instant_drift_coef*alpha;
        drift_coef     = ema_drift_coef*(1-beta)  + instant_drift_coef*beta;

        Serial.print("Instant drift: ");
        Serial.println((instant_drift_coef-1)*1000000);
        Serial.print("Local delta: ");
        Serial.println(local_delta);
        Serial.print("Source delta: ");
        Serial.println(source_delta);

        time_to_sync = false;
    }
}

uint32_t micros_mod() {
    uint32_t delta = -20*1000*1000;
    return micros() + delta;
}

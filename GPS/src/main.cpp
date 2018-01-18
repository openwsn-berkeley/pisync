#include <Arduino.h>
#include "NanoClock.h"
#include "PinFlipper.h"

#define PPS_PIN 2
#define SYNCHRONIZATION_RATE 10
#define alpha 0.3
#define beta 0.2


volatile double drift_coef = 0;
volatile double ema_drift_coef = 0;
volatile bool time_to_sync = false;
volatile bool led_pin_state = false;
volatile uint32_t pps_counter = 0;
volatile bool sync_pps = true;

volatile double local_delta;
volatile double source_delta;

NanoClock nano_clock = NanoClock();
PinFlipper pin_flipper = PinFlipper();

void interrupt_routine();
void check_sync();
void sync_pps_counter();
void check_pps_counter_sync();


void setup() {
    Serial.begin(115200);
    Serial3.begin(9600);
    Serial.println("===== Hello =====");
    pinMode(PPS_PIN, INPUT);
    attachInterrupt(digitalPinToInterrupt(PPS_PIN), interrupt_routine, FALLING); // PPS interrupt
    // Timer2.attachInterrupt(flip_pin_handler); // Pin flip interrupt
    // Timer4.attachInterrupt(flip_reset);
    // Timer8.attachInterrupt(nanoClock_callback); // NanoClock callback - empty

    nano_clock.start();
    pin_flipper.setup();

    // sync_pps_counter();

    Serial.println("Setup complete\n\n");
}

void loop() {
    // flip_pin(LED_PIN);
    check_sync();
    check_pps_counter_sync();
}

void interrupt_routine() {
    uint32_t now = nano_clock.getClockTicks();
    static uint32_t last_sync = 0;

    // Serial.println("PPS signal!");
    Serial.println(pps_counter);

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
        pin_flipper.reset();
        pin_flipper.setDriftRate(drift_coef);
    } else if (pps_counter % SYNCHRONIZATION_RATE == 3) {
        // Serial.println("Recalibrate pps_counter");
        sync_pps = true;
    }
}


void check_sync() {
    if (time_to_sync) {
        // Serial.println("Time to sync!");

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

        // flip_delay_adjusted = static_cast<uint32_t> (FLIP_DELAY*drift_coef);

        // Serial.print("Instant drift: ");
        // Serial.println((instant_drift_coef-1)*1000000);
        // Serial.print("Smooth drift: ");
        // Serial.println((drift_coef-1)*1000000);
        // Serial.print("Local delta: ");
        // Serial.println(local_delta);
        // Serial.print("Source delta: ");
        // Serial.println(source_delta);
        // Serial.print("New delay: ");
        // Serial.println(flip_delay_adjusted);

    }
}


void check_pps_counter_sync() {
    if (sync_pps) {
        sync_pps = false;
        sync_pps_counter();
    }
}


void sync_pps_counter() {
    // Serial.println("Beginning sync_pps_counter");
    bool pps_counter_set = false;
    int position_counter = 0;
    char nmea_gprmc[] = "SGPRMC";
    bool is_gprms = false;
    char ch;

    while (true) {
        while(Serial3.available()) {
            ch = Serial3.read();
            // Serial.print(ch);

            if (position_counter < 6 & ch != nmea_gprmc[position_counter]) {
                position_counter = 0;
            }

            position_counter++;

            if (position_counter == 6) {
                is_gprms = true;
            }

            if (is_gprms) {
                if (position_counter == 12) {
                    pps_counter = int(ch-'0')*10;
                } else if (position_counter == 13) {
                    pps_counter += int(ch-'0');
                    // Serial.print("pps_counter set to: ");
                    // Serial.println(pps_counter);
                    return;
                }
            }
        }
    }
    Serial.println("Something went wrong with sync_pps_counter");
}

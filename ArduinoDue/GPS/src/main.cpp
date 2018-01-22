#include <Arduino.h>
#include "NanoClock.h"
#include "PinFlipper.h"
#include "Drifter.h"

#define PPS_PIN 2
#define SYNCHRONIZATION_RATE 10

volatile double drift_coef    = 0;
volatile uint32_t pps_counter = 0;
volatile bool sync_pps        = true;

NanoClock nano_clock          = NanoClock();
PinFlipper pin_flipper        = PinFlipper();
Drifter drifter               = Drifter();

void interrupt_routine();
void sync_pps_counter();
void check_pps_counter_sync();


void setup() {
    Serial.begin(115200);
    Serial3.begin(9600);

    Serial.println("===== Hello =====");

    pinMode(PPS_PIN, INPUT);
    attachInterrupt(digitalPinToInterrupt(PPS_PIN), interrupt_routine, FALLING);

    nano_clock.start();
    pin_flipper.setup();

    Serial.println("Setup complete\n\n");
}

void loop() {
    // flip_pin(LED_PIN);
    // check_sync();
    double new_drift = drifter.processSyncData();
    if (new_drift != 0) {
        // Serial.print("New drift: ");
        // Serial.println((new_drift-1)*1000000);
        drift_coef = new_drift;
    }

    check_pps_counter_sync();
}

void interrupt_routine() {
    uint32_t now = nano_clock.getClockTicks();
    static uint32_t last_sync = 0;
    double local_delta;
    double source_delta;

    // Serial.println("PPS signal!");
    // Serial.println(pps_counter);

    pps_counter++;
    if (pps_counter % SYNCHRONIZATION_RATE == 1) {
        // Serial.println("First case");
        if (last_sync == 0) {
            last_sync = now;
            return;
        }

        if (now - last_sync == 0) {
            return;
        }

        local_delta = nano_clock.ticksToNanos(static_cast<uint64_t> (now - last_sync))/1000.;
        source_delta = round(local_delta/1000000)*1000000;

        drifter.addSyncData(local_delta, source_delta);

        last_sync = now;
        // time_to_sync = true;

    } else if (pps_counter % SYNCHRONIZATION_RATE == 2) {
        // Serial.println("Second case");
        pin_flipper.reset();
        // pin_flipper.scheduleReset(100); // TODO: test this and then go back to previous line implementation
        pin_flipper.setDriftRate(drift_coef);
    } else if (pps_counter % SYNCHRONIZATION_RATE == 3) {
        // Serial.println("Third case");
        // Serial.println("Recalibrate pps_counter");
        sync_pps = true;
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
    int position_counter = 0;
    char nmea_gprmc[] = "SGPRMC";
    bool is_gprms = false;
    char ch;

    while (true) {
        while(Serial3.available()) {
            ch = Serial3.read();
            // Serial.print(ch);

            if ((position_counter < 6) & (ch != nmea_gprmc[position_counter])) {
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

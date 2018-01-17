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
// #define FLIP_DELAY 500000 // value in microseconds
#define FLIP_DELAY 21*1000*1000// value in timer ticks with timer @ 32 MHz
#define DRIFT_THRESHOLD 21*1000 // value in timer ticks with timer @ 32 MHz


volatile double drift_coef = 0;
volatile double ema_drift_coef = 0;
volatile bool time_to_sync = false;
volatile bool led_pin_state = false;
volatile uint32_t pps_counter = 0;

volatile double local_delta;
volatile double source_delta;
volatile uint32_t flip_delay_adjusted;

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
void setup_pin_flip_timer();
void set_pps_counter();
// uint32_t micros_mod();

// TODO: rewrite pin flip routine without DueLibrary

void setup() {
    Serial.begin(115200);
    Serial3.begin(9600);

    attachInterrupt(digitalPinToInterrupt(PPS_PIN), interrupt_routine, FALLING); // PPS interrupt
    Timer2.attachInterrupt(flip_pin_handler); // Pin flip interrupt
    Timer4.attachInterrupt(flip_reset);
    Timer8.attachInterrupt(nanoClock_callback); // NanoClock callback
    nano_clock.start();
    pinMode(LED_PIN, OUTPUT);
    Serial.println("Setup complete\n\n");

    set_pps_counter();
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
    static uint32_t last_sync = 0;

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
        // Timer4.start(250000*drift_coef);
        flip_reset();
    }
}

void flip_reset() {
    setLedLow();

    // TODO: rewrite this without using Timer3 form DueTimer library
    // Timer3.start(flip_delay_adjusted);
    setup_pin_flip_timer();

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

        flip_delay_adjusted = static_cast<uint32_t> (FLIP_DELAY*drift_coef);

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



void setup_pin_flip_timer() {
    if (flip_delay_adjusted - FLIP_DELAY > DRIFT_THRESHOLD && FLIP_DELAY - flip_delay_adjusted > DRIFT_THRESHOLD) { // this works because we're using unsigned variables
        Serial.print("flip_delay_adjusted is too far from orignal value: ");
        Serial.println(flip_delay_adjusted);
        return;
    }

    Tc *tc = TC0;
    uint32_t channel = 2;
    IRQn_Type irq = TC2_IRQn;

    pmc_set_writeprotect(false);
    pmc_enable_periph_clk((uint32_t)irq);
    TC_Configure(tc, channel, TC_CMR_WAVE | TC_CMR_WAVSEL_UP_RC | TC_CMR_TCCLKS_TIMER_CLOCK1);
    uint32_t rc = flip_delay_adjusted;
    // Serial.println(rc);
    TC_SetRA(tc, channel, rc/2); //50% high, 50% low
    TC_SetRC(tc, channel, rc);

    TC_Start(tc, channel);
    tc->TC_CHANNEL[channel].TC_IER=TC_IER_CPCS;
    tc->TC_CHANNEL[channel].TC_IDR=~TC_IER_CPCS;
    NVIC_EnableIRQ(irq);

    // Serial.println("Flip timer configured!");
}

void set_pps_counter() {
    Serial.println("Beginning set_pps_counter");
    bool pps_counter_set = false;
    int position_counter = 0;
    char nmea_gprmc[] = "SGPRMC";
    bool is_gprms = false;
    char ch;

    while (true) {
        while(Serial3.available()) {
            ch = Serial3.read();
            Serial.print(ch);

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
                    Serial.print("pps_counter set to: ");
                    Serial.println(pps_counter);
                    return;
                }
            }
        }
    }
    Serial.println("Something went wrong with set_pps_counter");
}

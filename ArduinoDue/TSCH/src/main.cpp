#include <Arduino.h>
// #include <DueTimer.h>

#include <IpMtWrapper.h>
// #include <TriangleGenerator.h>
#include <dn_ipmt.h>

#include "NanoClock.h"
#include "PinFlipper.h"
#include "Drifter.h"
#include "SimpleTimer.h"

IpMtWrapper       ipmtwrapper;
// TriangleGenerator generator;

//========================== "variables" ===================================

#define TIMEn_TRIGGER        3
#define LED_PIN              13
#define SYNCHRONIZATION_RATE 10

NanoClock nano_clock       = NanoClock();
PinFlipper pin_flipper     = PinFlipper();
Drifter drifter            = Drifter();

volatile double   drift_coef = 1.0;
volatile double   local_delta;
volatile double   source_delta;
volatile uint32_t last_trigger_timerTimestamp;

uint32_t last_source_secs;
uint32_t last_source_usecs;

//===================== "functions declarations" ==============================

void time_n_trigger_handler();
void timeIndication_Cb(dn_ipmt_timeIndication_nt* timeIndication);
void calculate_new_drift(dn_ipmt_timeIndication_nt* timeIndication);
void setup_time_n_timer();
void reschedule_timer_n_timer(uint new_periode);


//=========================== "main" ==========================================

void setup() {
    pinMode(TIMEn_TRIGGER, OUTPUT);
    pinMode(LED_PIN, OUTPUT);

    ipmtwrapper.setup(
        timeIndication_Cb
    );

    Serial.println("===== Hello =====");

    nano_clock.start();
    pin_flipper.setup();

    setup_time_n_timer();

    // TODO: add timer to reset pin flip

    // Timer3.attachInterrupt(flip_pin_handler).start(FLIP_DELAY); // Pin flip interrupt
    // Timer4.attachInterrupt(time_n_trigger_handler).start(SYNCHRONIZATION_RATE*1000*1000); // Pin flip interrupt
    // Timer5.attachInterrupt(reset_flip_pin_handler); // make sure the flip high occurs at each whole second. This is activated by the TIMEn handler and deactivated by itself

    Serial.println("Main setup complete\n");
}


void loop() {


    ipmtwrapper.loop();
}

//=========================== "functions" =====================================


void timeIndication_Cb(dn_ipmt_timeIndication_nt* timeIndication) {
    uint32_t elapsed_since_trigger;
    uint32_t time_to_next_flip_reset;
    uint32_t time_to_next_time_n_trigger;
    uint32_t utcSecs;
    uint32_t now;

    calculate_new_drift(timeIndication);
    dn_read_uint32_t(&utcSecs, &timeIndication->utcSecs[4]);

    elapsed_since_trigger = static_cast<uint32_t> (nano_clock.ticksToNanos(static_cast<uint64_t> (nano_clock.getClockTicks() - last_trigger_timerTimestamp))/1000.);

    time_to_next_flip_reset = (1000000 - timeIndication->utcUsecs - elapsed_since_trigger)*drift_coef;
    pin_flipper.scheduleReset(time_to_next_flip_reset, drift_coef);

    // TODO: this line is not working well. Do something about it
    now = (utcSecs*1000*1000 + timeIndication->utcUsecs + elapsed_since_trigger)%(SYNCHRONIZATION_RATE*1000*1000);

    uint32_t OFFSET = 0;

    time_to_next_time_n_trigger = static_cast<uint32_t> ((SYNCHRONIZATION_RATE)*1000*1000 - now)*drift_coef;
    if (SYNCHRONIZATION_RATE*1000*1000 - now < OFFSET*1000*1000) {
        time_to_next_time_n_trigger += SYNCHRONIZATION_RATE*1000*1000;
    }

    reschedule_timer_n_timer(time_to_next_time_n_trigger);

    // Serial.print("   time_to_next_flip_reset: ");
    // Serial.println(time_to_next_flip_reset);
    //
    // Serial.print("   time_to_next_time_n_trigger: ");
    // Serial.println(time_to_next_time_n_trigger);
    //
    // Serial.print("     time: ");
    // Serial.print(utcSecs);
    // Serial.print(".");
    // Serial.println(timeIndication->utcUsecs);
}

void calculate_new_drift(dn_ipmt_timeIndication_nt* timeIndication) {
    static uint32_t last_sync;
    uint32_t utcSecs;
    double new_drift;

    dn_read_uint32_t(&utcSecs, &timeIndication->utcSecs[4]);

    // calculate deltas;
    local_delta = nano_clock.ticksToNanos(static_cast<uint64_t> (last_trigger_timerTimestamp - last_sync))/1000.;
    source_delta = static_cast<double> ((utcSecs - last_source_secs)*1000*1000 + timeIndication->utcUsecs - last_source_usecs);

    if (last_source_secs != 0 && last_source_usecs != 0) {
        drifter.addSyncData(local_delta, source_delta);
        new_drift = drifter.processSyncData();
        if (new_drift != 0) {
            Serial.print("New drift: ");
            Serial.println((new_drift-1)*1000000);
            drift_coef = new_drift;
        }
    }

    Serial.print("delta utcSecs: ");
    Serial.println(utcSecs-last_source_secs);
    Serial.print("delta utcSecs: ");
    Serial.print(timeIndication->utcUsecs-last_source_usecs);
    Serial.print("   ");
    Serial.println(last_source_usecs - timeIndication->utcUsecs);

    last_sync = last_trigger_timerTimestamp;
    last_source_secs = utcSecs;
    last_source_usecs = timeIndication->utcUsecs;
}

void time_n_trigger_handler() {
    // Serial.println("time_n_trigger_handler");
    // TODO: trigger this without TimerDue library
    digitalWrite(TIMEn_TRIGGER, LOW);
    delayMicroseconds(200);
    digitalWrite(TIMEn_TRIGGER, HIGH);
    last_trigger_timerTimestamp = nano_clock.getClockTicks();
}

void setup_time_n_timer() {
    SimpleTimer::setCallback(4, time_n_trigger_handler);
    SimpleTimer::configure(4, 2, 5*42*1000*1000);
    SimpleTimer::start(4);
}

void reschedule_timer_n_timer(uint new_periode_us) {
    SimpleTimer::configure(4, 2, new_periode_us*42);
    SimpleTimer::start(4);
}

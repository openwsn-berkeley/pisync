#include <Arduino.h>
#include <DueTimer.h>

#include <IpMtWrapper.h>
#include <TriangleGenerator.h>
#include <dn_ipmt.h>

IpMtWrapper       ipmtwrapper;
TriangleGenerator generator;

//========================== "variables" ===================================

#define TIMEn_TRIGGER 3
#define LED_PIN 13
#define SYNCHRONIZATION_RATE 10
#define alpha 0.3
#define beta 0.2
// #define alpha 1
// #define beta 1
#define FLIP_DELAY 500000
#define DRIFT_THRESHOLD 1000


volatile double      drift_coef = 1.0;
volatile double      ema_drift_coef = 1.0;
volatile bool        time_to_sync = false;
volatile bool        did_first_sync = false;
volatile bool        led_pin_state = false;
volatile uint32_t    local_delta;
volatile uint32_t    source_delta;
volatile uint32_t    last_trigger_timestamp;

uint32_t    last_source_secs;
uint32_t    last_source_usecs;

//===================== "functions declarations" ==============================

void                 interrupt_routine();
void                 sleep_until(uint32_t);
uint32_t             time();
void                 flip_pin_handler();
void                 time_n_trigger_handler();
void                 reset_flip_pin_handler();
void                 check_sync();
uint32_t             micros_mod();
void                 timeIndication_Cb(dn_ipmt_timeIndication_nt* timeIndication);


//=========================== "main" ==========================================

void setup() {
    pinMode(TIMEn_TRIGGER, OUTPUT);
    pinMode(LED_PIN, OUTPUT);

    ipmtwrapper.setup(
        timeIndication_Cb
    );

    Timer3.attachInterrupt(flip_pin_handler).start(FLIP_DELAY); // Pin flip interrupt
    Timer4.attachInterrupt(time_n_trigger_handler).start(SYNCHRONIZATION_RATE*1000*1000); // Pin flip interrupt
    Timer5.attachInterrupt(reset_flip_pin_handler); // make sure the flip high occurs at each whole second. This is activated by the TIMEn handler and deactivated by itself

    Serial.println("Main setup complete\n");
    // TODO: write routine to synchronize the first flip up with a whole second
}

int interval = 1000;

void loop() {
    check_sync();
    ipmtwrapper.loop();
}

//=========================== "functions" =====================================


void timeIndication_Cb(dn_ipmt_timeIndication_nt* timeIndication) {
    // TODO
    static uint32_t last_sync;
    uint32_t utcSecs;
    uint32_t next_flip_reset;

    dn_read_uint32_t(&utcSecs, &timeIndication->utcSecs[4]);

    // calculate deltas;
    local_delta = last_trigger_timestamp - last_sync;
    source_delta = (utcSecs - last_source_secs)*1000*1000 + timeIndication->utcUsecs - last_source_usecs;

    Serial.println();
    Serial.print("   Local delta: ");
    Serial.print(local_delta/1000);
    Serial.print(".");
    Serial.print(local_delta%1000);
    Serial.print("   Source delta: ");
    Serial.print(source_delta/1000);
    Serial.print(".");
    Serial.print(source_delta%1000);
    Serial.print("   Time: ");
    Serial.print(timeIndication->utcSecs[7]);
    Serial.print(".");
    Serial.print(timeIndication->utcUsecs);

    last_sync = last_trigger_timestamp;

    if (last_source_secs != 0 && last_source_usecs != 0) {
        // calculate alpha when it's not the first sync
        time_to_sync = true;
    }
    // last_source_secs = timeIndication->utcSecs[7];
    last_source_secs = utcSecs;
    last_source_usecs = timeIndication->utcUsecs;

    next_flip_reset = (1000000 - last_source_usecs) - (micros_mod() - last_trigger_timestamp);
    Serial.print("   next_flip_reset: ");
    Serial.print(next_flip_reset);
    Timer5.start(next_flip_reset);
}

void time_n_trigger_handler() {
    digitalWrite(TIMEn_TRIGGER, LOW);
    last_trigger_timestamp = micros_mod();
    delayMicroseconds(200);
    digitalWrite(TIMEn_TRIGGER, HIGH);
}

// void interrupt_routine() {
//     static uint32_t pps_counter = 0;
//
//     pps_counter++;
//     if (pps_counter % SYNCHRONIZATION_RATE == 2) {
//         Timer3.stop();
//         Timer3.start(FLIP_DELAY*drift_coef);
//
//         if (led_pin_state == true) {
//             flip_pin_handler();
//         }
//         Serial.print("New delay: ");
//         Serial.println(FLIP_DELAY*drift_coef);
//     }
// }


void flip_pin_handler() {
    static int counter = 0;
    counter++;

    led_pin_state = !led_pin_state;
    digitalWrite(LED_PIN, led_pin_state);
}


void reset_flip_pin_handler() {
    Timer3.stop();
    Timer3.start(FLIP_DELAY*drift_coef);

    if (led_pin_state == true) {
        flip_pin_handler();
    }
    Serial.print("   New delay: ");
    Serial.println(FLIP_DELAY*drift_coef);

    Timer5.stop(); // disable itself
}


void check_sync() {
    if (time_to_sync) {
        time_to_sync = false;

        double instant_drift_coef;

        instant_drift_coef = ((double) local_delta) / ((double) source_delta);

        Serial.print("  Instant drift: ");
        Serial.println((instant_drift_coef-1)*1000000);

        if (instant_drift_coef > (1.0+(DRIFT_THRESHOLD/1000000.)) || instant_drift_coef < (1.0-(DRIFT_THRESHOLD/1000000.))) {
            Serial.println("=== DRIFT too high! Ignored ===");
            return;
        }

        ema_drift_coef = ema_drift_coef*(1-alpha) + instant_drift_coef*alpha;
        drift_coef     = ema_drift_coef*(1-beta)  + instant_drift_coef*beta;
    }
}


uint32_t micros_mod() {
    uint32_t delta = -20*1000*1000;
    return micros() + delta;
}

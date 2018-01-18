#include "PinFlipper.h"

bool state = false;

void TC2_Handler()
{
    // Serial.println("TC2_Handler");
    TC_GetStatus(TC0, 2);
    PinFlipper::flip();
}

void PinFlipper::setup() {
    pinMode(LED_PIN, OUTPUT);
}

void PinFlipper::setDriftRate(double drift_rate) {
    if (drift_rate-1 > DRIFT_THRESHOLD || drift_rate-1 < -DRIFT_THRESHOLD) { // this works because we're using unsigned variables
        Serial.print("drift_rate is too far from orignal value: ");
        Serial.print((drift_rate-1)*1000000);
        Serial.println(" ppm");
        return;
    }

    // Serial.println("Beginning flip timer configuration");

    uint32_t flip_delay_adjusted = static_cast<uint32_t> (drift_rate * FLIP_DELAY);

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

void PinFlipper::reset() {
    PinFlipper::setLow();
    state = false;
}

void PinFlipper::setLow() {
    REG_PIOB_CODR = 0x1 << 27; // set pin 13 LOW
}

void PinFlipper::setHigh() {
    REG_PIOB_SODR = 0x1 << 27; // set pin 13 HIGH
}

void PinFlipper::flip() {
    // Serial.println("Flip!");
    state = !state;
    if (state) {
        PinFlipper::setHigh();
    } else {
        PinFlipper::setLow();
    }
}

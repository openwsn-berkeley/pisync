#include "NanoClock.h"

// void TC7_Handler()
// {
//     TC_GetStatus(TC2, 1);
// }

void NanoClock::start() {
    Tc *tc = TC2;
    uint32_t channel = 2;
    IRQn_Type irq = TC8_IRQn;

    pmc_set_writeprotect(false);
    pmc_enable_periph_clk((uint32_t)irq);
    TC_Configure(tc, channel, TC_CMR_WAVE | TC_CMR_WAVSEL_UP_RC | TC_CMR_TCCLKS_TIMER_CLOCK1);
    uint32_t rc = UINT32_MAX;
    Serial.println(rc);
    TC_SetRA(tc, channel, rc/2); //50% high, 50% low
    TC_SetRC(tc, channel, rc);

    TC_Start(tc, channel);
    tc->TC_CHANNEL[channel].TC_IER=TC_IER_CPCS;
    tc->TC_CHANNEL[channel].TC_IDR=~TC_IER_CPCS;
    NVIC_EnableIRQ(irq);
}


uint32_t NanoClock::getClockTicks() {
    return TC_ReadCV(TC2, 2)<<1;
}


uint32_t NanoClock::ticksToNanos(uint32_t ticks) {
    return static_cast<uint32_t> (ticks*11.904761905);
}


uint64_t NanoClock::ticksToNanos(uint64_t ticks) {
    return static_cast<uint64_t> (ticks*11.904761905);
}

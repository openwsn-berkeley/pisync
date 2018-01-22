#include <stdexcept>
#include "SimpleTimer.h"

void (*SimpleTimer::callbacks[NUM_TIMERS])() = {};

const SimpleTimer::Timer SimpleTimer::Timers[NUM_TIMERS] = {
	{TC0,0,TC0_IRQn},
	{TC0,1,TC1_IRQn},
	{TC0,2,TC2_IRQn},
	{TC1,0,TC3_IRQn},
	{TC1,1,TC4_IRQn},
	{TC1,2,TC5_IRQn},
	{TC2,0,TC6_IRQn},
	{TC2,1,TC7_IRQn},
	{TC2,2,TC8_IRQn},
};


void SimpleTimer::setCallback(int timer_number, void (*isr)()) {
	// Serial.print("Setting callback for timer ");
	// Serial.println(timer_number);
    // if (!SimpleTimer::isAvailable(timer_number)) {
    //     callbacks[timer_number] = isr;
    // } else {
    //     Serial.print("Timer ");
    //     Serial.print(timer_number);
    //     Serial.println(" is already being used");
    // }

	callbacks[timer_number] = isr;
}

void SimpleTimer::start(int timer_number) {
	Tc *tc = Timers[timer_number].tc;
    uint32_t channel = Timers[timer_number].channel;
    IRQn_Type irq = Timers[timer_number].irq;

	NVIC_ClearPendingIRQ(irq);
	NVIC_EnableIRQ(irq);

	TC_Start(tc, channel);
}

void SimpleTimer::configure(int timer_number, int clock_divider, int compare_value) {
    Tc *tc = Timers[timer_number].tc;
    uint32_t channel = Timers[timer_number].channel;
    IRQn_Type irq = Timers[timer_number].irq;

    switch(clock_divider) {
        case 2:
            clock_divider = TC_CMR_TCCLKS_TIMER_CLOCK1;
            break;
        case 8:
            clock_divider = TC_CMR_TCCLKS_TIMER_CLOCK2;
            break;
        case 32:
            clock_divider = TC_CMR_TCCLKS_TIMER_CLOCK3;
            break;
        case 128:
            clock_divider = TC_CMR_TCCLKS_TIMER_CLOCK4;
            break;
        default:
            Serial.println("Invalid clock_divider. Available options are 2, 8, 32 and 128");
            return;
    }

    pmc_set_writeprotect(false);
    pmc_enable_periph_clk((uint32_t)irq);
    TC_Configure(tc, channel, TC_CMR_WAVE | TC_CMR_WAVSEL_UP_RC | clock_divider);
    uint32_t rc = compare_value;

    // TC_SetRA(tc, channel, rc/2); //50% high, 50% low
    TC_SetRC(tc, channel, rc);

    tc->TC_CHANNEL[channel].TC_IER=TC_IER_CPCS;
    tc->TC_CHANNEL[channel].TC_IDR=~TC_IER_CPCS;
}

bool SimpleTimer::isAvailable(int timer_number) {
	return !callbacks[timer_number];
}

int SimpleTimer::getAvailable() {
	for (int i = 0; i < NUM_TIMERS; i++) {
        if (!callbacks[i]) {
            return i;
        }
    }
}

void SimpleTimer::stop(int timer_number) {
    NVIC_DisableIRQ(Timers[timer_number].irq);
	TC_Stop(Timers[timer_number].tc, Timers[timer_number].channel);
}

void SimpleTimer::clear(int timer_number) {
    SimpleTimer::stop(timer_number);
    callbacks[timer_number] = NULL;
}

void TC0_Handler(void){
	TC_GetStatus(TC0, 0);
	SimpleTimer::callbacks[0]();
}
void TC1_Handler(void){
	TC_GetStatus(TC0, 1);
	SimpleTimer::callbacks[1]();
}
void TC2_Handler(void){
	TC_GetStatus(TC0, 2);
	SimpleTimer::callbacks[2]();
}
void TC3_Handler(void){
	TC_GetStatus(TC1, 0);
	SimpleTimer::callbacks[3]();
}
void TC4_Handler(void){
	TC_GetStatus(TC1, 1);
	SimpleTimer::callbacks[4]();
}
void TC5_Handler(void){
	TC_GetStatus(TC1, 2);
	SimpleTimer::callbacks[5]();
}
void TC6_Handler(void){
	TC_GetStatus(TC2, 0);
	SimpleTimer::callbacks[6]();
}
void TC7_Handler(void){
	TC_GetStatus(TC2, 1);
	SimpleTimer::callbacks[7]();
}
void TC8_Handler(void){
	TC_GetStatus(TC2, 2);
	SimpleTimer::callbacks[8]();
}

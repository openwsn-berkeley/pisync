#include <Arduino.h>

#ifndef SimpleTimer_h
#define SimpleTimer_h

#define NUM_TIMERS 9

class SimpleTimer {
private:
    // Make Interrupt handlers friends, so they can use callbacks
    friend void TC0_Handler(void);
    friend void TC1_Handler(void);
    friend void TC2_Handler(void);
    friend void TC3_Handler(void);
    friend void TC4_Handler(void);
    friend void TC5_Handler(void);
    friend void TC6_Handler(void);
    friend void TC7_Handler(void);
    friend void TC8_Handler(void);

  static void (*callbacks[NUM_TIMERS])();

  struct Timer
  	{
  		Tc *tc;
  		uint32_t channel;
  		IRQn_Type irq;
  	};

  static const Timer Timers[NUM_TIMERS];

public:
    static void setCallback(int timer_number, void (*isr)());
    static void start(int timer_number);
    static void configure(int timer_number, int clock_divider, int compare_value);
    static bool isAvailable(int timer_number);
    static int getAvailable();
    static void stop(int timer_number);
    static void clear(int timer_number);
};



#endif

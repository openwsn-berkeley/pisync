/*
  DueTimer.h - DueTimer header file, definition of methods and attributes...
  For instructions, go to https://github.com/ivanseidel/DueTimer
  Created by Ivan Seidel Gomes, March, 2013.
  Modified by Philipp Klaus, June 2013.
  Released into the public domain.
*/

#ifdef __arm__

#ifndef PinFlipper_h
#define PinFlipper_h

#include "Arduino.h"

#define FLIP_DELAY 21*1000*1000// value in timer ticks with timer @ 32 MHz
#define DRIFT_THRESHOLD 0.001 // value in timer ticks with timer @ 32 MHz
#define LED_PIN 13

class PinFlipper
{
protected:
    static void setLow();
    static void setHigh();

public:
    static void flip();
    static void setup();
    static void setDriftRate(double drift_rate);
    static void reset();
    static void scheduleReset(uint32_t usecondsToGo);
    // uint32_t getClockTicks();
    // uint32_t ticksToNanos(uint32_t ticks);
    // uint64_t ticksToNanos(uint64_t ticks);
};

#endif

#else
	#error Oops! Trying to include PinFlipper on another device?
#endif

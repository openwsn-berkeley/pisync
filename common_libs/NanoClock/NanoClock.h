/*
  DueTimer.h - DueTimer header file, definition of methods and attributes...
  For instructions, go to https://github.com/ivanseidel/DueTimer
  Created by Ivan Seidel Gomes, March, 2013.
  Modified by Philipp Klaus, June 2013.
  Released into the public domain.
*/

#ifdef __arm__

#ifndef NanoClock_h
#define NanoClock_h

#include "Arduino.h"


class NanoClock
{
protected:

public:
    void start();
    uint32_t getClockTicks();
    uint32_t ticksToNanos(uint32_t ticks);
    uint64_t ticksToNanos(uint64_t ticks);
};

#endif

#else
	#error Oops! Trying to include DueTimer on another device?
#endif

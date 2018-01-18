/*
  DueTimer.h - DueTimer header file, definition of methods and attributes...
  For instructions, go to https://github.com/ivanseidel/DueTimer
  Created by Ivan Seidel Gomes, March, 2013.
  Modified by Philipp Klaus, June 2013.
  Released into the public domain.
*/


#ifndef Drifter_h
#define Drifter_h

#include "Arduino.h"

#define alpha 0.3
#define beta 0.2

class Drifter {
protected:
    bool time_to_sync = false;
    uint64_t last_sync = 0;
    double local_delta;
    double source_delta;

    double drift_coef = 0;
    double ema_drift_coef = 0;

public:
    void addSyncData(double local_delta, double source_delta);
    double processSyncData();
};

#endif

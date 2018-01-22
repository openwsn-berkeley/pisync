#include "Drifter.h"

void Drifter::addSyncData(double local_delta, double source_delta) {
    this->local_delta = local_delta;
    this->source_delta = source_delta;
    this->time_to_sync = true;
}


double Drifter::processSyncData() {
    if (this->time_to_sync) {
        // Serial.println("Time to sync!");

        this->time_to_sync = false;
        double instant_drift_coef;
        //
        instant_drift_coef = local_delta / source_delta;
        // if (abs(instant_drift_coef-1)*1000*1000 > 100) {
        //     return 0; // drift too big, something must have gone wrong
        // }

        if (this->drift_coef == 0) { // this is the first sync
            this->ema_drift_coef = instant_drift_coef;
            this->drift_coef     = instant_drift_coef;
        } else {
            this->ema_drift_coef = this->ema_drift_coef*(1-alpha) + instant_drift_coef*alpha;
            this->drift_coef     = this->ema_drift_coef*(1-beta)  + instant_drift_coef*beta;
        }

        // flip_delay_adjusted = static_cast<uint32_t> (FLIP_DELAY*drift_coef);

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

        return this->drift_coef;
    }
    return 0;
}

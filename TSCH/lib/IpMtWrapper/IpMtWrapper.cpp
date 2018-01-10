#include "Arduino.h"
#include "IpMtWrapper.h"
#include "dn_ipmt.h"
#include "dn_uart.h"

//=========================== prototypes ======================================

#ifdef __cplusplus
extern "C" {
    #endif

    void dn_ipmt_notif_cb(uint8_t cmdId, uint8_t subCmdId);
    void dn_ipmt_reply_cb(uint8_t cmdId);

    #ifdef __cplusplus
}
#endif

//=========================== variables =======================================

extern IpMtWrapper ipmtwrapper;

typedef struct {
    // module
    dn_uart_rxByte_cbt   ipmt_uart_rxByte_cb;
    // reply
    fsm_reply_callback   replyCb;
    uint8_t              replyBuf[MAX_FRAME_LENGTH];        // holds notifications from ipmt
    uint8_t              notifBuf[MAX_FRAME_LENGTH];        // notifications buffer internal to ipmt
    // callbacks
    time_indication_callback timeIndication_Cb;
} app_vars_t;

app_vars_t              app_vars;

//=========================== public ==========================================

/**
\brief Constructor.
*/
IpMtWrapper::IpMtWrapper() {
}

/**
\brief Setting up the instance.
*/
void IpMtWrapper::setup(
    time_indication_callback timeIndication_Cb
) {
    // reset local variables
    memset(&app_vars,    0, sizeof(app_vars));

    // store params
    app_vars.timeIndication_Cb = timeIndication_Cb;

    // initialize the serial port connected to the computer
    Serial.begin(BAUDRATE_CLI);

    // initialize the ipmt module
    dn_ipmt_init(
        dn_ipmt_notif_cb,                // notifCb
        app_vars.notifBuf,               // notifBuf
        sizeof(app_vars.notifBuf),       // notifBufLen
        dn_ipmt_reply_cb                 // replyCb
    );

    // print banner
    Serial.print("IpMtWrapper Library, version ");
    Serial.print(VER_MAJOR);
    Serial.print(".");
    Serial.print(VER_MINOR);
    Serial.print(".");
    Serial.print(VER_PATCH);
    Serial.print(".");
    Serial.print(VER_BUILD);
    Serial.println(" (c) Dust Networks, 2014.");
    Serial.println("");

    // schedule first event
    // fsm_scheduleEvent(2*CMD_PERIOD, &IpMtWrapper::api_getMoteStatus);
}

void IpMtWrapper::loop() {
    uint8_t byte;
    TIME_T  currentTime;

    // receive and react to HDLC frames
    while (Serial1.available()) {
        // read a serial byte
        byte = uint8_t(Serial1.read());

        // hand over byte to ipmt module
        app_vars.ipmt_uart_rxByte_cb(byte);
        Serial.print(".");
    }
}

//=========================== private =========================================

void IpMtWrapper::printByteArray(uint8_t* payload, uint8_t length) {
    uint8_t i;

    Serial.print(" ");
    for (i=0;i<length;i++) {
        Serial.print(payload[i]);
        if (i<length-1) {
            Serial.print("-");
        }
    }
    Serial.print("\n");
}

extern "C" void printBuf(uint8_t* buf, uint8_t bufLen) {
    uint8_t i;

    Serial.print(" ");
    for (i=0;i<bufLen;i++) {
        Serial.print(buf[i]);
        if (i<bufLen-1) {
            Serial.print("-");
        }
    }
    Serial.print("\n");
}

//=========================== callback functions for ipmt =====================

void dn_ipmt_notif_cb(uint8_t cmdId, uint8_t subCmdId) {

    dn_ipmt_events_nt* dn_ipmt_events_notif;
    dn_ipmt_timeIndication_nt* dn_ipmt_timeIndication_notif;

    switch (cmdId) {
        case CMDID_TIMEINDICATION:
        // Serial.println("");
        // Serial.println("INFO:     notif CMDID_TIMEINDICATION");

        dn_ipmt_timeIndication_notif = (dn_ipmt_timeIndication_nt*)app_vars.notifBuf;

        // Serial.print("INFO:     uptime=");
        // Serial.println(dn_ipmt_timeIndication_notif->uptime);

        app_vars.timeIndication_Cb(dn_ipmt_timeIndication_notif);

        break;
        default:
        // nothing to do
        break;
    }
}

extern "C" void dn_ipmt_reply_cb(uint8_t cmdId) {
    (ipmtwrapper.*app_vars.replyCb)();
}

//=========================== port to Arduino =================================

//===== definition of interface declared in uart.h

extern "C" void dn_uart_init(dn_uart_rxByte_cbt rxByte_cb) {
    // remember function to call back
    app_vars.ipmt_uart_rxByte_cb = rxByte_cb;

    // open the serial 1 port on the Arduino Due
    Serial1.begin(BAUDRATE_API);
}

extern "C" void dn_uart_txByte(uint8_t byte) {
    // write to the serial 1 port on the Arduino Due
    Serial1.write(byte);
}

extern "C" void dn_uart_txFlush() {
    // nothing to do since Arduino Due serial 1 driver is byte-oriented
}

//===== definition of interface declared in lock.h

extern "C" void dn_lock() {
    // this sample Arduino code is single threaded, no need to lock.
}

extern "C" void dn_unlock() {
    // this sample Arduino code is single threaded, no need to lock.
}

//===== definition of interface declared in endianness.h

extern "C" void dn_write_uint16_t(uint8_t* ptr, uint16_t val) {
    // arduino Due is a little-endian platform
    ptr[0]     = (val>>8)  & 0xff;
    ptr[1]     = (val>>0)  & 0xff;
}

extern "C" void dn_write_uint32_t(uint8_t* ptr, uint32_t val) {
    // arduino Due is a little-endian platform
    ptr[0]     = (val>>24) & 0xff;
    ptr[1]     = (val>>16) & 0xff;
    ptr[2]     = (val>>8)  & 0xff;
    ptr[3]     = (val>>0)  & 0xff;
}

extern "C" void dn_read_uint16_t(uint16_t* to, uint8_t* from) {
    // arduino Due is a little endian platform
    *to        = 0;
    *to       |= (from[1]<<0);
    *to       |= (from[0]<<8);
}
extern "C" void dn_read_uint32_t(uint32_t* to, uint8_t* from) {
    // arduino Due is a little endian platform
    *to        = 0;
    *to       |= (from[3]<<0);
    *to       |= (from[2]<<8);
    *to       |= (from[1]<<16);
    *to       |= (from[0]<<24);
}

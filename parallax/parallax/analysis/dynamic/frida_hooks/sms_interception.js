Java.perform(function() {
    var SmsManager = Java.use('android.telephony.SmsManager');
    
    function getCallerPackage() {
        try {
            var Exception = Java.use('java.lang.Exception');
            var log = Exception.$new().getStackTrace();
            for (var i = 0; i < log.length; i++) {
                var className = log[i].getClassName();
                if (className.indexOf('{package_name}') >= 0) return '{package_name}';
            }
        } catch (e) {}
        return 'unknown';
    }

    var callCount = 0;
    var lastReset = Date.now();

    try {
        SmsManager.sendTextMessage.overload(
            'java.lang.String', 'java.lang.String', 'java.lang.String', 
            'android.app.PendingIntent', 'android.app.PendingIntent'
        ).implementation = function(dest, scAddress, text, sentIntent, deliveryIntent) {
            var now = Date.now();
            if (now - lastReset > 60000) { callCount = 0; lastReset = now; }
            callCount++;
            
            var ret = null;
            var exc = null;
            try {
                ret = this.sendTextMessage(dest, scAddress, text, sentIntent, deliveryIntent);
            } catch (e) {
                exc = e.stack ? e.stack : e.toString();
            }
            
            if (callCount <= 100) {
                send({
                    "type": "observation",
                    "schema_version": "1.0",
                    "hypothesis_id": "{hypothesis_id}",
                    "hook": "android.telephony.SmsManager.sendTextMessage",
                    "captured_at_ms": now,
                    "thread_id": Process.getCurrentThreadId(),
                    "thread_name": Process.getCurrentThreadName(),
                    "caller_package": getCallerPackage(),
                    "args": { "destination": dest, "text": text },
                    "return_value": ret,
                    "exception": exc,
                    "session_id": globalThis.SESSION_ID
                });
            }
            
            if (exc !== null) throw exc;
            return ret;
        };
    } catch (e) {
        console.error("Failed to hook SmsManager.sendTextMessage: " + e);
    }
});

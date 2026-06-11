Java.perform(function() {
    var AccessibilityService = Java.use('android.accessibilityservice.AccessibilityService');
    
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
        AccessibilityService.onServiceConnected.implementation = function() {
            var now = Date.now();
            var ret = null;
            var exc = null;
            try {
                ret = this.onServiceConnected();
            } catch (e) {
                exc = e.stack ? e.stack : e.toString();
            }
            send({
                "type": "observation",
                "schema_version": "1.0",
                "hypothesis_id": "{hypothesis_id}",
                "hook": "android.accessibilityservice.AccessibilityService.onServiceConnected",
                "captured_at_ms": now,
                "thread_id": Process.getCurrentThreadId(),
                "thread_name": Process.getCurrentThreadName(),
                "caller_package": getCallerPackage(),
                "args": {},
                "return_value": ret,
                "exception": exc,
                "session_id": globalThis.SESSION_ID
            });
            if (exc !== null) throw exc;
            return ret;
        };
    } catch (e) {
        console.error("Failed to hook onServiceConnected: " + e);
    }

    try {
        AccessibilityService.onAccessibilityEvent.implementation = function(event) {
            var now = Date.now();
            if (now - lastReset > 60000) { callCount = 0; lastReset = now; }
            callCount++;
            
            var eventStr = event ? event.toString() : "null";
            var ret = null;
            var exc = null;
            try {
                ret = this.onAccessibilityEvent(event);
            } catch (e) {
                exc = e.stack ? e.stack : e.toString();
            }
            
            if (callCount <= 100) {
                send({
                    "type": "observation",
                    "schema_version": "1.0",
                    "hypothesis_id": "{hypothesis_id}",
                    "hook": "android.accessibilityservice.AccessibilityService.onAccessibilityEvent",
                    "captured_at_ms": now,
                    "thread_id": Process.getCurrentThreadId(),
                    "thread_name": Process.getCurrentThreadName(),
                    "caller_package": getCallerPackage(),
                    "args": { "event": eventStr },
                    "return_value": ret,
                    "exception": exc,
                    "session_id": globalThis.SESSION_ID
                });
            }
            if (exc !== null) throw exc;
            return ret;
        };
    } catch (e) {
        console.error("Failed to hook onAccessibilityEvent: " + e);
    }
});

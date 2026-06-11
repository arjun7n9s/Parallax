Java.perform(function() {
    var KeyCharacterMap = Java.use('android.view.KeyCharacterMap');
    
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
        KeyCharacterMap.get.overload('int', 'int').implementation = function(keyCode, metaState) {
            var now = Date.now();
            if (now - lastReset > 60000) { callCount = 0; lastReset = now; }
            callCount++;
            
            var ret = null;
            var exc = null;
            try {
                ret = this.get(keyCode, metaState);
            } catch (e) {
                exc = e.stack ? e.stack : e.toString();
            }
            
            if (callCount <= 100) {
                send({
                    "type": "observation",
                    "schema_version": "1.0",
                    "hypothesis_id": "{hypothesis_id}",
                    "hook": "android.view.KeyCharacterMap.get",
                    "captured_at_ms": now,
                    "thread_id": Process.getCurrentThreadId(),
                    "thread_name": Process.getCurrentThreadName(),
                    "caller_package": getCallerPackage(),
                    "args": { "keyCode": keyCode, "metaState": metaState },
                    "return_value": ret,
                    "exception": exc,
                    "session_id": globalThis.SESSION_ID
                });
            }
            if (exc !== null) throw exc;
            return ret;
        };
    } catch (e) {
        console.error("Failed to hook KeyCharacterMap.get: " + e);
    }

    try {
        var InputManager = Java.use('android.hardware.input.InputManager');
        InputManager.injectInputEvent.overload('android.view.InputEvent', 'int').implementation = function(event, mode) {
            var now = Date.now();
            if (now - lastReset > 60000) { callCount = 0; lastReset = now; }
            callCount++;
            
            var eventStr = event ? event.toString() : "null";
            var ret = null;
            var exc = null;
            try {
                ret = this.injectInputEvent(event, mode);
            } catch (e) {
                exc = e.stack ? e.stack : e.toString();
            }
            
            if (callCount <= 100) {
                send({
                    "type": "observation",
                    "schema_version": "1.0",
                    "hypothesis_id": "{hypothesis_id}",
                    "hook": "android.hardware.input.InputManager.injectInputEvent",
                    "captured_at_ms": now,
                    "thread_id": Process.getCurrentThreadId(),
                    "thread_name": Process.getCurrentThreadName(),
                    "caller_package": getCallerPackage(),
                    "args": { "event": eventStr, "mode": mode },
                    "return_value": ret,
                    "exception": exc,
                    "session_id": globalThis.SESSION_ID
                });
            }
            if (exc !== null) throw exc;
            return ret;
        };
    } catch (e) {
        console.error("Failed to hook InputManager.injectInputEvent: " + e);
    }
});

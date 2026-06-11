Java.perform(function() {
    var Cipher = Java.use('javax.crypto.Cipher');
    
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

    function byteToHexString(byteArray) {
        if (!byteArray) return "null";
        try {
            // Check if it is a Java byte array
            var len = byteArray.length;
            var str = "";
            for (var i = 0; i < len; i++) {
                var val = byteArray[i] & 0xFF;
                var hex = val.toString(16);
                if (hex.length == 1) hex = "0" + hex;
                str += hex;
            }
            return str;
        } catch (e) {
            return "error_hex_conversion";
        }
    }

    function cleanArg(arg) {
        if (arg === null || arg === undefined) return "null";
        try {
            if (arg.getClass) {
                var name = arg.getClass().getName();
                if (name === '[B') {
                    return byteToHexString(arg);
                }
            }
            return arg.toString();
        } catch (e) {
            return String(arg);
        }
    }

    var callCount = 0;
    var lastReset = Date.now();

    Cipher.doFinal.overloads.forEach(function(overload) {
        overload.implementation = function() {
            var now = Date.now();
            if (now - lastReset > 60000) { callCount = 0; lastReset = now; }
            callCount++;

            // Gather arguments
            var inputArgs = [];
            for (var i = 0; i < arguments.length; i++) {
                inputArgs.push(cleanArg(arguments[i]));
            }

            var ret = null;
            var exc = null;
            try {
                ret = this.doFinal.apply(this, arguments);
            } catch (e) {
                exc = e.stack ? e.stack : e.toString();
            }

            var cleanRet = cleanArg(ret);

            if (callCount <= 100) {
                send({
                    "type": "observation",
                    "schema_version": "1.0",
                    "hypothesis_id": "{hypothesis_id}",
                    "hook": "javax.crypto.Cipher.doFinal",
                    "captured_at_ms": now,
                    "thread_id": Process.getCurrentThreadId(),
                    "thread_name": Process.getCurrentThreadName(),
                    "caller_package": getCallerPackage(),
                    "args": { "inputs": inputArgs, "algorithm": this.getAlgorithm() },
                    "return_value": cleanRet,
                    "exception": exc,
                    "session_id": globalThis.SESSION_ID
                });
            }

            if (exc !== null) throw exc;
            return ret;
        };
    });
});

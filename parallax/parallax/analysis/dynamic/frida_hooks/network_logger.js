Java.perform(function() {
    var URL = Java.use('java.net.URL');
    
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

    function logConnection(urlObj, methodOverload) {
        var now = Date.now();
        if (now - lastReset > 60000) { callCount = 0; lastReset = now; }
        callCount++;
        
        var urlStr = urlObj ? urlObj.toString() : "null";
        
        if (callCount <= 100) {
            send({
                "type": "observation",
                "schema_version": "1.0",
                "hypothesis_id": "{hypothesis_id}",
                "hook": "java.net.URL.openConnection",
                "captured_at_ms": now,
                "thread_id": Process.getCurrentThreadId(),
                "thread_name": Process.getCurrentThreadName(),
                "caller_package": getCallerPackage(),
                "args": { "url": urlStr, "method": methodOverload },
                "return_value": "URLConnection",
                "exception": null,
                "session_id": globalThis.SESSION_ID
            });
        }
    }

    try {
        URL.openConnection.overload().implementation = function() {
            var conn = this.openConnection();
            logConnection(this, "overload()");
            return conn;
        };
    } catch (e) {
        console.error("Failed to hook URL.openConnection(): " + e);
    }

    try {
        URL.openConnection.overload('java.net.Proxy').implementation = function(proxy) {
            var conn = this.openConnection(proxy);
            logConnection(this, "overload(Proxy)");
            return conn;
        };
    } catch (e) {
        console.error("Failed to hook URL.openConnection(Proxy): " + e);
    }
});

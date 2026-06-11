"""
Taint source and sink definitions for FlowDroid.
Curated for Android banking malware detection.
"""

# TAINT SOURCES: Methods that produce sensitive data
# Each entry: (class_name, method_name, description)
TAINT_SOURCES = [
    # SMS content
    ("android.telephony.SmsMessage", "getMessageBody", "Read SMS body"),
    ("android.telephony.SmsMessage", "getDisplayMessageBody", "Read SMS body"),
    ("android.telephony.SmsManager", "sendTextMessage", "Send SMS"),
    # Contacts
    ("android.provider.ContactsContract", "query", "Query contacts"),
    # Location
    ("android.location.LocationManager", "getLastKnownLocation", "Read location"),
    ("android.location.Location", "getLatitude", "Read latitude"),
    ("android.location.Location", "getLongitude", "Read longitude"),
    # Device identifiers
    ("android.telephony.TelephonyManager", "getDeviceId", "IMEI/MEID"),
    ("android.telephony.TelephonyManager", "getSubscriberId", "IMSI"),
    ("android.telephony.TelephonyManager", "getLine1Number", "Phone number"),
    ("android.telephony.TelephonyManager", "getSimSerialNumber", "SIM serial"),
    ("android.telephony.TelephonyManager", "getNetworkOperator", "Network operator"),
    # Account info
    ("android.accounts.AccountManager", "getAccounts", "Read accounts"),
    ("android.accounts.AccountManager", "getAccountsByType", "Read accounts by type"),
    # Clipboard
    ("android.content.ClipboardManager", "getPrimaryClip", "Read clipboard"),
    # Camera/microphone
    ("android.hardware.Camera", "takePicture", "Capture image"),
    ("android.media.MediaRecorder", "start", "Start recording"),
]

# TAINT SINKS: Methods that exfiltrate or persist sensitive data
TAINT_SINKS = [
    # Network exfiltration
    ("java.net.URL", "openConnection", "Open HTTP connection"),
    ("java.net.HttpURLConnection", "connect", "HTTP connect"),
    ("java.net.HttpURLConnection", "getOutputStream", "HTTP output"),
    ("okhttp3.OkHttpClient", "newCall", "OkHttp request"),
    ("okhttp3.Request$Builder", "build", "OkHttp request build"),
    # File system writes
    ("java.io.FileOutputStream", "write", "File write"),
    ("java.io.FileWriter", "write", "File write"),
    ("android.content.SharedPreferences$Editor", "putString", "SharedPrefs write"),
    # IPC / broadcasts
    ("android.content.Context", "sendBroadcast", "Send broadcast"),
    ("android.content.Context", "startService", "Start service"),
    # Crypto (sometimes used to wrap stolen data before exfil)
    ("javax.crypto.Cipher", "doFinal", "Crypto operation"),
    # SMS (one of the most common exfil channels in banking trojans)
    ("android.telephony.SmsManager", "sendTextMessage", "Send SMS"),
    ("android.telephony.SmsManager", "sendMultipartTextMessage", "Send multi-part SMS"),
    ("android.telephony.SmsManager", "sendDataMessage", "Send data SMS"),
]

# Risk classification: which sink categories indicate high risk
HIGH_RISK_SINKS = {
    "android.telephony.SmsManager.sendTextMessage",
    "android.telephony.SmsManager.sendMultipartTextMessage",
    "java.net.URL.openConnection",
    "java.net.HttpURLConnection.connect",
    "okhttp3.OkHttpClient.newCall",
}

# ATT&CK Mobile technique mapping for common sink types
SINK_TO_ATTCK = {
    "android.telephony.SmsManager.sendTextMessage": "T1485.001",  # Data Destruction (SMS)
    "java.net.URL.openConnection": "T1437.001",  # Application Layer Protocol: Web Protocols
    "java.net.HttpURLConnection.connect": "T1437.001",
    "okhttp3.OkHttpClient.newCall": "T1437.001",
    "android.content.SharedPreferences$Editor.putString": "T1407",  # Download New Code at Runtime... actually T1655.001
}

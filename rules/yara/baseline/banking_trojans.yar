rule Android_BankingTrojan_Generic {
    meta:
        description = "Detects generic patterns often found in Android banking trojans (e.g. Accessibility Service abuse, Device Admin requests, overlay attacks)."
        author = "PARALLAX Curated Baseline"
        severity = "High"
        category = "Banking Trojan"
        reference = "Malpedia, CAPA"

    strings:
        // Accessibility Service Abuse
        $acc_1 = "android.accessibilityservice.AccessibilityService" ascii wide
        $acc_2 = "AccessibilityEvent" ascii wide
        $acc_3 = "getEventText" ascii wide
        $acc_4 = "performGlobalAction" ascii wide
        $acc_5 = "dispatchGesture" ascii wide
        
        // Device Admin Abuse
        $admin_1 = "android.app.action.DEVICE_ADMIN_ENABLED" ascii wide
        $admin_2 = "DeviceAdminReceiver" ascii wide
        $admin_3 = "lockNow" ascii wide
        $admin_4 = "resetPassword" ascii wide
        
        // Overlay attacks (SYSTEM_ALERT_WINDOW)
        $overlay_1 = "android.permission.SYSTEM_ALERT_WINDOW" ascii wide
        $overlay_2 = "TYPE_APPLICATION_OVERLAY" ascii wide
        $overlay_3 = "TYPE_PHONE" ascii wide
        
        // SMS Interception / Forwarding
        $sms_1 = "android.provider.Telephony.SMS_RECEIVED" ascii wide
        $sms_2 = "getDisplayMessageBody" ascii wide
        $sms_3 = "SmsMessage" ascii wide
        
        // Obfuscation / Dynamic loading (common in droppers)
        $dyn_1 = "dalvik.system.DexClassLoader" ascii wide
        $dyn_2 = "dalvik.system.PathClassLoader" ascii wide
        $dyn_3 = "loadClass" ascii wide

    condition:
        (
            2 of ($acc_*) and
            (
                1 of ($admin_*) or
                1 of ($overlay_*) or
                1 of ($sms_*) or
                1 of ($dyn_*)
            )
        )
}

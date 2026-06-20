/**
 * Mock dataset for the demo. Realistic values that mimic what the live
 * PARALLAX API would return after analyzing real Android malware samples.
 *
 * When `?demo=true` is in the URL, the app uses this data so visitors can
 * interact with the full UI without a live backend.
 */

export type Severity = "low" | "medium" | "high" | "critical";
export type Verdict = "CLEAN" | "SUSPICIOUS" | "MALICIOUS" | "CRITICAL";

export interface Submission {
  id: string;
  packageName: string;
  fileName: string;
  sizeBytes: number;
  sha256: string;
  submittedAt: string; // ISO
  submittedBy: string;
  status: "queued" | "running" | "complete" | "failed";
  verdict?: Verdict;
  riskScore: number; // 0-10
  family?: string;
  permissions: string[];
  iocs: number;
  durationMs: number;
  threatHuntHits: number;
  tags: string[];
}

export interface ThreatHuntHit {
  id: string;
  indicator: string;
  type: "ip" | "domain" | "hash" | "url" | "permission";
  matchedIn: string;
  firstSeen: string;
  severity: Severity;
  family: string;
}

export interface TAIGNodes {
  nodes: Array<{
    id: string;
    label: string;
    type: "class" | "method" | "string" | "permission" | "ioc";
    x?: number;
    y?: number;
  }>;
  edges: Array<{
    from: string;
    to: string;
    relationship: string;
  }>;
}

export interface KpiSummary {
  totalSubmissions: number;
  activeThreats: number;
  criticalRisk: number;
  avgRiskScore: number;
  totalApksScanned: number;
  familiesIdentified: number;
  iocsDiscovered: number;
  familiesTracked: number;
  newFamilies: number;
  // 7-day rolling time series for sparkline
  trend: number[];
}

const SAMPLE_PACKAGES: Array<{ pkg: string; family: string | null; verdict: Verdict; score: number; perms: string[]; tags: string[] }> = [
  { pkg: "com.sec.sharkbot", family: "SharkBot", verdict: "CRITICAL" as Verdict, score: 9.2, perms: ["RECEIVE_SMS", "READ_SMS", "SEND_SMS", "BIND_ACCESSIBILITY_SERVICE", "SYSTEM_ALERT_WINDOW", "QUERY_ALL_PACKAGES"], tags: ["dropper", "sms", "overlay"] },
  { pkg: "com.fin.cerberus", family: "Cerberus", verdict: "MALICIOUS" as Verdict, score: 8.7, perms: ["RECEIVE_SMS", "READ_CONTACTS", "ACCESS_FINE_LOCATION", "BIND_DEVICE_ADMIN", "RECORD_AUDIO"], tags: ["banker", "rat"] },
  { pkg: "com.utility.cleaner.pro", family: null, verdict: "CLEAN" as Verdict, score: 1.2, perms: ["INTERNET", "QUERY_ALL_PACKAGES"], tags: ["clean"] },
  { pkg: "com.shop.deal.finder", family: "Joker", verdict: "MALICIOUS" as Verdict, score: 7.4, perms: ["READ_SMS", "RECEIVE_BOOT_COMPLETED", "INTERNET"], tags: ["subscription-fraud", "dropper"] },
  { pkg: "com.messaging.fast.sms", family: "FluBot", verdict: "CRITICAL" as Verdict, score: 9.5, perms: ["READ_CONTACTS", "SEND_SMS", "RECEIVE_SMS", "INTERNET", "BIND_ACCESSIBILITY_SERVICE"], tags: ["sms", "worm", "overlay"] },
  { pkg: "com.app.weather.now", family: null, verdict: "CLEAN" as Verdict, score: 0.8, perms: ["INTERNET", "ACCESS_COARSE_LOCATION"], tags: ["clean"] },
  { pkg: "com.bank.secure.auth", family: "Anubis", verdict: "MALICIOUS" as Verdict, score: 8.1, perms: ["BIND_ACCESSIBILITY_SERVICE", "SYSTEM_ALERT_WINDOW", "REQUEST_INSTALL_PACKAGES"], tags: ["banker", "overlay"] },
  { pkg: "com.game.puzzle.daily", family: null, verdict: "SUSPICIOUS" as Verdict, score: 5.3, perms: ["READ_PHONE_STATE", "INTERNET"], tags: ["adware"] },
  { pkg: "com.trojan.spy.agent", family: "Pegasus", verdict: "CRITICAL" as Verdict, score: 9.8, perms: ["ACCESS_FINE_LOCATION", "RECORD_AUDIO", "CAMERA", "READ_CONTACTS"], tags: ["apt", "spyware"] },
  { pkg: "com.tool.qr.scanner", family: null, verdict: "CLEAN" as Verdict, score: 2.1, perms: ["CAMERA", "INTERNET"], tags: ["clean"] },
  { pkg: "com.free.vpn.unlimited", family: "SpyNote", verdict: "MALICIOUS" as Verdict, score: 7.9, perms: ["BIND_ACCESSIBILITY_SERVICE", "SYSTEM_ALERT_WINDOW", "INTERNET"], tags: ["rat", "dropper"] },
  { pkg: "com.media.photo.editor", family: null, verdict: "SUSPICIOUS" as Verdict, score: 4.2, perms: ["READ_EXTERNAL_STORAGE", "INTERNET"], tags: ["pua"] },
  { pkg: "com.coin.tracker.bit", family: null, verdict: "CLEAN" as Verdict, score: 1.5, perms: ["INTERNET"], tags: ["clean"] },
  { pkg: "com.android.system.update", family: "Hydra", verdict: "MALICIOUS" as Verdict, score: 8.4, perms: ["BIND_DEVICE_ADMIN", "REQUEST_INSTALL_PACKAGES", "SYSTEM_ALERT_WINDOW"], tags: ["dropper", "banker"] },
  { pkg: "com.fitness.tracker.run", family: null, verdict: "CLEAN" as Verdict, score: 0.6, perms: ["ACCESS_FINE_LOCATION", "INTERNET"], tags: ["clean"] },
  { pkg: "com.notes.simple.cloud", family: null, verdict: "CLEAN" as Verdict, score: 1.0, perms: ["INTERNET", "READ_EXTERNAL_STORAGE"], tags: ["clean"] },
  { pkg: "com.app.flashlight.bright", family: "GoldDream", verdict: "MALICIOUS" as Verdict, score: 6.8, perms: ["READ_CONTACTS", "READ_SMS", "INTERNET", "RECEIVE_BOOT_COMPLETED"], tags: ["sms", "rat"] },
  { pkg: "com.android.designer.key", family: null, verdict: "CLEAN" as Verdict, score: 0.4, perms: [], tags: ["clean"] },
  { pkg: "com.music.player.hd", family: "HeroRat", verdict: "MALICIOUS" as Verdict, score: 7.2, perms: ["BIND_ACCESSIBILITY_SERVICE", "INTERNET", "READ_CONTACTS"], tags: ["rat"] },
  { pkg: "com.ebook.reader.free", family: null, verdict: "SUSPICIOUS" as Verdict, score: 4.8, perms: ["READ_EXTERNAL_STORAGE", "INTERNET"], tags: ["adware"] },
];

function rand(seed: number): () => number {
  let s = seed;
  return () => {
    s = (s * 9301 + 49297) % 233280;
    return s / 233280;
  };
}

function pick<T>(arr: T[], r: number): T {
  return arr[Math.floor(r * arr.length)];
}

function makeHash(r: () => number): string {
  const hex = "0123456789abcdef";
  let h = "";
  for (let i = 0; i < 64; i++) h += hex[Math.floor(r() * 16)];
  return h;
}

function isoAgo(minutes: number): string {
  return new Date(Date.now() - minutes * 60 * 1000).toISOString();
}

export const submissions: Submission[] = SAMPLE_PACKAGES.map((p, i) => {
  const r = rand(i * 7919 + 13);
  const submittedMinsAgo = Math.floor(r() * 60 * 48); // last 48h
  return {
    id: `sub_${String(i + 1).padStart(4, "0")}`,
    packageName: p.pkg,
    fileName: `${p.pkg.replace(/\./g, "_")}_v${Math.floor(r() * 50) + 10}.apk`,
    sizeBytes: Math.floor(2_000_000 + r() * 38_000_000),
    sha256: makeHash(r),
    submittedAt: isoAgo(submittedMinsAgo),
    submittedBy: pick(["arjun@parallax.io", "m.kumar@parallax.io", "analyst@parallax.io", "demo@parallax.io"], r()),
    status: submittedMinsAgo < 3 ? "running" : "complete",
    verdict: p.verdict,
    riskScore: p.score,
    family: p.family ?? undefined,
    permissions: p.perms,
    iocs: Math.floor(1 + r() * 12),
    durationMs: Math.floor(8_000 + r() * 60_000),
    threatHuntHits: Math.floor(r() * 6),
    tags: p.tags,
  };
});

export const threatHuntHits: ThreatHuntHit[] = [
  { id: "h_001", indicator: "10.237.14.141:9085", type: "ip", matchedIn: "sub_0001", firstSeen: isoAgo(2), severity: "critical", family: "SharkBot" },
  { id: "h_002", indicator: "hxxp://malicious-cdn.example/rat.apk", type: "url", matchedIn: "sub_0005", firstSeen: isoAgo(8), severity: "critical", family: "FluBot" },
  { id: "h_003", indicator: "android.telephony.SmsManager.sendTextMessage", type: "permission", matchedIn: "sub_0001, sub_0005", firstSeen: isoAgo(2), severity: "high", family: "SharkBot" },
  { id: "h_004", indicator: "dalvik.system.DexClassLoader", type: "permission", matchedIn: "sub_0011, sub_0014", firstSeen: isoAgo(45), severity: "high", family: "SpyNote, Hydra" },
  { id: "h_005", indicator: "evil-payload.duckdns.org", type: "domain", matchedIn: "sub_0007", firstSeen: isoAgo(120), severity: "high", family: "Anubis" },
  { id: "h_006", indicator: "android.app.admin.DevicePolicyManager", type: "permission", matchedIn: "sub_0002, sub_0014", firstSeen: isoAgo(75), severity: "medium", family: "Cerberus, Hydra" },
  { id: "h_007", indicator: "192.168.49.1:4444", type: "ip", matchedIn: "sub_0019", firstSeen: isoAgo(220), severity: "medium", family: "HeroRat" },
  { id: "h_008", indicator: "a52d2105c8e1c2d97fbb796aa8d8a3b1c2d97fbb796aa8d8a3b1c2d97fbb796a", type: "hash", matchedIn: "sub_0001", firstSeen: isoAgo(2), severity: "critical", family: "SharkBot" },
];

export const taigGraph: TAIGNodes = {
  nodes: [
    { id: "pkg", label: "com.sec.sharkbot", type: "permission" },
    { id: "perm1", label: "RECEIVE_SMS", type: "permission" },
    { id: "perm2", label: "SEND_SMS", type: "permission" },
    { id: "perm3", label: "BIND_ACCESSIBILITY_SERVICE", type: "permission" },
    { id: "perm4", label: "SYSTEM_ALERT_WINDOW", type: "permission" },
    { id: "cls1", label: "MainActivity", type: "class" },
    { id: "cls2", label: "C2Service", type: "class" },
    { id: "cls3", label: "SmsReceiver", type: "class" },
    { id: "cls4", label: "DynamicLoader", type: "class" },
    { id: "m1", label: "sendTextMessage", type: "method" },
    { id: "m2", label: "onAccessibilityEvent", type: "method" },
    { id: "m3", label: "exec", type: "method" },
    { id: "m4", label: "loadDex", type: "method" },
    { id: "ioc1", label: "10.237.14.141:9085", type: "ioc" },
    { id: "ioc2", label: "evil-cdn.duckdns.org", type: "ioc" },
    { id: "str1", label: "/pass/v2/register", type: "string" },
    { id: "str2", label: "AES/ECB/PKCS5Padding", type: "string" },
  ],
  edges: [
    { from: "pkg", to: "perm1", relationship: "declares" },
    { from: "pkg", to: "perm2", relationship: "declares" },
    { from: "pkg", to: "perm3", relationship: "declares" },
    { from: "pkg", to: "perm4", relationship: "declares" },
    { from: "pkg", to: "cls1", relationship: "contains" },
    { from: "pkg", to: "cls2", relationship: "contains" },
    { from: "pkg", to: "cls3", relationship: "contains" },
    { from: "pkg", to: "cls4", relationship: "contains" },
    { from: "cls3", to: "m1", relationship: "calls" },
    { from: "cls1", to: "m2", relationship: "calls" },
    { from: "cls4", to: "m3", relationship: "calls" },
    { from: "cls4", to: "m4", relationship: "calls" },
    { from: "m4", to: "ioc2", relationship: "fetches" },
    { from: "cls2", to: "ioc1", relationship: "connects" },
    { from: "cls2", to: "str1", relationship: "uses" },
    { from: "cls3", to: "str2", relationship: "encrypts" },
  ],
};

export const kpiSummary: KpiSummary = {
  totalSubmissions: 1247,
  activeThreats: 18,
  criticalRisk: 4,
  avgRiskScore: 3.8,
  totalApksScanned: 8932,
  familiesIdentified: 23,
  iocsDiscovered: 312,
  familiesTracked: 23,
  newFamilies: 3,
  trend: [42, 38, 51, 47, 63, 58, 71],
};

export const recentFamilies = [
  { family: "SharkBot", count: 31, delta: 12, trend: "up" as const },
  { family: "Cerberus", count: 24, delta: -3, trend: "down" as const },
  { family: "Joker", count: 19, delta: 4, trend: "up" as const },
  { family: "Anubis", count: 17, delta: 0, trend: "flat" as const },
  { family: "FluBot", count: 14, delta: 8, trend: "up" as const },
  { family: "Pegasus", count: 6, delta: 2, trend: "up" as const },
  { family: "Hydra", count: 5, delta: -1, trend: "down" as const },
  { family: "HeroRat", count: 4, delta: 0, trend: "flat" as const },
];

export interface RecentEvent {
  time: string;
  text: string;
  kind: "danger" | "warn" | "ok" | "info";
}

export const recentEvents: RecentEvent[] = [
  { time: "2m ago", text: "New submission sub_0001 — SharkBot, CRITICAL 9.2", kind: "danger" as const },
  { time: "5m ago", text: "Threat hunt hit: 10.237.14.141:9085 in sub_0001", kind: "warn" as const },
  { time: "8m ago", text: "sub_0005 complete — FluBot family attribution", kind: "warn" as const },
  { time: "12m ago", text: "Band room: hook planner emitted 4 Frida payloads", kind: "ok" as const },
  { time: "23m ago", text: "sub_0011 — SpyNote, MALICIOUS 7.9", kind: "danger" as const },
  { time: "47m ago", text: "Cost guard: 12 analyses this hour, $1.84 total", kind: "ok" as const },
  { time: "1h ago", text: "sub_0009 — Pegasus detection, CRITICAL 9.8", kind: "danger" as const },
  { time: "2h ago", text: "Model calibration: 4 new YARA rules added", kind: "ok" as const },
];

/** Synthetic ticker text — what's streaming through the system right now. */
export const tickerItems = [
  "SHARKBOT dropper detected in com.sec.sharkbot",
  "Frida hook: SmsManager.sendTextMessage → captured 3 sends",
  "Anubis family identified via dex bytecode similarity 0.94",
  "10.237.14.141:9085 added to IOC feed",
  "Band room: 4 agents active in case room CR-2401",
  "Cost: $0.16 per analysis (target: $0.20)",
  "BIND_ACCESSIBILITY_SERVICE abuse flagged on sub_0011",
  "Webhook dispatched: S3 evidence bundle signed",
];

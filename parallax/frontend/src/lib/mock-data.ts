/**
 * Seeded demo dataset. Used when `?demo=true` (or a `demo-` key) is active, and
 * as a graceful fallback. Values mirror the shape and scale of the real
 * PARALLAX API (0-100 calibrated scores, CLEAN/LOW/MEDIUM/HIGH/CRITICAL
 * verdicts) so the demo and a live backend render through identical code paths.
 *
 * The headline sample is a real Alien banking-trojan analysis (HIGH / 65, the
 * 10.237.14.141 C2) that PARALLAX actually produced — not a fabricated number.
 */

import type { AnalysisResult, RecentEvent, Submission, TAIGNodes, ThreatHuntHit, KpiResponse } from "./api";

export type { AnalysisResult, RecentEvent, Submission, TAIGNodes, ThreatHuntHit, KpiResponse } from "./api";

interface Seed {
  pkg: string;
  family: string | null;
  verdict: Submission["verdict"];
  score: number; // 0-100
  perms: string[];
  tags: string[];
  iocs: number;
}

const SEEDS: Seed[] = [
  { pkg: "com.alien.banking.kyc", family: "Alien", verdict: "HIGH", score: 65, perms: ["RECEIVE_SMS", "READ_SMS", "BIND_ACCESSIBILITY_SERVICE", "SYSTEM_ALERT_WINDOW", "READ_CONTACTS"], tags: ["banking_trojan", "Alien"], iocs: 2 },
  { pkg: "com.sec.sharkbot", family: "SharkBot", verdict: "CRITICAL", score: 92, perms: ["RECEIVE_SMS", "SEND_SMS", "BIND_ACCESSIBILITY_SERVICE", "SYSTEM_ALERT_WINDOW", "QUERY_ALL_PACKAGES"], tags: ["dropper", "overlay"], iocs: 7 },
  { pkg: "com.utility.cleaner.pro", family: null, verdict: "CLEAN", score: 8, perms: ["INTERNET"], tags: ["clean"], iocs: 0 },
  { pkg: "com.shop.deal.finder", family: "Joker", verdict: "HIGH", score: 74, perms: ["READ_SMS", "RECEIVE_BOOT_COMPLETED", "INTERNET"], tags: ["subscription-fraud"], iocs: 4 },
  { pkg: "com.messaging.fast.sms", family: "FluBot", verdict: "CRITICAL", score: 95, perms: ["READ_CONTACTS", "SEND_SMS", "RECEIVE_SMS", "BIND_ACCESSIBILITY_SERVICE"], tags: ["sms", "worm"], iocs: 9 },
  { pkg: "com.app.weather.now", family: null, verdict: "CLEAN", score: 6, perms: ["INTERNET", "ACCESS_COARSE_LOCATION"], tags: ["clean"], iocs: 0 },
  { pkg: "com.bank.secure.auth", family: "Anubis", verdict: "HIGH", score: 78, perms: ["BIND_ACCESSIBILITY_SERVICE", "SYSTEM_ALERT_WINDOW", "REQUEST_INSTALL_PACKAGES"], tags: ["banker", "overlay"], iocs: 5 },
  { pkg: "com.game.puzzle.daily", family: null, verdict: "MEDIUM", score: 47, perms: ["READ_PHONE_STATE", "INTERNET"], tags: ["adware"], iocs: 1 },
  { pkg: "com.tool.qr.scanner", family: null, verdict: "LOW", score: 22, perms: ["CAMERA", "INTERNET"], tags: ["pua"], iocs: 0 },
  { pkg: "com.free.vpn.unlimited", family: "SpyNote", verdict: "HIGH", score: 71, perms: ["BIND_ACCESSIBILITY_SERVICE", "SYSTEM_ALERT_WINDOW", "INTERNET"], tags: ["rat", "dropper"], iocs: 6 },
  { pkg: "com.media.photo.editor", family: null, verdict: "MEDIUM", score: 42, perms: ["READ_EXTERNAL_STORAGE", "INTERNET"], tags: ["pua"], iocs: 1 },
  { pkg: "com.android.system.update", family: "Hydra", verdict: "HIGH", score: 79, perms: ["BIND_DEVICE_ADMIN", "REQUEST_INSTALL_PACKAGES", "SYSTEM_ALERT_WINDOW"], tags: ["dropper", "banker"], iocs: 5 },
  { pkg: "com.fitness.tracker.run", family: null, verdict: "CLEAN", score: 4, perms: ["ACCESS_FINE_LOCATION", "INTERNET"], tags: ["clean"], iocs: 0 },
];

function rand(seed: number): () => number {
  let s = seed;
  return () => ((s = (s * 9301 + 49297) % 233280), s / 233280);
}
function makeHash(r: () => number): string {
  let h = "";
  for (let i = 0; i < 64; i++) h += "0123456789abcdef"[Math.floor(r() * 16)];
  return h;
}
const isoAgo = (min: number) => new Date(Date.now() - min * 60_000).toISOString();

export const submissions: Submission[] = SEEDS.map((p, i) => {
  const r = rand(i * 7919 + 13);
  const minsAgo = Math.floor(r() * 60 * 48);
  return {
    id: `sub_${String(i + 1).padStart(4, "0")}`,
    packageName: p.pkg,
    fileName: `${p.pkg.replace(/\./g, "_")}.apk`,
    sizeBytes: Math.floor(1_500_000 + r() * 18_000_000),
    sha256: i === 0 ? "1f99051054b9c0a682a83939624b386e1d5e29f57454275c8639b174738f839b" : makeHash(r),
    submittedAt: isoAgo(minsAgo),
    submittedBy: "analyst@parallax.io",
    status: minsAgo < 2 ? "running" : "complete",
    stage: minsAgo < 2 ? "reasoning" : "complete",
    verdict: p.verdict,
    riskScore: p.score,
    family: p.family ?? undefined,
    permissions: p.perms,
    iocs: p.iocs,
    durationMs: Math.floor(40_000 + r() * 120_000),
    tags: p.tags,
  };
});

export function mockResult(id: string): AnalysisResult {
  const s = submissions.find((x) => x.id === id) ?? submissions[0];
  const isAlien = s.family === "Alien";
  return {
    executiveSummary: `${s.packageName} is attributed to the ${s.family ?? "an unclassified"} family with a calibrated risk of ${s.riskScore}/100 (${s.verdict}). Static analysis flagged ${s.permissions.length} permissions including accessibility and SMS abuse consistent with mobile banking fraud.`,
    technicalFindings: [
      `Requests ${s.permissions.slice(0, 3).join(", ")} — a strong device-compromise signal.`,
      "SMS receiver registered for OTP interception.",
      isAlien ? "Overlay attack vector consistent with the Alien/Cerberus lineage." : "Dynamic payload fetch observed at boot.",
      "Accessibility service abused to auto-grant and capture UI events.",
    ],
    attck: isAlien
      ? ["T1406", "T1407", "T1418", "T1429", "T1521", "T1636.003", "T1636.004"]
      : ["T1417.001", "T1582", "T1636.003", "T1516"],
    iocs: isAlien
      ? [
          { type: "url", value: "hxxp[://]10[.]237[.]14[.]141:9085/pass/v2/register" },
          { type: "ip", value: "10[.]237[.]14[.]141" },
        ]
      : [
          { type: "domain", value: "evil-payload[.]duckdns[.]org" },
          { type: "ip", value: "192[.]168[.]49[.]1" },
        ],
    recommendations: [
      { action: "Block package from the production app store", rationale: "Confirmed malicious family attribution.", mode: "HELD" },
      { action: `Add ${s.family ?? "this sample"} IOCs to the threat-hunt feed`, rationale: "Cross-sample correlation.", mode: "AUTO_LOW_RISK" },
      { action: "Notify SOC within the 4h SLA", rationale: "High-severity verdict.", mode: "SUGGEST" },
    ],
    irt: [
      { status: "CONFIRMED", claim: `Static code intent is ${s.tags[0] ?? "banking_trojan"}`, explanation: "Accessibility + SMS permission triad with overlay capability." },
      { status: "CONFIRMED", claim: `Known-malware family '${s.family ?? "?"}' confirmed by threat intel`, explanation: "Hash matched a reputable feed at high confidence." },
      { status: s.stage === "complete" && s.verdict !== "CRITICAL" ? "UNRESOLVED" : "CONFIRMED", claim: "Runtime exfiltration observed", explanation: "Static-only run; dynamic confirmation pending." },
    ],
    components: { permission_abuse: 1.0, behavioral_indicators: 0.2, code_intent_risk: 1.0, network_exfiltration: 0.0, code_obfuscation: 0.0, brand_impersonation: 0.0, campaign_association: 0.0, attribution_confidence: 0.9 },
    weights: { permission_abuse: 0.12, behavioral_indicators: 0.2, code_intent_risk: 0.18, network_exfiltration: 0.15, code_obfuscation: 0.05, brand_impersonation: 0.15, campaign_association: 0.1, attribution_confidence: 0.05 },
    evidenceScore: s.riskScore,
    calibratedScore: s.riskScore,
    confidence: { score: 0.62, band: "moderate", needsReview: s.verdict === "HIGH" || s.verdict === "CRITICAL", drivers: ["3/4 analysts produced signal", "static-only: no runtime evidence (confidence reduced)", `known-family attribution: ${s.family ?? "n/a"}`] },
    family: s.family,
    familyConfidence: s.family ? 0.9 : undefined,
    riskNotes: s.family
      ? [`Known-malware family '${s.family}' confirmed by threat intel: evidence floored to ${s.riskScore}.`, "Static-only analysis: confidence reduced."]
      : [],
    raw: {},
  };
}

export const threatHuntHits: ThreatHuntHit[] = [
  { id: "h_001", indicator: "10.237.14.141:9085", type: "ip", matchedIn: "sub_0001", firstSeen: isoAgo(2), severity: "high", family: "Alien" },
  { id: "h_002", indicator: "hxxp://malicious-cdn.example/rat.apk", type: "url", matchedIn: "sub_0005", firstSeen: isoAgo(8), severity: "critical", family: "FluBot" },
  { id: "h_003", indicator: "android.telephony.SmsManager.sendTextMessage", type: "permission", matchedIn: "sub_0001, sub_0005", firstSeen: isoAgo(2), severity: "high", family: "Alien" },
  { id: "h_004", indicator: "dalvik.system.DexClassLoader", type: "permission", matchedIn: "sub_0010, sub_0012", firstSeen: isoAgo(45), severity: "high", family: "SpyNote, Hydra" },
  { id: "h_005", indicator: "evil-payload.duckdns.org", type: "domain", matchedIn: "sub_0007", firstSeen: isoAgo(120), severity: "high", family: "Anubis" },
  { id: "h_006", indicator: "a52d2105c8e1c2d97fbb796aa8d8a3b1c2d97fbb796aa8d8a3b1c2d97fbb796a", type: "hash", matchedIn: "sub_0001", firstSeen: isoAgo(2), severity: "high", family: "Alien" },
];

export const taigGraph: TAIGNodes = {
  nodes: [
    { id: "pkg", label: "com.alien.banking.kyc", type: "class" },
    { id: "perm1", label: "BIND_ACCESSIBILITY_SERVICE", type: "permission" },
    { id: "perm2", label: "RECEIVE_SMS", type: "permission" },
    { id: "perm3", label: "SYSTEM_ALERT_WINDOW", type: "permission" },
    { id: "cls2", label: "C2Service", type: "class" },
    { id: "cls3", label: "SmsReceiver", type: "class" },
    { id: "m1", label: "sendTextMessage", type: "method" },
    { id: "m2", label: "onAccessibilityEvent", type: "method" },
    { id: "ioc1", label: "10.237.14.141:9085", type: "ioc" },
    { id: "str1", label: "/pass/v2/register", type: "string" },
  ],
  edges: [
    { from: "pkg", to: "perm1", relationship: "declares" },
    { from: "pkg", to: "perm2", relationship: "declares" },
    { from: "pkg", to: "perm3", relationship: "declares" },
    { from: "pkg", to: "cls2", relationship: "contains" },
    { from: "pkg", to: "cls3", relationship: "contains" },
    { from: "cls3", to: "m1", relationship: "calls" },
    { from: "cls2", to: "m2", relationship: "calls" },
    { from: "cls2", to: "ioc1", relationship: "connects" },
    { from: "cls2", to: "str1", relationship: "uses" },
  ],
};

export const kpiSummary: KpiResponse = {
  totalSubmissions: submissions.length,
  activeThreats: submissions.filter((s) => s.verdict === "HIGH" || s.verdict === "CRITICAL").length,
  criticalRisk: submissions.filter((s) => s.verdict === "CRITICAL").length,
  avgRiskScore: submissions.reduce((a, s) => a + s.riskScore, 0) / submissions.length,
  familiesIdentified: new Set(submissions.map((s) => s.family).filter(Boolean)).size,
  familiesTracked: new Set(submissions.map((s) => s.family).filter(Boolean)).size,
  newFamilies: 2,
  iocsDiscovered: submissions.reduce((a, s) => a + s.iocs, 0),
  trend: [3, 4, 2, 5, 4, 6, 5],
};

export const recentFamilies = [
  { family: "Alien", count: 9, delta: 4, trend: "up" as const },
  { family: "SharkBot", count: 7, delta: 2, trend: "up" as const },
  { family: "FluBot", count: 6, delta: -1, trend: "down" as const },
  { family: "Anubis", count: 5, delta: 0, trend: "flat" as const },
  { family: "Hydra", count: 4, delta: 1, trend: "up" as const },
  { family: "SpyNote", count: 3, delta: 0, trend: "flat" as const },
];

export const recentEvents: RecentEvent[] = [
  { time: "2m ago", text: "com.alien.banking.kyc — HIGH · Alien · 65/100", kind: "danger" },
  { time: "5m ago", text: "Threat hunt hit: 10.237.14.141:9085 in sub_0001", kind: "warn" },
  { time: "8m ago", text: "sub_0005 complete — FluBot family attribution", kind: "warn" },
  { time: "12m ago", text: "Band room: 8 agents converged on an action packet", kind: "ok" },
  { time: "23m ago", text: "sub_0010 — SpyNote, HIGH 71", kind: "danger" },
  { time: "47m ago", text: "Cost guard: 12 analyses this hour", kind: "ok" },
];

export const tickerItems = [
  "ALIEN banking trojan attributed in com.alien.banking.kyc",
  "Frida hook: SmsManager.sendTextMessage captured",
  "10.237.14.141:9085 added to IOC feed",
  "Band room: 8 agents converged on case CASE-FR-ALIEN-001",
  "BIND_ACCESSIBILITY_SERVICE abuse flagged",
  "Webhook dispatched: signed evidence bundle",
];

"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Calendar, Filter, Search, Activity, Pill, Stethoscope,
  FlaskConical, Hospital, AlertCircle, ChevronDown, ChevronUp,
  TrendingUp, TrendingDown, Minus, RefreshCw, X, Info,
  AlertTriangle, Zap, Clock,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const USER_ID = "demo_user_001";

// ─── Types ────────────────────────────────────────────────────────────────────

interface RelatedDetail {
  condition?: { id: string; name: string; status: string; severity?: string; body_site?: string; diagnosed_date?: string; icd10_code?: string; notes?: string };
  medication?: { id: string; name: string; dosage?: string; frequency?: string; route?: string; start_date?: string; end_date?: string; prescriber?: string; indication?: string; is_active?: boolean };
  procedure?: { id: string; procedure_name: string; performed_date?: string; provider?: string; facility?: string; body_site?: string; indication?: string; outcome?: string; cpt_code?: string };
  lab_result?: { id: string; test_name: string; value?: string; unit?: string; reference_range?: string; is_abnormal?: boolean; abnormal_flag?: string; test_date?: string; ordering_provider?: string; lab_facility?: string };
}

interface TLEvent {
  id: string;
  event_date: string;
  event_type: string;
  event_title: string;
  event_description?: string;
  importance: "high" | "medium" | "low";
  provider?: string;
  facility?: string;
  document?: { id: string; filename: string; document_type: string };
  related_detail: RelatedDetail;
}

interface Stats {
  total_events: number;
  filtered_count: number;
  recent_events_30d: number;
  by_type: Record<string, number>;
  by_importance: Record<string, number>;
  date_range: { earliest?: string; latest?: string };
}

interface HealthScore {
  total_score: number;
  grade: string;
  breakdown: Record<string, number>;
  insights: string[];
}

interface Prediction { type: string; priority: string; message: string; recommended_action: string; }
interface Alert { type: string; severity: string; message: string; recommendation: string; }
interface Insights {
  health_score: HealthScore;
  predictions: Prediction[];
  alerts: Alert[];
  disease_progression: any[];
}
interface TimelineData { events: TLEvent[]; stats: Stats; insights: Insights; }

// ─── Config ───────────────────────────────────────────────────────────────────

const TYPE_CFG: Record<string, { label: string; color: string; bg: string; Icon: any }> = {
  diagnosis:          { label: "Diagnosis",        color: "#ef4444", bg: "rgba(239,68,68,0.12)",   Icon: Stethoscope },
  medication_started: { label: "Medication Start", color: "#3b82f6", bg: "rgba(59,130,246,0.12)",  Icon: Pill },
  medication_stopped: { label: "Medication Stop",  color: "#6366f1", bg: "rgba(99,102,241,0.12)",  Icon: Pill },
  lab_result:         { label: "Lab Result",       color: "#10b981", bg: "rgba(16,185,129,0.12)",  Icon: FlaskConical },
  procedure:          { label: "Procedure",        color: "#a855f7", bg: "rgba(168,85,247,0.12)",  Icon: Activity },
  surgery:            { label: "Surgery",          color: "#f59e0b", bg: "rgba(245,158,11,0.12)",  Icon: Activity },
  visit:              { label: "Visit",            color: "#06b6d4", bg: "rgba(6,182,212,0.12)",   Icon: Hospital },
  hospitalization:    { label: "Hospitalization",  color: "#f97316", bg: "rgba(249,115,22,0.12)",  Icon: Hospital },
};

const IMP_CFG = {
  high:   { dot: "#ef4444", ring: "rgba(239,68,68,0.3)",  label: "High" },
  medium: { dot: "#f59e0b", ring: "rgba(245,158,11,0.3)", label: "Medium" },
  low:    { dot: "#10b981", ring: "rgba(16,185,129,0.3)", label: "Low" },
};

const GRADE_COLOR: Record<string, string> = { A: "#10b981", B: "#3b82f6", C: "#f59e0b", D: "#f97316", F: "#ef4444" };

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtDate(iso?: string | null) {
  if (!iso) return "\u2014";
  return new Date(iso).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
}
function getYear(iso: string) { return new Date(iso).getFullYear().toString(); }
function getMonthYear(iso: string) { return new Date(iso).toLocaleDateString("en-US", { month: "long", year: "numeric" }); }
function getMonthShort(iso: string) { return new Date(iso).toLocaleDateString("en-US", { month: "long" }); }
function typeCfg(t: string) {
  return TYPE_CFG[t] ?? { label: t.replace(/_/g, " "), color: "#94a3b8", bg: "rgba(148,163,184,0.1)", Icon: AlertCircle };
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatCard({ icon: Icon, value, label, color }: { icon: any; value: number | string; label: string; color: string }) {
  return (
    <div style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 16, padding: "18px 22px", display: "flex", alignItems: "center", gap: 14, flex: 1, minWidth: 140 }}>
      <div style={{ width: 42, height: 42, borderRadius: 12, flexShrink: 0, background: `${color}22`, border: `1px solid ${color}44`, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Icon size={19} color={color} />
      </div>
      <div>
        <div style={{ fontSize: 24, fontWeight: 700, color: "#f1f5f9", lineHeight: 1 }}>{value}</div>
        <div style={{ fontSize: 11, color: "#64748b", marginTop: 4 }}>{label}</div>
      </div>
    </div>
  );
}

function HealthRing({ score, grade }: { score: number; grade: string }) {
  const color = GRADE_COLOR[grade] ?? "#94a3b8";
  const r = 34, circ = 2 * Math.PI * r, dash = (score / 100) * circ;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
      <svg width={88} height={88} viewBox="0 0 88 88">
        <circle cx={44} cy={44} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={8} />
        <circle cx={44} cy={44} r={r} fill="none" stroke={color} strokeWidth={8}
          strokeDasharray={`${dash} ${circ - dash}`} strokeDashoffset={circ / 4}
          strokeLinecap="round" style={{ filter: `drop-shadow(0 0 6px ${color})` }} />
        <text x={44} y={40} textAnchor="middle" fill={color} fontSize={18} fontWeight={700}>{score}</text>
        <text x={44} y={58} textAnchor="middle" fill="#64748b" fontSize={12}>{grade}</text>
      </svg>
      <div>
        <div style={{ fontSize: 13, fontWeight: 600, color: "#e2e8f0" }}>Health Score</div>
        <div style={{ fontSize: 11, color: "#64748b", marginTop: 2 }}>Based on your records</div>
      </div>
    </div>
  );
}

function Chip({ text, color }: { text: string; color: string }) {
  return <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 100, background: `${color}22`, color, border: `1px solid ${color}44`, fontWeight: 500 }}>{text}</span>;
}

function EventDetail({ detail }: { detail: RelatedDetail }) {
  return (
    <div style={{ marginTop: 14, background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 10, overflow: "hidden" }}>
      {detail.condition && (
        <div style={{ padding: "10px 14px", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
          <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em", color: "#475569", marginBottom: 5 }}>Condition</div>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#e2e8f0", marginBottom: 8 }}>{detail.condition.name}</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {detail.condition.status && <Chip text={detail.condition.status} color="#ef4444" />}
            {detail.condition.severity && <Chip text={detail.condition.severity} color="#f59e0b" />}
            {detail.condition.icd10_code && <Chip text={`ICD-10: ${detail.condition.icd10_code}`} color="#64748b" />}
          </div>
          {detail.condition.notes && <div style={{ fontSize: 12, color: "#64748b", marginTop: 8 }}>{detail.condition.notes}</div>}
        </div>
      )}
      {detail.medication && (
        <div style={{ padding: "10px 14px", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
          <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em", color: "#475569", marginBottom: 5 }}>Medication</div>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#e2e8f0", marginBottom: 8 }}>{detail.medication.name}</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {detail.medication.dosage && <Chip text={detail.medication.dosage} color="#3b82f6" />}
            {detail.medication.frequency && <Chip text={detail.medication.frequency} color="#6366f1" />}
            {detail.medication.route && <Chip text={detail.medication.route} color="#64748b" />}
          </div>
          {detail.medication.indication && <div style={{ fontSize: 12, color: "#64748b", marginTop: 8 }}>For: {detail.medication.indication}</div>}
          {detail.medication.prescriber && <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>By: {detail.medication.prescriber}</div>}
        </div>
      )}
      {detail.lab_result && (
        <div style={{ padding: "10px 14px", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
          <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em", color: "#475569", marginBottom: 5 }}>Lab Result</div>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#e2e8f0", marginBottom: 8 }}>{detail.lab_result.test_name}</div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <span style={{ fontSize: 16, fontWeight: 700, color: detail.lab_result.is_abnormal ? "#ef4444" : "#10b981" }}>
              {detail.lab_result.value} {detail.lab_result.unit}
            </span>
            {detail.lab_result.reference_range && <span style={{ fontSize: 11, color: "#475569" }}>ref: {detail.lab_result.reference_range}</span>}
            {detail.lab_result.is_abnormal && <Chip text="Abnormal" color="#ef4444" />}
          </div>
          {detail.lab_result.lab_facility && <div style={{ fontSize: 12, color: "#64748b", marginTop: 8 }}>{detail.lab_result.lab_facility}</div>}
        </div>
      )}
      {detail.procedure && (
        <div style={{ padding: "10px 14px" }}>
          <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em", color: "#475569", marginBottom: 5 }}>Procedure</div>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#e2e8f0", marginBottom: 8 }}>{detail.procedure.procedure_name}</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {detail.procedure.body_site && <Chip text={detail.procedure.body_site} color="#a855f7" />}
          </div>
          {detail.procedure.outcome && <div style={{ fontSize: 12, color: "#64748b", marginTop: 8 }}>Outcome: {detail.procedure.outcome}</div>}
          {detail.procedure.facility && <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>{detail.procedure.facility}</div>}
        </div>
      )}
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export default function TimelinePage() {
  const [data, setData] = useState<TimelineData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filterType, setFilterType] = useState("");
  const [filterImportance, setFilterImportance] = useState("");
  const [filterStart, setFilterStart] = useState("");
  const [filterEnd, setFilterEnd] = useState("");
  const [search, setSearch] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [showInsights, setShowInsights] = useState(false);
  const yearRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const fetchData = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const params = new URLSearchParams();
      if (filterType) params.set("event_type", filterType);
      if (filterImportance) params.set("importance", filterImportance);
      if (filterStart) params.set("start_date", filterStart);
      if (filterEnd) params.set("end_date", filterEnd);
      params.set("limit", "200");
      const res = await fetch(`${API_BASE}/api/v1/timeline/${USER_ID}?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setData(await res.json());
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }, [filterType, filterImportance, filterStart, filterEnd]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const events = data?.events ?? [];
  const stats = data?.stats;
  const insights = data?.insights;

  const filtered = search
    ? events.filter(e =>
        e.event_title.toLowerCase().includes(search.toLowerCase()) ||
        e.event_description?.toLowerCase().includes(search.toLowerCase()) ||
        e.provider?.toLowerCase().includes(search.toLowerCase())
      )
    : events;

  const byYear: Record<string, Record<string, TLEvent[]>> = {};
  filtered.forEach(e => {
    const yr = getYear(e.event_date);
    const mo = getMonthYear(e.event_date);
    if (!byYear[yr]) byYear[yr] = {};
    if (!byYear[yr][mo]) byYear[yr][mo] = [];
    byYear[yr][mo].push(e);
  });
  const years = Object.keys(byYear).sort((a, b) => +b - +a);
  const hasFilters = !!(filterType || filterImportance || filterStart || filterEnd || search);
  const alertCount = (insights?.predictions.length ?? 0) + (insights?.alerts.length ?? 0);

  return (
    <div style={{ minHeight: "100vh", background: "linear-gradient(135deg, #0a0f1e 0%, #0d1b3e 50%, #0a1628 100%)", color: "#e2e8f0", fontFamily: "system-ui, -apple-system, sans-serif" }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg) } } select option { background: #0d1b3e; }`}</style>

      {/* Header */}
      <div style={{ padding: "26px 32px 18px", borderBottom: "1px solid rgba(255,255,255,0.06)", background: "rgba(255,255,255,0.02)", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ width: 44, height: 44, borderRadius: 12, background: "linear-gradient(135deg, rgba(59,130,246,0.3), rgba(99,102,241,0.3))", border: "1px solid rgba(99,102,241,0.4)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Calendar size={22} color="#818cf8" />
          </div>
          <div>
            <h1 style={{ fontSize: 21, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Medical Timeline</h1>
            <p style={{ fontSize: 13, color: "#475569", margin: 0 }}>Chronological history across all documents</p>
          </div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button onClick={() => setShowInsights(v => !v)} style={{ display: "flex", alignItems: "center", gap: 7, padding: "8px 16px", background: showInsights ? "rgba(99,102,241,0.25)" : "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.3)", borderRadius: 10, color: "#a5b4fc", fontSize: 13, cursor: "pointer", fontWeight: 500 }}>
            <Zap size={14} />Insights
            {alertCount > 0 && <span style={{ background: "#ef4444", color: "#fff", borderRadius: 100, fontSize: 10, fontWeight: 700, padding: "1px 5px" }}>{alertCount}</span>}
          </button>
          <button onClick={() => setShowFilters(v => !v)} style={{ display: "flex", alignItems: "center", gap: 7, padding: "8px 16px", background: showFilters ? "rgba(16,185,129,0.2)" : "rgba(255,255,255,0.05)", border: `1px solid ${showFilters ? "rgba(16,185,129,0.4)" : "rgba(255,255,255,0.1)"}`, borderRadius: 10, color: showFilters ? "#34d399" : "#94a3b8", fontSize: 13, cursor: "pointer", fontWeight: 500 }}>
            <Filter size={14} />Filter
            {hasFilters && <span style={{ background: "#10b981", color: "#fff", borderRadius: 100, fontSize: 10, fontWeight: 700, padding: "1px 5px" }}>{"filled"}</span>}
          </button>
          <button onClick={fetchData} style={{ width: 36, height: 36, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10, cursor: "pointer" }}>
            <RefreshCw size={15} color="#64748b" />
          </button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div style={{ padding: "18px 32px", display: "flex", gap: 12, flexWrap: "wrap" }}>
          <StatCard icon={Calendar} value={stats.total_events} label="Total Events" color="#3b82f6" />
          <StatCard icon={Clock} value={stats.recent_events_30d} label="Last 30 Days" color="#10b981" />
          <StatCard icon={AlertTriangle} value={stats.by_importance?.high ?? 0} label="High Importance" color="#ef4444" />
          <StatCard icon={Pill} value={stats.by_type?.medication_started ?? 0} label="Medications" color="#6366f1" />
          {insights && (
            <div style={{ flex: 1, minWidth: 200, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 16, padding: "12px 20px", display: "flex", alignItems: "center" }}>
              <HealthRing score={insights.health_score?.total_score ?? 0} grade={insights.health_score?.grade ?? "N/A"} />
            </div>
          )}
        </div>
      )}

      {/* Insights panel */}
      {showInsights && insights && (
        <div style={{ margin: "0 32px 20px", background: "rgba(99,102,241,0.06)", border: "1px solid rgba(99,102,241,0.18)", borderRadius: 16, padding: 20, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 16 }}>
          {(insights.health_score?.insights?.length ?? 0) > 0 && (
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: "#818cf8", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.08em" }}>Health Insights</div>
              {insights.health_score.insights.map((ins, i) => (
                <div key={i} style={{ fontSize: 13, color: "#cbd5e1", marginBottom: 6 }}>{"bullet"} {ins}</div>
              ))}
            </div>
          )}
          {(insights.predictions?.length ?? 0) > 0 && (
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: "#f59e0b", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.08em" }}>Upcoming / Due</div>
              {insights.predictions.map((p, i) => (
                <div key={i} style={{ fontSize: 13, color: "#fde68a", marginBottom: 8, background: "rgba(245,158,11,0.08)", borderRadius: 8, padding: "8px 10px", border: "1px solid rgba(245,158,11,0.15)" }}>
                  <div style={{ fontWeight: 600, marginBottom: 3 }}>{p.message}</div>
                  <div style={{ fontSize: 11, color: "#92400e" }}>{p.recommended_action}</div>
                </div>
              ))}
            </div>
          )}
          {(insights.alerts?.length ?? 0) > 0 && (
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: "#ef4444", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.08em" }}>Alerts</div>
              {insights.alerts.slice(0, 4).map((a, i) => (
                <div key={i} style={{ fontSize: 13, color: "#fca5a5", marginBottom: 8, background: "rgba(239,68,68,0.08)", borderRadius: 8, padding: "8px 10px", border: "1px solid rgba(239,68,68,0.15)" }}>
                  <div style={{ fontWeight: 600, marginBottom: 3 }}>{a.message}</div>
                  <div style={{ fontSize: 11, color: "#7f1d1d" }}>{a.recommendation}</div>
                </div>
              ))}
            </div>
          )}
          {(insights.disease_progression?.length ?? 0) > 0 && (
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: "#10b981", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.08em" }}>Progression Trends</div>
              {insights.disease_progression.map((d: any, i: number) => {
                const Icon = d.trend === "improving" ? TrendingDown : d.trend === "worsening" ? TrendingUp : Minus;
                const color = d.trend === "improving" ? "#10b981" : d.trend === "worsening" ? "#ef4444" : "#f59e0b";
                return (
                  <div key={i} style={{ fontSize: 13, marginBottom: 8, padding: "8px 10px", borderRadius: 8, background: `${color}11`, border: `1px solid ${color}22` }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 7 }}><Icon size={13} color={color} /><span style={{ fontWeight: 600, color }}>{d.condition}</span></div>
                    <div style={{ fontSize: 11, color: "#64748b", marginTop: 3 }}>{d.test_name}: {d.first_value} {"->"} {d.last_value}</div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Filter bar */}
      {showFilters && (
        <div style={{ margin: "0 32px 20px", background: "rgba(16,185,129,0.04)", border: "1px solid rgba(16,185,129,0.15)", borderRadius: 16, padding: 20, display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr 1fr", gap: 14, alignItems: "end" }}>
          <div>
            <label style={{ fontSize: 11, color: "#475569", display: "block", marginBottom: 6 }}>SEARCH</label>
            <div style={{ position: "relative" }}>
              <Search size={13} color="#475569" style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)" }} />
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Events, providers..." style={{ width: "100%", paddingLeft: 32, paddingRight: 10, paddingTop: 9, paddingBottom: 9, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 9, color: "#e2e8f0", fontSize: 13, boxSizing: "border-box", outline: "none" }} />
            </div>
          </div>
          <div>
            <label style={{ fontSize: 11, color: "#475569", display: "block", marginBottom: 6 }}>TYPE</label>
            <select value={filterType} onChange={e => setFilterType(e.target.value)} style={{ width: "100%", padding: "9px 10px", background: "rgba(20,30,60,0.9)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 9, color: "#e2e8f0", fontSize: 13, outline: "none" }}>
              <option value="">All Types</option>
              <option value="diagnosis">Diagnosis</option>
              <option value="medication_started">Medication Start</option>
              <option value="medication_stopped">Medication Stop</option>
              <option value="lab_result">Lab Result</option>
              <option value="procedure">Procedure</option>
              <option value="visit">Visit</option>
              <option value="hospitalization">Hospitalization</option>
            </select>
          </div>
          <div>
            <label style={{ fontSize: 11, color: "#475569", display: "block", marginBottom: 6 }}>IMPORTANCE</label>
            <select value={filterImportance} onChange={e => setFilterImportance(e.target.value)} style={{ width: "100%", padding: "9px 10px", background: "rgba(20,30,60,0.9)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 9, color: "#e2e8f0", fontSize: 13, outline: "none" }}>
              <option value="">All</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
          <div>
            <label style={{ fontSize: 11, color: "#475569", display: "block", marginBottom: 6 }}>FROM</label>
            <input type="date" value={filterStart} onChange={e => setFilterStart(e.target.value)} style={{ width: "100%", padding: "9px 10px", background: "rgba(20,30,60,0.9)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 9, color: "#e2e8f0", fontSize: 13, outline: "none", colorScheme: "dark", boxSizing: "border-box" }} />
          </div>
          <div>
            <label style={{ fontSize: 11, color: "#475569", display: "block", marginBottom: 6 }}>TO</label>
            <input type="date" value={filterEnd} onChange={e => setFilterEnd(e.target.value)} style={{ width: "100%", padding: "9px 10px", background: "rgba(20,30,60,0.9)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 9, color: "#e2e8f0", fontSize: 13, outline: "none", colorScheme: "dark", boxSizing: "border-box" }} />
          </div>
          {hasFilters && (
            <button onClick={() => { setSearch(""); setFilterType(""); setFilterImportance(""); setFilterStart(""); setFilterEnd(""); }} style={{ gridColumn: "1/-1", background: "none", border: "none", color: "#64748b", fontSize: 12, cursor: "pointer", textAlign: "left", padding: 0 }}>
              Clear all filters
            </button>
          )}
        </div>
      )}

      {/* Body */}
      <div style={{ display: "flex", padding: "0 32px 60px", gap: 28 }}>
        {years.length > 0 && (
          <div style={{ position: "sticky", top: 20, alignSelf: "flex-start", paddingTop: 4, minWidth: 52 }}>
            <div style={{ fontSize: 10, color: "#334155", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 10 }}>Year</div>
            {years.map(yr => (
              <button key={yr} onClick={() => yearRefs.current[yr]?.scrollIntoView({ behavior: "smooth", block: "start" })}
                style={{ display: "block", width: "100%", background: "none", border: "none", color: "#475569", fontSize: 13, fontWeight: 600, padding: "6px 0", cursor: "pointer", textAlign: "left" }}
                onMouseEnter={e => (e.currentTarget.style.color = "#93c5fd")}
                onMouseLeave={e => (e.currentTarget.style.color = "#475569")}>
                {yr}
              </button>
            ))}
          </div>
        )}

        <div style={{ flex: 1 }}>
          {loading && (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "80px 0", gap: 16 }}>
              <div style={{ width: 42, height: 42, borderRadius: "50%", border: "3px solid rgba(99,102,241,0.15)", borderTopColor: "#818cf8", animation: "spin 0.8s linear infinite" }} />
              <span style={{ fontSize: 14, color: "#475569" }}>Loading timeline...</span>
            </div>
          )}
          {!loading && error && (
            <div style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 16, padding: 28, textAlign: "center" }}>
              <AlertCircle size={32} color="#ef4444" style={{ margin: "0 auto 12px" }} />
              <div style={{ color: "#fca5a5", fontWeight: 600 }}>Failed to load timeline</div>
              <div style={{ color: "#64748b", fontSize: 13, marginTop: 6 }}>{error}</div>
              <button onClick={fetchData} style={{ marginTop: 16, padding: "8px 20px", background: "rgba(239,68,68,0.15)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 8, color: "#fca5a5", fontSize: 13, cursor: "pointer" }}>Retry</button>
            </div>
          )}
          {!loading && !error && filtered.length === 0 && (
            <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 16, padding: 60, textAlign: "center" }}>
              <Calendar size={40} color="#334155" style={{ margin: "0 auto 16px" }} />
              <div style={{ color: "#475569", fontWeight: 600 }}>No timeline events found</div>
              <div style={{ color: "#334155", fontSize: 13, marginTop: 6 }}>{hasFilters ? "Try removing some filters" : "Upload medical documents to build your timeline"}</div>
            </div>
          )}
          {!loading && !error && years.map(year => (
            <div key={year} ref={el => { yearRefs.current[year] = el; }} style={{ marginBottom: 36 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 22, position: "sticky", top: 0, zIndex: 10, paddingTop: 8, paddingBottom: 8, background: "linear-gradient(135deg, #0a0f1e 0%, #0d1b3e 50%, #0a1628 100%)" }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: "#818cf8", background: "rgba(99,102,241,0.12)", border: "1px solid rgba(99,102,241,0.25)", padding: "4px 14px", borderRadius: 100 }}>{year}</div>
                <div style={{ flex: 1, height: 1, background: "rgba(99,102,241,0.15)" }} />
                <div style={{ fontSize: 12, color: "#334155" }}>{Object.values(byYear[year]).flat().length} events</div>
              </div>
              {Object.entries(byYear[year]).map(([month, monthEvents]) => (
                <div key={month} style={{ marginBottom: 24 }}>
                  <div style={{ fontSize: 12, color: "#475569", marginBottom: 12, fontWeight: 600 }}>{getMonthShort(monthEvents[0].event_date)}</div>
                  <div style={{ position: "relative" }}>
                    <div style={{ position: "absolute", left: 19, top: 0, bottom: 0, width: 2, background: "rgba(255,255,255,0.05)" }} />
                    {monthEvents.map(event => {
                      const cfg = typeCfg(event.event_type);
                      const imp = IMP_CFG[event.importance] ?? IMP_CFG.low;
                      const isExpanded = expandedId === event.id;
                      const hasDetail = Object.keys(event.related_detail).length > 0;
                      return (
                        <div key={event.id} style={{ position: "relative", paddingLeft: 50, marginBottom: 14 }}>
                          <div style={{ position: "absolute", left: 9, top: 16, width: 22, height: 22, borderRadius: "50%", background: imp.dot, border: `3px solid ${imp.ring}`, boxShadow: `0 0 10px ${imp.dot}66`, display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1 }}>
                            <cfg.Icon size={10} color="#fff" />
                          </div>
                          <div onClick={() => hasDetail && setExpandedId(isExpanded ? null : event.id)}
                            style={{ background: isExpanded ? `linear-gradient(135deg, ${cfg.bg}, rgba(255,255,255,0.03))` : "rgba(255,255,255,0.03)", border: `1px solid ${isExpanded ? cfg.color + "44" : "rgba(255,255,255,0.07)"}`, borderRadius: 14, padding: "13px 16px", cursor: hasDetail ? "pointer" : "default", transition: "all 0.2s" }}
                            onMouseEnter={e => { if (!isExpanded) (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,255,255,0.13)"; }}
                            onMouseLeave={e => { if (!isExpanded) (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,255,255,0.07)"; }}>
                            <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 10 }}>
                              <div style={{ flex: 1 }}>
                                <div style={{ display: "flex", alignItems: "center", gap: 7, flexWrap: "wrap", marginBottom: 5 }}>
                                  <span style={{ fontSize: 10, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.07em", color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.color}33`, padding: "2px 8px", borderRadius: 100 }}>{cfg.label}</span>
                                  <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 100, background: `${imp.dot}22`, color: imp.dot, border: `1px solid ${imp.dot}44` }}>{imp.label}</span>
                                </div>
                                <div style={{ fontSize: 14, fontWeight: 600, color: "#f1f5f9", marginBottom: 3 }}>{event.event_title}</div>
                                <div style={{ fontSize: 12, color: "#475569" }}>
                                  {fmtDate(event.event_date)}{event.provider && ` - ${event.provider}`}{event.facility && ` - ${event.facility}`}
                                </div>
                                {event.event_description && <div style={{ fontSize: 13, color: "#94a3b8", marginTop: 7, lineHeight: 1.5 }}>{event.event_description}</div>}
                              </div>
                              {hasDetail && <div style={{ color: "#334155", flexShrink: 0, marginTop: 2 }}>{isExpanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}</div>}
                            </div>
                            {event.document && (
                              <div style={{ marginTop: 8, fontSize: 11, color: "#334155", display: "flex", alignItems: "center", gap: 5 }}>
                                <Info size={10} />{event.document.filename}
                                {event.document.document_type && <span style={{ fontSize: 10, background: "rgba(255,255,255,0.05)", borderRadius: 4, padding: "1px 6px", color: "#475569", border: "1px solid rgba(255,255,255,0.08)" }}>{event.document.document_type}</span>}
                              </div>
                            )}
                            {isExpanded && hasDetail && <EventDetail detail={event.related_detail} />}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

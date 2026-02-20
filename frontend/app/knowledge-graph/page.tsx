"use client";

import { useEffect, useState, useCallback, memo } from "react";
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  MarkerType,
  Handle,
  Position,
  NodeProps,
  Panel,
  MiniMap,
} from "reactflow";
import "reactflow/dist/style.css";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  Pill,
  Stethoscope,
  TestTube,
  X,
  Info,
  BarChart3,
  Network,
  RefreshCw,
  ExternalLink,
} from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

interface KGNode {
  id: string;
  label: string;
  type: "medication" | "condition" | "lab_result" | "procedure" | "allergy";
  properties: Record<string, any>;
  source_documents: string[];
  earliest_date: string | null;
}

interface KGEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  confidence: number;
  evidence: string;
}

interface KGStats {
  total_nodes: number;
  total_edges: number;
  node_types: Record<string, number>;
  relationship_types: Record<string, number>;
  avg_confidence: number;
  high_confidence: number;
}

interface KGData {
  nodes: KGNode[];
  edges: KGEdge[];
  statistics: KGStats;
  clusters: Record<string, string[]>;
  message?: string;
}

// ─── Design tokens ────────────────────────────────────────────────────────────

const NODE_PALETTE: Record<string, { bg: string; border: string; glow: string; dot: string }> = {
  medication:  { bg: "linear-gradient(135deg,#1e3a5f 0%,#1d4ed8 100%)", border: "#3b82f6", glow: "#3b82f680", dot: "#60a5fa" },
  condition:   { bg: "linear-gradient(135deg,#5f1e1e 0%,#dc2626 100%)", border: "#ef4444", glow: "#ef444480", dot: "#f87171" },
  lab_result:  { bg: "linear-gradient(135deg,#1e4a2e 0%,#16a34a 100%)", border: "#22c55e", glow: "#22c55e80", dot: "#4ade80" },
  procedure:   { bg: "linear-gradient(135deg,#3b1e5f 0%,#7c3aed 100%)", border: "#8b5cf6", glow: "#8b5cf680", dot: "#a78bfa" },
  allergy:     { bg: "linear-gradient(135deg,#5f3b1e 0%,#ea580c 100%)", border: "#f97316", glow: "#f9731680", dot: "#fb923c" },
};

const EDGE_COLORS: Record<string, string> = {
  treats_for:            "#3b82f6",
  prescribed_for:        "#6366f1",
  monitors:              "#22c55e",
  abnormal_indicates:    "#ef4444",
  procedure_for:         "#8b5cf6",
  contraindicated_with:  "#f59e0b",
  serial_monitoring:     "#14b8a6",
  co_occurs_with:        "#475569",
};

const REL_LABELS: Record<string, string> = {
  treats_for:            "treats",
  prescribed_for:        "prescribed for",
  monitors:              "monitors",
  abnormal_indicates:    "⚠ abnormal",
  procedure_for:         "procedure for",
  contraindicated_with:  "⛔ contra",
  serial_monitoring:     "repeated",
  co_occurs_with:        "co-occurs",
};

const NODE_TYPE_LABELS: Record<string, string> = {
  medication:  "Medications",
  condition:   "Conditions",
  lab_result:  "Lab Results",
  procedure:   "Procedures",
  allergy:     "Allergies",
};

// ─── Custom node ──────────────────────────────────────────────────────────────

const EntityNode = memo(({ data, selected }: NodeProps) => {
  const palette = NODE_PALETTE[data.type] ?? NODE_PALETTE.condition;
  const Icon =
    data.type === "medication"  ? Pill :
    data.type === "condition"   ? AlertCircle :
    data.type === "lab_result"  ? TestTube :
    data.type === "procedure"   ? Stethoscope :
    data.type === "allergy"     ? AlertTriangle : Activity;

  return (
    <div style={{
      background: palette.bg,
      border: `1.5px solid ${selected ? "#ffffff" : palette.border}`,
      boxShadow: selected
        ? `0 0 0 3px #ffffff60, 0 8px 32px ${palette.glow}`
        : `0 4px 20px ${palette.glow}, 0 2px 6px rgba(0,0,0,0.4)`,
      borderRadius: 12,
      padding: "10px 16px",
      minWidth: 140,
      maxWidth: 200,
      cursor: "pointer",
      transition: "box-shadow 0.2s, border-color 0.2s",
      userSelect: "none",
    }}>
      <Handle type="target" position={Position.Top}
        style={{ background: palette.dot, border: "2px solid #0a0f1e", width: 8, height: 8 }} />
      <Handle type="source" position={Position.Bottom}
        style={{ background: palette.dot, border: "2px solid #0a0f1e", width: 8, height: 8 }} />
      <Handle type="target" position={Position.Left}
        style={{ background: palette.dot, border: "2px solid #0a0f1e", width: 8, height: 8 }} />
      <Handle type="source" position={Position.Right}
        style={{ background: palette.dot, border: "2px solid #0a0f1e", width: 8, height: 8 }} />

      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{
          width: 28, height: 28, borderRadius: 8,
          background: "rgba(255,255,255,0.12)",
          display: "flex", alignItems: "center", justifyContent: "center",
          flexShrink: 0,
        }}>
          <Icon size={15} color="#fff" />
        </div>
        <div style={{ flex: 1, overflow: "hidden" }}>
          <div style={{ color: "#fff", fontSize: 12, fontWeight: 600, lineHeight: 1.3, wordBreak: "break-word" }}>
            {data.label}
          </div>
          {data.subtitle && (
            <div style={{ color: "rgba(255,255,255,0.6)", fontSize: 10, marginTop: 2 }}>
              {data.subtitle}
            </div>
          )}
        </div>
      </div>

      {data.badge && (
        <div style={{
          marginTop: 6,
          display: "inline-flex", alignItems: "center", gap: 4,
          background: "rgba(239,68,68,0.25)", border: "1px solid rgba(239,68,68,0.5)",
          borderRadius: 6, padding: "2px 7px", fontSize: 9.5, color: "#fca5a5", fontWeight: 600,
        }}>
          ⚠ {data.badge}
        </div>
      )}
    </div>
  );
});
EntityNode.displayName = "EntityNode";

const nodeTypes = { entity: EntityNode };

// ─── Layout ───────────────────────────────────────────────────────────────────

function layoutNodes(nodes: KGNode[]): Record<string, { x: number; y: number }> {
  const zones: Record<string, KGNode[]> = {
    condition:  nodes.filter((n) => n.type === "condition"),
    medication: nodes.filter((n) => n.type === "medication"),
    lab_result: nodes.filter((n) => n.type === "lab_result"),
    procedure:  nodes.filter((n) => n.type === "procedure"),
    allergy:    nodes.filter((n) => n.type === "allergy"),
  };
  const positions: Record<string, { x: number; y: number }> = {};

  const spreadV = (items: KGNode[], cx: number, topY: number, gap: number) =>
    items.forEach((n, i) => { positions[n.id] = { x: cx, y: topY + i * gap }; });

  const spreadH = (items: KGNode[], cy: number, leftX: number, gap: number) =>
    items.forEach((n, i) => { positions[n.id] = { x: leftX + i * gap, y: cy }; });

  // Conditions: radial cluster at centre
  const cc = zones.condition;
  if (cc.length === 1) {
    positions[cc[0].id] = { x: 560, y: 360 };
  } else {
    cc.forEach((n, i) => {
      const angle = (i / cc.length) * 2 * Math.PI - Math.PI / 2;
      const r = Math.max(90, cc.length * 32);
      positions[n.id] = { x: 560 + r * Math.cos(angle), y: 360 + r * Math.sin(angle) };
    });
  }

  const vGap = (n: number) => Math.max(80, Math.min(120, 560 / Math.max(n, 1)));
  const hGap = (n: number) => Math.max(150, Math.min(220, 800 / Math.max(n, 1)));

  spreadV(zones.medication, 120, 60,  vGap(zones.medication.length));
  spreadV(zones.lab_result, 1020, 60, vGap(zones.lab_result.length));
  spreadH(zones.procedure,  30,  200, hGap(zones.procedure.length));
  spreadH(zones.allergy,    690, 200, hGap(zones.allergy.length));

  return positions;
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function KnowledgeGraphPage() {
  const [loading, setLoading]   = useState(true);
  const [kgData, setKgData]     = useState<KGData | null>(null);
  const [error, setError]       = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<KGNode | null>(null);
  const [activeFilter, setActiveFilter] = useState("all");
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const applyFilter = useCallback((filter: string, data: KGData) => {
    const visible = new Set(
      filter === "all"
        ? data.nodes.map((n) => n.id)
        : data.nodes.filter((n) => n.type === filter).map((n) => n.id)
    );
    const positions = layoutNodes(data.nodes.filter((n) => visible.has(n.id)));

    const flowNodes: Node[] = data.nodes
      .filter((n) => visible.has(n.id))
      .map((n) => {
        const sub =
          n.type === "medication" && n.properties.dosage      ? n.properties.dosage :
          n.type === "lab_result" && n.properties.latest_value ? `${n.properties.latest_value} ${n.properties.unit ?? ""}`.trim() :
          n.type === "condition"  && n.properties.status       ? n.properties.status : "";
        return {
          id: n.id,
          type: "entity",
          data: {
            label: n.label, type: n.type, subtitle: sub,
            badge: n.type === "lab_result" && n.properties.is_abnormal ? "Abnormal" : undefined,
          },
          position: positions[n.id] ?? { x: 400, y: 300 },
        };
      });

    const flowEdges: Edge[] = data.edges
      .filter((e) => filter === "all"
        ? e.source !== e.target
        : visible.has(e.source) && visible.has(e.target) && e.source !== e.target
      )
      .map((e) => {
        const color   = EDGE_COLORS[e.type] ?? "#64748b";
        const isHigh  = e.confidence >= 0.9;
        const isDash  = ["co_occurs_with","serial_monitoring","prescribed_for"].includes(e.type);
        const isWarn  = ["contraindicated_with","abnormal_indicates"].includes(e.type);
        return {
          id: e.id,
          source: e.source,
          target: e.target,
          label: REL_LABELS[e.type] ?? e.type,
          type: "smoothstep",
          animated: isWarn || isHigh,
          markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14, color },
          style: { stroke: color, strokeWidth: isHigh ? 2.5 : 1.8, strokeDasharray: isDash ? "5 4" : undefined },
          labelStyle: { fontSize: 10, fontWeight: 600, fill: color },
          labelBgStyle: { fill: "rgba(10,15,30,0.85)", stroke: color, strokeWidth: 0.5, rx: 4, ry: 4 },
          labelBgPadding: [4, 6] as [number, number],
        };
      });

    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [setNodes, setEdges]);

  const fetchGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("http://localhost:8000/api/v1/knowledge-graph/demo_user_001");
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const data: KGData = await res.json();
      if (!data.nodes.length) {
        setError(data.message ?? "No clinical entities found. Upload and process medical documents to build your knowledge graph.");
        setLoading(false); return;
      }
      setKgData(data);
      applyFilter("all", data);
      setLoading(false);
    } catch (e: any) { setError(e.message); setLoading(false); }
  }, [applyFilter]);

  useEffect(() => { fetchGraph(); }, [fetchGraph]);

  const handleFilter = (f: string) => {
    setActiveFilter(f);
    if (kgData) applyFilter(f, kgData);
  };

  const onNodeClick = useCallback((_: any, node: Node) => {
    setSelectedNode(kgData?.nodes.find((n) => n.id === node.id) ?? null);
  }, [kgData]);

  const onPaneClick = useCallback(() => setSelectedNode(null), []);
  const stats = kgData?.statistics;

  // ── States ────────────────────────────────────────────────────────────────
  if (loading) return (
    <div className="h-screen flex items-center justify-center"
      style={{ background: "linear-gradient(135deg,#0a0f1e 0%,#0d1b3e 50%,#0a1628 100%)" }}>
      <div className="text-center space-y-4">
        <div className="relative mx-auto w-20 h-20">
          <Network className="w-20 h-20 text-blue-400 opacity-20" />
          <Activity className="w-8 h-8 text-blue-400 animate-spin absolute top-6 left-6" />
        </div>
        <p className="text-blue-200 text-lg font-medium">Building Knowledge Graph…</p>
        <p className="text-blue-400/50 text-sm">Mapping clinical relationships</p>
      </div>
    </div>
  );

  if (error) return (
    <div className="h-screen flex items-center justify-center"
      style={{ background: "linear-gradient(135deg,#0a0f1e 0%,#0d1b3e 50%,#0a1628 100%)" }}>
      <div className="text-center max-w-md px-6 space-y-6">
        <div className="w-20 h-20 rounded-full flex items-center justify-center mx-auto"
          style={{ background: "rgba(59,130,246,0.1)", border: "1px solid rgba(59,130,246,0.3)" }}>
          <Network className="w-10 h-10 text-blue-400" />
        </div>
        <h2 className="text-2xl font-bold text-white">Knowledge Graph</h2>
        <p className="text-blue-200/70 leading-relaxed">{error}</p>
        <button onClick={fetchGraph}
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-white font-medium"
          style={{ background: "linear-gradient(135deg,#1d4ed8,#7c3aed)" }}>
          <RefreshCw className="w-4 h-4" /> Retry
        </button>
      </div>
    </div>
  );

  // ── Main ──────────────────────────────────────────────────────────────────
  return (
    <div className="h-screen flex flex-col overflow-hidden"
      style={{ background: "linear-gradient(135deg,#0a0f1e 0%,#0d1b3e 50%,#0a1628 100%)" }}>

      {/* Header */}
      <div style={{
        background: "rgba(10,15,30,0.88)",
        backdropFilter: "blur(20px)",
        borderBottom: "1px solid rgba(59,130,246,0.15)",
        flexShrink: 0,
      }}>
        <div className="px-6 py-4 flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ background: "linear-gradient(135deg,#1d4ed8,#7c3aed)" }}>
              <Network className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">Clinical Knowledge Graph</h1>
              <p className="text-xs text-blue-300/60">
                {stats?.total_nodes ?? 0} entities · {stats?.total_edges ?? 0} relationships · {((stats?.avg_confidence ?? 0) * 100).toFixed(0)}% avg confidence
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {stats && (Object.entries(NODE_PALETTE) as [string, any][])
              .filter(([t]) => (stats.node_types[t] ?? 0) > 0)
              .map(([t, p]) => (
                <div key={t} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg"
                  style={{ background: "rgba(255,255,255,0.05)", border: `1px solid ${p.border}28` }}>
                  <span className="w-2 h-2 rounded-full" style={{ background: p.dot }} />
                  <span className="text-xs text-white/75 font-medium">
                    {stats.node_types[t]} {NODE_TYPE_LABELS[t]}
                  </span>
                </div>
              ))}
            <button onClick={fetchGraph}
              className="p-2 rounded-lg hover:bg-white/10 transition-colors text-blue-300 ml-1"
              title="Refresh">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Filter bar */}
        <div className="px-6 pb-3 flex items-center gap-2 flex-wrap">
          <FilterTab label="All" count={stats?.total_nodes ?? 0} dot="#60a5fa"
            active={activeFilter === "all"} onClick={() => handleFilter("all")} />
          {stats && (Object.entries(NODE_PALETTE) as [string, any][])
            .filter(([t]) => (stats.node_types[t] ?? 0) > 0)
            .map(([t, p]) => (
              <FilterTab key={t} label={NODE_TYPE_LABELS[t]} count={stats.node_types[t] ?? 0}
                dot={p.dot} active={activeFilter === t} onClick={() => handleFilter(t)} />
            ))}
        </div>
      </div>

      {/* Graph + detail panel */}
      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 relative">
          <ReactFlow
            nodes={nodes} edges={edges}
            onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick} onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            fitView fitViewOptions={{ padding: 0.18 }}
            proOptions={{ hideAttribution: true }}
            style={{ background: "transparent" }}
          >
            <Background variant={BackgroundVariant.Dots} gap={28} size={1} color="rgba(59,130,246,0.10)" />
            <Controls style={{
              background: "rgba(10,15,30,0.85)",
              border: "1px solid rgba(59,130,246,0.2)",
              borderRadius: 10, overflow: "hidden",
            }} />
            <MiniMap
              nodeColor={(n) => NODE_PALETTE[kgData?.nodes.find((k) => k.id === n.id)?.type ?? "condition"]?.dot ?? "#60a5fa"}
              style={{ background: "rgba(10,15,30,0.9)", border: "1px solid rgba(59,130,246,0.2)", borderRadius: 10 }}
              maskColor="rgba(10,15,30,0.6)"
            />
            <Panel position="top-right">
              <GraphLegend stats={stats} />
            </Panel>
          </ReactFlow>
        </div>

        {selectedNode && (
          <NodeDetailPanel node={selectedNode} onClose={() => setSelectedNode(null)} />
        )}
      </div>
    </div>
  );
}

// ─── Filter tab ───────────────────────────────────────────────────────────────

function FilterTab({ label, count, dot, active, onClick }: {
  label: string; count: number; dot: string; active: boolean; onClick: () => void;
}) {
  return (
    <button onClick={onClick} style={{
      display: "flex", alignItems: "center", gap: 6,
      padding: "5px 12px", borderRadius: 8,
      border: `1px solid ${active ? dot : "rgba(255,255,255,0.08)"}`,
      background: active ? `${dot}20` : "rgba(255,255,255,0.03)",
      color: active ? "#fff" : "rgba(255,255,255,0.5)",
      fontSize: 12, fontWeight: active ? 600 : 400, cursor: "pointer",
      transition: "all 0.15s",
    }}>
      <span className="w-2 h-2 rounded-full" style={{ background: active ? dot : "rgba(255,255,255,0.2)" }} />
      {label}
      <span style={{ marginLeft: 2, fontSize: 10, fontWeight: 700, color: active ? dot : "rgba(255,255,255,0.3)" }}>
        {count}
      </span>
    </button>
  );
}

// ─── Legend panel ─────────────────────────────────────────────────────────────

function GraphLegend({ stats }: { stats?: KGStats }) {
  const rels = stats ? Object.entries(stats.relationship_types).sort((a, b) => b[1] - a[1]) : [];
  return (
    <div style={{
      margin: 12,
      background: "rgba(10,15,30,0.92)", backdropFilter: "blur(16px)",
      border: "1px solid rgba(59,130,246,0.2)", borderRadius: 12, padding: "14px 16px",
      minWidth: 200,
    }}>
      <div className="text-xs font-bold text-blue-300/70 uppercase tracking-wider mb-2">Entity Types</div>
      <div className="space-y-1.5 mb-4">
        {(Object.entries(NODE_PALETTE) as [string, any][]).map(([t, p]) => (
          <div key={t} className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-sm flex-shrink-0" style={{ background: p.bg, border: `1px solid ${p.border}` }} />
            <span className="text-xs text-white/65">{NODE_TYPE_LABELS[t]}</span>
          </div>
        ))}
      </div>
      {rels.length > 0 && (
        <>
          <div className="text-xs font-bold text-blue-300/70 uppercase tracking-wider mb-2">Relationships</div>
          <div className="space-y-1.5">
            {rels.slice(0, 6).map(([type, count]) => (
              <div key={type} className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-0.5 rounded-full flex-shrink-0" style={{ background: EDGE_COLORS[type] ?? "#64748b" }} />
                  <span className="text-xs text-white/55">{REL_LABELS[type] ?? type}</span>
                </div>
                <span className="text-xs text-white/35">{count}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ─── Node detail panel ────────────────────────────────────────────────────────

function NodeDetailPanel({ node, onClose }: { node: KGNode; onClose: () => void }) {
  const palette = NODE_PALETTE[node.type] ?? NODE_PALETTE.condition;
  const Icon =
    node.type === "medication" ? Pill :
    node.type === "condition"  ? AlertCircle :
    node.type === "lab_result" ? TestTube :
    node.type === "procedure"  ? Stethoscope :
    node.type === "allergy"    ? AlertTriangle : Activity;

  const propRows = Object.entries(node.properties)
    .filter(([, v]) => v != null && v !== "" && v !== false)
    .map(([k, v]) => [k.replace(/_/g, " "), String(v)] as [string, string]);

  return (
    <div style={{
      width: 300, flexShrink: 0,
      background: "rgba(10,15,30,0.96)", backdropFilter: "blur(24px)",
      borderLeft: `1px solid ${palette.border}30`,
      overflowY: "auto", display: "flex", flexDirection: "column",
    }}>
      {/* Header */}
      <div style={{
        padding: "16px 18px",
        background: `linear-gradient(135deg,${palette.border}18,transparent)`,
        borderBottom: `1px solid ${palette.border}22`,
        flexShrink: 0,
      }}>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{ background: palette.bg, border: `1px solid ${palette.border}` }}>
              <Icon size={18} color="#fff" />
            </div>
            <div>
              <div className="text-sm font-bold text-white leading-snug">{node.label}</div>
              <div className="text-xs mt-0.5" style={{ color: palette.dot }}>{NODE_TYPE_LABELS[node.type]}</div>
            </div>
          </div>
          <button onClick={onClose} className="text-white/35 hover:text-white/70 transition-colors mt-0.5">
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Properties */}
      {propRows.length > 0 && (
        <div style={{ padding: "14px 18px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          <div className="text-xs font-bold text-blue-300/55 uppercase tracking-wider mb-3">Properties</div>
          <div className="space-y-2">
            {propRows.map(([k, v]) => (
              <div key={k} className="flex justify-between gap-3">
                <span className="text-xs text-white/40 capitalize flex-shrink-0">{k}</span>
                <span className="text-xs text-right font-medium"
                  style={{ color: v === "true" || v === "True" ? "#4ade80" : v === "false" || v === "False" ? "#f87171" : "rgba(255,255,255,0.75)" }}>
                  {v === "true" || v === "True" ? "Yes" : v === "false" || v === "False" ? "No" : v}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Source docs */}
      {node.source_documents.length > 0 && (
        <div style={{ padding: "14px 18px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          <div className="text-xs font-bold text-blue-300/55 uppercase tracking-wider mb-3">
            Source Documents ({node.source_documents.length})
          </div>
          <div className="space-y-1.5">
            {node.source_documents.map((id) => (
              <div key={id} className="flex items-center gap-2 text-xs text-white/45">
                <ExternalLink size={10} className="text-blue-400/50 flex-shrink-0" />
                <span className="font-mono truncate">{id.slice(0, 20)}…</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* First seen */}
      {node.earliest_date && (
        <div style={{ padding: "14px 18px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          <div className="text-xs font-bold text-blue-300/55 uppercase tracking-wider mb-2">First Recorded</div>
          <div className="text-xs text-white/65 font-medium">
            {new Date(node.earliest_date).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
          </div>
        </div>
      )}

      <div className="mt-auto" style={{
        padding: "12px 18px",
        background: "rgba(59,130,246,0.04)",
        borderTop: "1px solid rgba(59,130,246,0.08)",
      }}>
        <div className="flex items-start gap-2">
          <Info size={12} className="text-blue-400/50 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-blue-300/40 leading-relaxed">
            Deduplicated across all documents. Edges represent clinically inferred relationships.
          </p>
        </div>
      </div>
    </div>
  );
}

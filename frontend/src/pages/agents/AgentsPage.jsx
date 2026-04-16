import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  Bot, Play, ToggleLeft, ToggleRight, Clock, CheckCircle,
  XCircle, AlertCircle, ChevronDown, ChevronRight, Zap,
  Eye, Settings, MessageSquare, ArrowRight, Network, Building2
} from "lucide-react";
import { agentsApi } from "../../api/agents";
import { organizationsApi } from "../../api/organizations";
import clsx from "clsx";

// ── Agent metadata (static, keys used to look up i18n strings) ───────────────

const AGENT_META = {
  coordinator: {
    color: "indigo",
    icon: Network,
  },
  operations: {
    color: "blue",
    icon: Zap,
  },
  customer_support: {
    color: "green",
    icon: MessageSquare,
  },
  sales: {
    color: "orange",
    icon: ArrowRight,
  },
  marketing: {
    color: "pink",
    icon: Zap,
  },
  analytics: {
    color: "purple",
    icon: Eye,
  },
};

const COLOR = {
  indigo: { bg: "bg-indigo-500/15", text: "text-indigo-400", border: "border-indigo-500/30", dot: "bg-indigo-400" },
  blue:   { bg: "bg-blue-500/15",   text: "text-blue-400",   border: "border-blue-500/30",   dot: "bg-blue-400" },
  green:  { bg: "bg-green-500/15",  text: "text-green-400",  border: "border-green-500/30",  dot: "bg-green-400" },
  orange: { bg: "bg-orange-500/15", text: "text-orange-400", border: "border-orange-500/30", dot: "bg-orange-400" },
  pink:   { bg: "bg-pink-500/15",   text: "text-pink-400",   border: "border-pink-500/30",   dot: "bg-pink-400" },
  purple: { bg: "bg-purple-500/15", text: "text-purple-400", border: "border-purple-500/30", dot: "bg-purple-400" },
};

const STATUS_ICON = {
  completed:         <CheckCircle size={13} className="text-green-400" />,
  failed:            <XCircle size={13} className="text-red-400" />,
  awaiting_approval: <AlertCircle size={13} className="text-yellow-400" />,
  started:           <Clock size={13} className="text-blue-400 animate-pulse" />,
};

// ── Sub-components ────────────────────────────────────────────────────────────

function AutonomyBar({ value }) {
  const { t } = useTranslation();
  const pct = Math.round((value || 0) * 100);
  const color = pct >= 70 ? "bg-green-500" : pct >= 40 ? "bg-yellow-500" : "bg-red-400";
  return (
    <div>
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>{t("agents.autonomy")}</span>
        <span className={pct >= 70 ? "text-green-400" : pct >= 40 ? "text-yellow-400" : "text-red-400"}>
          {pct}%
        </span>
      </div>
      <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div className={clsx("h-full rounded-full transition-all", color)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function SystemPromptModal({ config, onClose }) {
  const { t } = useTranslation();
  const [prompt, setPrompt] = useState(config.system_prompt || "");
  const [custom, setCustom] = useState(config.custom_instructions || "");
  const qc = useQueryClient();

  const saveMutation = useMutation({
    mutationFn: () => agentsApi.updateConfig(config.id, { system_prompt: prompt, custom_instructions: custom }),
    onSuccess: () => { qc.invalidateQueries(["agent-configs"]); onClose(); },
  });

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-2xl space-y-4 max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-white flex items-center gap-2">
            <Settings size={16} className="text-gray-400" />
            {config.agent_type_display} — {t("agents.systemPrompt")}
          </h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300">✕</button>
        </div>

        <div className="flex-1 overflow-y-auto space-y-4">
          <div>
            <label className="label">{t("agents.systemPrompt")}</label>
            <p className="text-xs text-gray-500 mb-2">{t("agents.systemPromptHint")}</p>
            <textarea
              className="input resize-none font-mono text-xs"
              rows={14}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder={t("agents.systemPromptPlaceholder")}
            />
          </div>
          <div>
            <label className="label">{t("agents.customInstructions")}</label>
            <p className="text-xs text-gray-500 mb-2">{t("agents.customInstructionsHint")}</p>
            <textarea
              className="input resize-none text-sm"
              rows={4}
              value={custom}
              onChange={(e) => setCustom(e.target.value)}
              placeholder={t("agents.customInstructionsPlaceholder")}
            />
          </div>
        </div>

        <div className="flex gap-2 pt-2 border-t border-gray-800">
          <button className="btn-primary" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
            {saveMutation.isPending ? t("agents.saving") : t("common.save")}
          </button>
          <button className="btn-secondary" onClick={onClose}>{t("common.cancel")}</button>
        </div>
      </div>
    </div>
  );
}

function DeptModal({ config, onClose }) {
  const { t } = useTranslation();
  const qc = useQueryClient();

  const { data: allDepts = [] } = useQuery({
    queryKey: ["departments"],
    queryFn: () => organizationsApi.list().then((r) => r.data.results ?? r.data),
  });

  const [selected, setSelected] = useState(
    () => new Set((config.department_ids || []).map(String))
  );
  const [monitorChats, setMonitorChats] = useState(config.monitor_chats ?? false);

  const saveMutation = useMutation({
    mutationFn: () =>
      agentsApi.updateConfig(config.id, {
        departments: Array.from(selected),
        monitor_chats: monitorChats,
      }),
    onSuccess: () => {
      qc.invalidateQueries(["agent-configs"]);
      onClose();
    },
  });

  const toggle = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-md space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-white flex items-center gap-2">
            <Building2 size={16} className="text-gray-400" />
            {config.agent_type_display} — {t("agents.assignDepartments")}
          </h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300">✕</button>
        </div>

        {/* monitor_chats toggle */}
        <label className="flex items-center justify-between gap-3 cursor-pointer py-2 border-b border-gray-800">
          <div>
            <p className="text-sm text-gray-200">{t("agents.monitorChats")}</p>
            <p className="text-xs text-gray-500">{t("agents.monitorChatsHint")}</p>
          </div>
          <button
            type="button"
            onClick={() => setMonitorChats((v) => !v)}
            className="text-gray-400 hover:text-gray-200 transition-colors"
          >
            {monitorChats
              ? <ToggleRight size={26} className="text-brand-400" />
              : <ToggleLeft size={26} />}
          </button>
        </label>

        {/* department list */}
        <div>
          <p className="text-xs text-gray-500 mb-2">
            {selected.size === 0 ? t("agents.deptAll") : `${selected.size} ${t("agents.departments").toLowerCase()}`}
          </p>
          <div className="max-h-52 overflow-y-auto space-y-1 pr-1">
            {allDepts.length === 0 && (
              <p className="text-xs text-gray-500">{t("agents.deptNone")}</p>
            )}
            {allDepts.map((dept) => {
              const checked = selected.has(String(dept.id));
              return (
                <label key={dept.id} className="flex items-center gap-2 cursor-pointer py-1.5 px-2 rounded-lg hover:bg-gray-800 transition-colors">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggle(String(dept.id))}
                    className="accent-brand-500 w-4 h-4 flex-shrink-0"
                  />
                  <span className="text-sm text-gray-200">{dept.name}</span>
                  {dept.head_name && (
                    <span className="text-xs text-gray-500 ml-auto">{dept.head_name}</span>
                  )}
                </label>
              );
            })}
          </div>
        </div>

        <div className="flex gap-2 pt-2 border-t border-gray-800">
          <button
            className="btn-primary"
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending}
          >
            {saveMutation.isPending ? t("agents.savingDepts") : t("common.save")}
          </button>
          <button className="btn-secondary" onClick={onClose}>{t("common.cancel")}</button>
        </div>
      </div>
    </div>
  );
}

function AgentCard({ config, onTrigger, isTriggering }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const [showPromptEditor, setShowPromptEditor] = useState(false);
  const [showDeptModal, setShowDeptModal] = useState(false);
  const qc = useQueryClient();
  const meta = AGENT_META[config.agent_type] || {};
  const colors = COLOR[meta.color] || COLOR.blue;
  const Icon = meta.icon || Bot;
  const isRoot = !config.parent_agent;

  const toggleMutation = useMutation({
    mutationFn: () => agentsApi.updateConfig(config.id, { is_enabled: !config.is_enabled }),
    onSuccess: () => qc.invalidateQueries(["agent-configs"]),
  });

  return (
    <>
      <div className={clsx(
        "card border transition-all",
        config.is_enabled ? colors.border : "border-gray-800 opacity-60",
        isRoot && "ring-1 ring-indigo-500/20"
      )}>
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className={clsx("w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0", colors.bg)}>
              <Icon size={18} className={colors.text} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <p className="font-semibold text-white text-sm">{config.agent_type_display}</p>
                {isRoot && (
                  <span className="badge bg-indigo-500/20 text-indigo-400 text-[10px]">{t("agents.root")}</span>
                )}
              </div>
              {config.parent_agent_display && (
                <p className="text-xs text-gray-500 flex items-center gap-1">
                  {t("agents.reportsTo")} <span className="text-gray-400">{config.parent_agent_display}</span>
                </p>
              )}
            </div>
          </div>
          <button
            onClick={() => toggleMutation.mutate()}
            disabled={toggleMutation.isPending}
            className="text-gray-500 hover:text-gray-300 transition-colors flex-shrink-0"
            title={config.is_enabled ? "Disable agent" : "Enable agent"}
          >
            {config.is_enabled
              ? <ToggleRight size={24} className={colors.text} />
              : <ToggleLeft size={24} />
            }
          </button>
        </div>

        {/* Description */}
        <p className="text-xs text-gray-400 mb-4 leading-relaxed">{t(`agents.descriptions.${config.agent_type}`)}</p>

        {/* Autonomy bar */}
        <div className="mb-4">
          <AutonomyBar value={config.autonomy_level} />
        </div>

        {/* Children */}
        {config.child_agents?.length > 0 && (
          <div className="mb-4">
            <p className="text-xs text-gray-500 mb-1.5">{t("agents.delegatesTo")}:</p>
            <div className="flex flex-wrap gap-1.5">
              {config.child_agents.map((child) => {
                const cm = AGENT_META[child.agent_type];
                const cc = COLOR[cm?.color] || COLOR.blue;
                return (
                  <span key={child.id} className={clsx("badge border text-[10px]", cc.bg, cc.text, cc.border)}>
                    {child.label}
                  </span>
                );
              })}
            </div>
          </div>
        )}

        {/* Expandable capabilities */}
        <button
          onClick={() => setExpanded((e) => !e)}
          className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 mb-3 transition-colors"
        >
          {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          {t("agents.capabilities")}
        </button>
        {expanded && (
          <ul className="mb-4 space-y-1">
            {(t(`agents.capabilities.${config.agent_type}`, { returnObjects: true }) || []).map((cap) => (
              <li key={cap} className="text-xs text-gray-400 flex items-center gap-2">
                <span className={clsx("w-1.5 h-1.5 rounded-full flex-shrink-0", colors.dot)} />
                {cap}
              </li>
            ))}
          </ul>
        )}

        {/* Department badges */}
        <div className="mb-3">
          <div className="flex items-center gap-1.5 flex-wrap">
            <Building2 size={11} className="text-gray-500 flex-shrink-0" />
            {config.department_names?.length > 0 ? (
              config.department_names.map((n) => (
                <span key={n} className="badge bg-gray-800 text-gray-400 text-[10px]">{n}</span>
              ))
            ) : (
              <span className="text-[11px] text-gray-600">{t("agents.deptAll")}</span>
            )}
            {config.monitor_chats && (
              <span className="badge bg-blue-500/15 text-blue-400 text-[10px] border border-blue-500/25 ml-auto">
                <MessageSquare size={9} className="inline mr-0.5" />
                {t("agents.monitorChats")}
              </span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <button
            className={clsx(
              "flex-1 flex items-center justify-center gap-1.5 text-xs py-2 rounded-lg font-medium transition-colors",
              config.is_enabled
                ? `${colors.bg} ${colors.text} hover:opacity-80`
                : "bg-gray-800 text-gray-500 cursor-not-allowed"
            )}
            onClick={() => onTrigger(config.id)}
            disabled={!config.is_enabled || isTriggering}
          >
            <Play size={12} />
            {t("agents.runNow")}
          </button>
          <button
            className="px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-gray-200 rounded-lg text-xs transition-colors"
            onClick={() => setShowDeptModal(true)}
            title={t("agents.assignDepartments")}
          >
            <Building2 size={13} />
          </button>
          <button
            className="px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-gray-200 rounded-lg text-xs transition-colors"
            onClick={() => setShowPromptEditor(true)}
            title="Edit system prompt"
          >
            <Settings size={13} />
          </button>
        </div>
      </div>

      {showDeptModal && (
        <DeptModal config={config} onClose={() => setShowDeptModal(false)} />
      )}
      {showPromptEditor && (
        <SystemPromptModal config={config} onClose={() => setShowPromptEditor(false)} />
      )}
    </>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function AgentsPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState("fleet");
  const [triggeringId, setTriggeringId] = useState(null);

  const { data: configs = [], isLoading } = useQuery({
    queryKey: ["agent-configs"],
    queryFn: () => agentsApi.configs().then((r) => r.data.results ?? r.data),
  });

  const { data: logs = [] } = useQuery({
    queryKey: ["agent-logs"],
    queryFn: () => agentsApi.logs({ page_size: 30 }).then((r) => r.data.results ?? r.data),
    refetchInterval: 10_000,
  });

  const triggerMutation = useMutation({
    mutationFn: (id) => agentsApi.triggerAgent(id, {}),
    onMutate: (id) => setTriggeringId(id),
    onSettled: () => { setTriggeringId(null); qc.invalidateQueries(["agent-logs"]); },
  });

  // Separate coordinator (root) from domain agents
  const rootAgent = configs.find((c) => c.agent_type === "coordinator");
  const domainAgents = configs.filter((c) => c.agent_type !== "coordinator");
  const enabledCount = configs.filter((c) => c.is_enabled).length;

  return (
    <div className="p-4 sm:p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-lg sm:text-xl font-bold text-white">{t("agents.title")}</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            {t("agents.activeCount", { enabled: enabledCount, total: configs.length })}
          </p>
        </div>
        <div className="flex gap-2">
          {[
            { key: "fleet",     label: t("agents.fleet") },
            { key: "hierarchy", label: t("agents.hierarchy") },
            { key: "logs",      label: t("agents.logs") },
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={clsx(
                "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                activeTab === key
                  ? "bg-brand-500/20 text-brand-400"
                  : "text-gray-400 hover:text-gray-200"
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Fleet tab */}
      {activeTab === "fleet" && (
        <div className="space-y-5">
          {/* Coordinator — full width */}
          {isLoading ? (
            <div className="card animate-pulse h-48 bg-gray-800" />
          ) : rootAgent ? (
            <div className="max-w-sm">
              <AgentCard
                config={rootAgent}
                onTrigger={(id) => triggerMutation.mutate(id)}
                isTriggering={triggeringId === rootAgent.id}
              />
            </div>
          ) : null}

          {/* Domain agents grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {isLoading
              ? Array(5).fill(null).map((_, i) => (
                  <div key={i} className="card animate-pulse h-64 bg-gray-800" />
                ))
              : domainAgents.map((config) => (
                  <AgentCard
                    key={config.id}
                    config={config}
                    onTrigger={(id) => triggerMutation.mutate(id)}
                    isTriggering={triggeringId === config.id}
                  />
                ))}
          </div>
        </div>
      )}

      {/* Hierarchy tab */}
      {activeTab === "hierarchy" && (
        <div className="card">
          <h2 className="font-semibold text-white mb-6">{t("agents.hierarchy")}</h2>
          {rootAgent && (
            <div className="flex flex-col items-center">
              {/* Root node */}
              <HierarchyNode config={rootAgent} isRoot />
              {/* Connector line */}
              {domainAgents.length > 0 && (
                <>
                  <div className="w-px h-8 bg-gray-700" />
                  {/* Horizontal bar */}
                  <div className="relative flex items-start justify-center gap-0">
                    <div
                      className="absolute top-0 h-px bg-gray-700"
                      style={{ width: `${Math.max(domainAgents.length - 1, 1) * 180}px` }}
                    />
                    <div className="flex gap-0">
                      {domainAgents.map((agent, i) => (
                        <div key={agent.id} className="flex flex-col items-center w-44">
                          <div className="w-px h-8 bg-gray-700" />
                          <HierarchyNode config={agent} />
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>
          )}
          <p className="text-xs text-gray-600 text-center mt-8">
            {t("agents.hierarchyNote")}
          </p>
        </div>
      )}

      {/* Logs tab */}
      {activeTab === "logs" && (
        <div className="card">
          <h2 className="font-semibold text-white mb-4">{t("agents.logs")}</h2>
          {logs.length === 0 ? (
            <p className="text-sm text-gray-500">{t("agents.noLogs")}</p>
          ) : (
            <div className="space-y-0 divide-y divide-gray-800">
              {logs.map((log) => {
                const meta = AGENT_META[log.agent_type];
                const colors = COLOR[meta?.color] || COLOR.blue;
                return (
                  <div key={log.id} className="py-3 flex items-start gap-4">
                    <div className="flex-shrink-0 mt-0.5">
                      {STATUS_ICON[log.status] || <Clock size={13} className="text-gray-500" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={clsx("text-xs font-medium", colors.text)}>
                          {log.agent_type_display}
                        </span>
                        <span className="text-xs text-gray-600">·</span>
                        <span className="text-xs text-gray-500">
                          {t(`agents.triggerSources.${log.trigger_source}`, { defaultValue: log.trigger_source?.replace(/_/g, " ") })}
                        </span>
                      </div>
                      <p className="text-sm text-gray-300 truncate mt-0.5">{log.task_description}</p>
                      {log.parsed_output?.summary && (
                        <p className="text-xs text-gray-500 mt-1 truncate">{log.parsed_output.summary}</p>
                      )}
                    </div>
                    <div className="text-right text-xs text-gray-500 flex-shrink-0 space-y-0.5">
                      <p>{log.total_tokens > 0 ? `${log.total_tokens} ${t("agents.tokens")}` : "—"}</p>
                      {log.confidence_score && (
                        <p>{Math.round(log.confidence_score * 100)}% {t("agents.conf")}</p>
                      )}
                      <p className="text-gray-600">{new Date(log.started_at).toLocaleTimeString()}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function HierarchyNode({ config, isRoot }) {
  const { t } = useTranslation();
  const meta = AGENT_META[config.agent_type] || {};
  const colors = COLOR[meta.color] || COLOR.blue;
  const Icon = meta.icon || Bot;

  return (
    <div className={clsx(
      "border rounded-xl px-4 py-3 text-center w-40",
      colors.border, colors.bg,
      isRoot && "ring-1 ring-indigo-500/40"
    )}>
      <div className={clsx("w-8 h-8 rounded-lg flex items-center justify-center mx-auto mb-2", colors.bg)}>
        <Icon size={16} className={colors.text} />
      </div>
      <p className={clsx("text-xs font-semibold", colors.text)}>
        {config.agent_type_display?.replace(" Agent", "")}
      </p>
      <p className="text-[10px] text-gray-500 mt-0.5">
        {config.is_enabled ? t("common.active") : t("common.disabled")}
      </p>
    </div>
  );
}

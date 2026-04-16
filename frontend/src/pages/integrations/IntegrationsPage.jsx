import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  Plus, Zap, RefreshCw, Activity, ChevronDown, ChevronRight,
  CheckCircle, XCircle, Clock, Wifi, WifiOff, Trash2, Settings,
} from "lucide-react";
import { integrationsApi } from "../../api/integrations";
import clsx from "clsx";

const TYPE_COLORS = {
  bitrix24: "blue",
  amocrm:   "purple",
  odoo:     "green",
  "1c":     "orange",
  generic:  "gray",
};
const COLOR = {
  blue:   { bg: "bg-blue-500/15",   text: "text-blue-400",   border: "border-blue-500/30" },
  purple: { bg: "bg-purple-500/15", text: "text-purple-400", border: "border-purple-500/30" },
  green:  { bg: "bg-green-500/15",  text: "text-green-400",  border: "border-green-500/30" },
  orange: { bg: "bg-orange-500/15", text: "text-orange-400", border: "border-orange-500/30" },
  gray:   { bg: "bg-gray-700/40",   text: "text-gray-400",   border: "border-gray-700" },
};

const TYPES    = ["bitrix24", "amocrm", "odoo", "1c", "generic"];
const DIRECTIONS = ["inbound", "outbound", "bidirectional"];

// ── Create / Edit Modal ───────────────────────────────────────────────────────

function IntegrationModal({ existing, onClose }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState({
    name:           existing?.name           ?? "",
    type:           existing?.type           ?? "bitrix24",
    api_url:        existing?.api_url        ?? "",
    api_key:        existing?.api_key        ?? "",
    sync_direction: existing?.sync_direction ?? "bidirectional",
    is_active:      existing?.is_active      ?? true,
  });

  const f = (k) => (v) => setForm((p) => ({ ...p, [k]: typeof v === "object" ? v.target.value : v }));

  const saveMutation = useMutation({
    mutationFn: () =>
      existing
        ? integrationsApi.update(existing.id, form)
        : integrationsApi.create(form),
    onSuccess: () => {
      qc.invalidateQueries(["integrations"]);
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-lg space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-white flex items-center gap-2">
            <Zap size={16} className="text-brand-400" />
            {existing ? existing.name : t("integrations.newIntegration")}
          </h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300">✕</button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="label">{t("integrations.name")}</label>
            <input className="input" value={form.name} onChange={f("name")} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">{t("integrations.type")}</label>
              <select className="input" value={form.type} onChange={f("type")}>
                {TYPES.map((tp) => (
                  <option key={tp} value={tp}>{t(`integrations.types.${tp}`)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">{t("integrations.syncDirection")}</label>
              <select className="input" value={form.sync_direction} onChange={f("sync_direction")}>
                {DIRECTIONS.map((d) => (
                  <option key={d} value={d}>{t(`integrations.direction.${d}`)}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="label">{t("integrations.apiUrl")}</label>
            <input className="input" value={form.api_url} onChange={f("api_url")} placeholder="https://your-crm.example.com" />
          </div>
          <div>
            <label className="label">{t("integrations.apiKey")}</label>
            <input className="input" type="password" value={form.api_key} onChange={f("api_key")} placeholder="••••••••" />
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => setForm((p) => ({ ...p, is_active: e.target.checked }))}
              className="accent-brand-500"
            />
            <span className="text-sm text-gray-300">{t("integrations.active")}</span>
          </label>
        </div>

        <div className="flex gap-2 pt-2 border-t border-gray-800">
          <button
            className="btn-primary"
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending || !form.name}
          >
            {saveMutation.isPending ? "..." : t("common.save")}
          </button>
          <button className="btn-secondary" onClick={onClose}>{t("common.cancel")}</button>
        </div>
      </div>
    </div>
  );
}

// ── Logs Modal ────────────────────────────────────────────────────────────────

function LogsModal({ integration, onClose }) {
  const { t } = useTranslation();
  const { data: logs = [], isLoading } = useQuery({
    queryKey: ["integration-logs", integration.id],
    queryFn: () => integrationsApi.logs(integration.id).then((r) => r.data.results ?? r.data),
  });

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-2xl max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-white">
            {integration.name} — {t("integrations.logs")}
          </h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300">✕</button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="space-y-2">
              {Array(4).fill(null).map((_, i) => (
                <div key={i} className="h-10 bg-gray-800 rounded animate-pulse" />
              ))}
            </div>
          ) : logs.length === 0 ? (
            <p className="text-sm text-gray-500">{t("integrations.noLogs")}</p>
          ) : (
            <div className="divide-y divide-gray-800">
              {logs.map((log) => (
                <div key={log.id} className="py-3 flex items-start gap-3">
                  <div className="mt-0.5">
                    {log.result === "success"
                      ? <CheckCircle size={13} className="text-green-400" />
                      : log.result === "error"
                      ? <XCircle size={13} className="text-red-400" />
                      : <Clock size={13} className="text-yellow-400" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 text-xs">
                      <span className={clsx(
                        "badge text-[10px]",
                        log.direction === "inbound" ? "bg-blue-500/15 text-blue-400" : "bg-green-500/15 text-green-400"
                      )}>
                        {log.direction}
                      </span>
                      <span className="text-gray-500">{log.records_in ?? 0}↓ / {log.records_out ?? 0}↑</span>
                    </div>
                    {log.error && <p className="text-xs text-red-400 mt-0.5 truncate">{log.error}</p>}
                  </div>
                  <p className="text-xs text-gray-600 flex-shrink-0">
                    {new Date(log.created_at).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="pt-3 border-t border-gray-800">
          <button className="btn-secondary text-sm" onClick={onClose}>{t("common.close")}</button>
        </div>
      </div>
    </div>
  );
}

// ── Integration Card ──────────────────────────────────────────────────────────

function IntegrationCard({ item }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [showLogs, setShowLogs] = useState(false);
  const [testMsg, setTestMsg] = useState(null);
  const [syncMsg, setSyncMsg] = useState(null);

  const colors = COLOR[TYPE_COLORS[item.type] ?? "gray"];

  const deleteMutation = useMutation({
    mutationFn: () => integrationsApi.delete(item.id),
    onSuccess: () => qc.invalidateQueries(["integrations"]),
  });

  const testMutation = useMutation({
    mutationFn: () => integrationsApi.testConnection(item.id),
    onSuccess: () => setTestMsg({ ok: true, text: t("integrations.testOk") }),
    onError: () => setTestMsg({ ok: false, text: t("integrations.testFail") }),
    onSettled: () => setTimeout(() => setTestMsg(null), 3000),
  });

  const syncMutation = useMutation({
    mutationFn: () => integrationsApi.manualSync(item.id),
    onSuccess: () => { setSyncMsg({ ok: true, text: t("integrations.syncOk") }); qc.invalidateQueries(["integrations"]); },
    onError: () => setSyncMsg({ ok: false, text: t("integrations.syncFail") }),
    onSettled: () => setTimeout(() => setSyncMsg(null), 3000),
  });

  const lastSync = item.last_sync_at
    ? new Date(item.last_sync_at).toLocaleString()
    : t("integrations.never");

  return (
    <>
      <div className={clsx("card border transition-all", item.is_active ? colors.border : "border-gray-800 opacity-60")}>
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className={clsx("w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0", colors.bg)}>
              <Zap size={16} className={colors.text} />
            </div>
            <div>
              <p className="font-semibold text-white text-sm">{item.name}</p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className={clsx("badge text-[10px] border", colors.bg, colors.text, colors.border)}>
                  {t(`integrations.types.${item.type}`)}
                </span>
                <span className="badge bg-gray-800 text-gray-400 text-[10px]">
                  {t(`integrations.direction.${item.sync_direction}`)
                    .split("(")[0].trim()}
                </span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            {item.is_active
              ? <Wifi size={13} className="text-green-400" />
              : <WifiOff size={13} className="text-gray-600" />}
          </div>
        </div>

        {/* Last sync */}
        <p className="text-xs text-gray-500 mb-3">
          {t("integrations.lastSync")}: <span className="text-gray-400">{lastSync}</span>
          {item.sync_count > 0 && (
            <span className="ml-2 text-gray-600">· {item.sync_count}×</span>
          )}
        </p>

        {/* Error banner */}
        {item.last_error && (
          <div className="mb-3 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/25">
            <p className="text-xs text-red-400 truncate">{item.last_error}</p>
          </div>
        )}

        {/* Status message */}
        {(testMsg || syncMsg) && (
          <div className={clsx(
            "mb-3 px-3 py-1.5 rounded-lg text-xs",
            (testMsg || syncMsg).ok ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400"
          )}>
            {(testMsg || syncMsg).text}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2 flex-wrap">
          <button
            className="flex items-center gap-1 text-xs px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg transition-colors"
            onClick={() => testMutation.mutate()}
            disabled={testMutation.isPending}
          >
            <Activity size={11} />
            {testMutation.isPending ? t("integrations.testing") : t("integrations.testConnection")}
          </button>
          <button
            className="flex items-center gap-1 text-xs px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg transition-colors"
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending || !item.is_active}
          >
            <RefreshCw size={11} className={syncMutation.isPending ? "animate-spin" : ""} />
            {syncMutation.isPending ? t("integrations.syncing") : t("integrations.manualSync")}
          </button>
          <button
            className="flex items-center gap-1 text-xs px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg transition-colors"
            onClick={() => setShowLogs(true)}
          >
            <Clock size={11} />
            {t("integrations.viewLogs")}
          </button>
          <button
            className="ml-auto px-2.5 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-gray-200 rounded-lg transition-colors"
            onClick={() => setShowEdit(true)}
          >
            <Settings size={12} />
          </button>
          <button
            className="px-2.5 py-1.5 bg-gray-800 hover:bg-red-500/20 text-gray-500 hover:text-red-400 rounded-lg transition-colors"
            onClick={() => {
              if (window.confirm(`Delete "${item.name}"?`)) deleteMutation.mutate();
            }}
          >
            <Trash2 size={12} />
          </button>
        </div>
      </div>

      {showEdit && <IntegrationModal existing={item} onClose={() => setShowEdit(false)} />}
      {showLogs && <LogsModal integration={item} onClose={() => setShowLogs(false)} />}
    </>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function IntegrationsPage() {
  const { t } = useTranslation();
  const [showCreate, setShowCreate] = useState(false);

  const { data: integrations = [], isLoading } = useQuery({
    queryKey: ["integrations"],
    queryFn: () => integrationsApi.list().then((r) => r.data.results ?? r.data),
  });

  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-lg sm:text-xl font-bold text-white">{t("integrations.title")}</h1>
          <p className="text-sm text-gray-400 mt-0.5">{t("integrations.subtitle")}</p>
        </div>
        <button className="btn-primary flex items-center gap-1.5" onClick={() => setShowCreate(true)}>
          <Plus size={14} />
          <span className="hidden sm:inline">{t("integrations.newIntegration")}</span>
        </button>
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array(3).fill(null).map((_, i) => (
            <div key={i} className="card animate-pulse h-48 bg-gray-800" />
          ))}
        </div>
      ) : integrations.length === 0 ? (
        <div className="card text-center py-16">
          <Zap size={36} className="mx-auto text-gray-700 mb-3" />
          <p className="text-gray-400 font-medium">{t("integrations.noIntegrations")}</p>
          <button className="btn-primary mt-4" onClick={() => setShowCreate(true)}>
            <Plus size={14} className="inline mr-1" />
            {t("integrations.newIntegration")}
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {integrations.map((item) => (
            <IntegrationCard key={item.id} item={item} />
          ))}
        </div>
      )}

      {showCreate && <IntegrationModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}

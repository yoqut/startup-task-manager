import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ShieldCheck, CheckCircle, XCircle, Clock, Bot } from "lucide-react";
import { approvalsApi } from "../../api/agents";
import clsx from "clsx";

const STATUS_STYLES = {
  pending:      "bg-yellow-500/15 text-yellow-400",
  approved:     "bg-green-500/15 text-green-400",
  rejected:     "bg-red-500/15 text-red-400",
  expired:      "bg-gray-700 text-gray-400",
  auto_approved:"bg-blue-500/15 text-blue-400",
};

export default function ApprovalsPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();

  const { data: approvals = [], isLoading } = useQuery({
    queryKey: ["approvals"],
    queryFn: () => approvalsApi.list().then((r) => r.data.results ?? r.data),
    refetchInterval: 20_000,
  });

  const approveMutation = useMutation({
    mutationFn: (id) => approvalsApi.approve(id, {}),
    onSuccess: () => qc.invalidateQueries(["approvals"]),
  });

  const rejectMutation = useMutation({
    mutationFn: (id) => approvalsApi.reject(id, {}),
    onSuccess: () => qc.invalidateQueries(["approvals"]),
  });

  const pending  = approvals.filter((a) => a.status === "pending");
  const resolved = approvals.filter((a) => a.status !== "pending");

  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-lg sm:text-xl font-bold text-white">{t("approvals.title")}</h1>
        <p className="text-sm text-gray-400 mt-0.5">{t("approvals.subtitle")}</p>
      </div>

      {/* Pending */}
      <section>
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3 flex items-center gap-2">
          <Clock size={14} className="text-yellow-400" />
          {t("approvals.pending")} ({pending.length})
        </h2>

        {isLoading ? (
          <div className="card animate-pulse h-24 bg-gray-800" />
        ) : pending.length === 0 ? (
          <div className="card text-center py-8">
            <ShieldCheck size={28} className="text-green-400 mx-auto mb-2" />
            <p className="text-sm text-gray-400">{t("approvals.noPending")}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {pending.map((approval) => (
              <ApprovalCard
                key={approval.id}
                approval={approval}
                onApprove={() => approveMutation.mutate(approval.id)}
                onReject={() => rejectMutation.mutate(approval.id)}
                isApproving={approveMutation.isPending}
                isRejecting={rejectMutation.isPending}
              />
            ))}
          </div>
        )}
      </section>

      {/* Resolved */}
      {resolved.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
            {t("approvals.recentDecisions")}
          </h2>
          <div className="card p-0 overflow-hidden">
            {resolved.slice(0, 10).map((approval) => (
              <div key={approval.id} className="flex items-center gap-4 px-5 py-3 border-b border-gray-800 last:border-0">
                <span className={clsx("badge capitalize flex-shrink-0", STATUS_STYLES[approval.status])}>
                  {t(`approvals.statuses.${approval.status}`)}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-300 truncate">{approval.title}</p>
                  <p className="text-xs text-gray-500">{approval.agent_type_display}</p>
                </div>
                <p className="text-xs text-gray-600 flex-shrink-0 hidden md:block">
                  {approval.decided_by_name || t("approvals.noDecider")}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function ApprovalCard({ approval, onApprove, onReject, isApproving, isRejecting }) {
  const { t } = useTranslation();
  const confidence = Math.round((approval.confidence_score || 0) * 100);
  const expiresIn  = Math.max(0, Math.floor((new Date(approval.expires_at) - Date.now()) / 1000 / 60 / 60));

  return (
    <div className="card border-yellow-500/20">
      <div className="flex flex-wrap items-start justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <Bot size={15} className="text-brand-400 flex-shrink-0" />
          <span className="text-xs text-gray-400">{approval.agent_type_display}</span>
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3 text-xs text-gray-500">
          <span>
            {t("approvals.confidence")}: <span className={confidence >= 80 ? "text-green-400" : "text-yellow-400"}>{confidence}%</span>
          </span>
          <span>{t("approvals.expiresIn", { hours: expiresIn })}</span>
        </div>
      </div>

      <h3 className="font-medium text-white mb-2">{approval.title}</h3>

      {approval.reasoning && (
        <p className="text-sm text-gray-400 mb-4 leading-relaxed border-l-2 border-gray-700 pl-3">
          {approval.reasoning.slice(0, 250)}{approval.reasoning.length > 250 ? "..." : ""}
        </p>
      )}

      <div className="flex gap-2">
        <button
          onClick={onApprove}
          disabled={isApproving}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-green-500/15 text-green-400 rounded-lg text-sm hover:bg-green-500/25 transition-colors font-medium"
        >
          <CheckCircle size={14} /> {t("approvals.approve")}
        </button>
        <button
          onClick={onReject}
          disabled={isRejecting}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-red-500/15 text-red-400 rounded-lg text-sm hover:bg-red-500/25 transition-colors font-medium"
        >
          <XCircle size={14} /> {t("approvals.reject")}
        </button>
      </div>
    </div>
  );
}

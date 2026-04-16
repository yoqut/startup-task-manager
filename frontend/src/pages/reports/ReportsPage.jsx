import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Plus, Send, CheckCircle, Eye, MessageSquare } from "lucide-react";
import { reportsApi } from "../../api/reports";
import useAuthStore from "../../store/authStore";
import clsx from "clsx";

const STATUS_COLORS = {
  sent:         "bg-yellow-500/15 text-yellow-400",
  read:         "bg-blue-500/15 text-blue-400",
  acknowledged: "bg-green-500/15 text-green-400",
};

const TYPE_COLORS = {
  daily:    "text-blue-400",
  weekly:   "text-purple-400",
  issue:    "text-red-400",
  progress: "text-green-400",
  request:  "text-yellow-400",
};

function ReportDetailModal({ report: initialReport, onClose }) {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const qc = useQueryClient();
  const [comment, setComment] = useState("");

  const { data: report = initialReport } = useQuery({
    queryKey: ["report", initialReport.id],
    queryFn:  () => reportsApi.get(initialReport.id).then(r => r.data),
  });

  const commentMutation = useMutation({
    mutationFn: (body) => reportsApi.addComment(report.id, { body }),
    onSuccess:  () => { qc.invalidateQueries(["report", report.id]); qc.invalidateQueries(["reports"]); setComment(""); },
  });

  const ackMutation = useMutation({
    mutationFn: () => reportsApi.acknowledge(report.id),
    onSuccess:  () => { qc.invalidateQueries(["report", report.id]); qc.invalidateQueries(["reports"]); },
  });

  const canAck = user?.role !== "member" && report.status !== "acknowledged";

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-lg space-y-4 max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 flex-shrink-0">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-white truncate">{report.title}</h3>
            <div className="flex items-center gap-2 mt-1">
              <span className={clsx("text-xs font-medium", TYPE_COLORS[report.report_type])}>
                {t(`reports.types.${report.report_type}`)}
              </span>
              <span className="text-gray-600">·</span>
              <span className="text-xs text-gray-500">{report.sent_by_name}</span>
              <span className="text-gray-600">·</span>
              <span className="text-xs text-gray-500">{new Date(report.created_at).toLocaleDateString()}</span>
            </div>
          </div>
          <span className={clsx("badge flex-shrink-0", STATUS_COLORS[report.status])}>
            {t(`reports.statuses.${report.status}`)}
          </span>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto space-y-4">
          <p className="text-sm text-gray-300 whitespace-pre-wrap">{report.body}</p>

          {/* Comments */}
          {report.comments?.length > 0 && (
            <div className="space-y-2 border-t border-gray-800 pt-3">
              <p className="text-xs text-gray-500 font-medium">{t("discussions.comments")}</p>
              {report.comments.map(c => (
                <div key={c.id} className="bg-gray-800/50 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium text-gray-300">{c.author_name}</span>
                    <span className="text-xs text-gray-600">{new Date(c.created_at).toLocaleDateString()}</span>
                  </div>
                  <p className="text-sm text-gray-400">{c.body}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Add comment */}
        <div className="flex-shrink-0 border-t border-gray-800 pt-3 space-y-2">
          <textarea
            className="input resize-none h-16 text-sm"
            placeholder={t("discussions.addComment")}
            value={comment}
            onChange={e => setComment(e.target.value)}
          />
          <div className="flex gap-2">
            {canAck && (
              <button
                className="flex items-center gap-1.5 px-3 py-1.5 bg-green-500/20 text-green-400 rounded-lg text-sm hover:bg-green-500/30 transition-colors"
                onClick={() => ackMutation.mutate()}
                disabled={ackMutation.isPending}
              >
                <CheckCircle size={14} /> {t("reports.acknowledge")}
              </button>
            )}
            <button
              className="flex-1 flex items-center justify-center gap-1.5 py-1.5 bg-brand-500/20 text-brand-400 rounded-lg text-sm hover:bg-brand-500/30 transition-colors"
              onClick={() => comment.trim() && commentMutation.mutate(comment.trim())}
              disabled={!comment.trim() || commentMutation.isPending}
            >
              <Send size={14} /> {t("common.send")}
            </button>
            <button className="btn-secondary text-sm" onClick={onClose}>{t("common.close")}</button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ReportsPage() {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [selected, setSelected] = useState(null);
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const { data: reports = [], isLoading } = useQuery({
    queryKey: ["reports", { type: typeFilter, status: statusFilter }],
    queryFn:  () => reportsApi.list({ report_type: typeFilter || undefined, status: statusFilter || undefined }).then(r => r.data.results ?? r.data),
  });

  const TYPES    = ["daily", "weekly", "issue", "progress", "request"];
  const STATUSES = ["sent", "read", "acknowledged"];

  const isOwnerOrManager = user?.role && ["owner", "admin", "manager"].includes(user.role);

  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto space-y-4 sm:space-y-5">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-lg sm:text-xl font-bold text-white">{t("nav.reports")}</h1>
        <button
          onClick={() => navigate("/reports/new")}
          className="btn-primary flex items-center gap-1.5 text-sm"
        >
          <Plus size={15} />
          <span className="hidden sm:inline">{t("reports.sendReport")}</span>
          <span className="sm:hidden">{t("common.send")}</span>
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 sm:gap-3">
        <select className="input flex-1 min-w-[130px]" value={typeFilter} onChange={e => setTypeFilter(e.target.value)}>
          <option value="">{t("reports.allTypes")}</option>
          {TYPES.map(tp => <option key={tp} value={tp}>{t(`reports.types.${tp}`)}</option>)}
        </select>
        <select className="input flex-1 min-w-[130px]" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="">{t("common.status")}: {t("common.all")}</option>
          {STATUSES.map(s => <option key={s} value={s}>{t(`reports.statuses.${s}`)}</option>)}
        </select>
      </div>

      {/* Reports list */}
      <div className="card p-0 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500 text-sm">{t("common.loading")}</div>
        ) : reports.length === 0 ? (
          <div className="p-8 text-center text-gray-500 text-sm">{t("reports.noReports")}</div>
        ) : (
          <div className="divide-y divide-gray-800">
            {reports.map(r => (
              <div
                key={r.id}
                onClick={() => setSelected(r)}
                className="px-5 py-4 hover:bg-gray-800/40 transition-colors cursor-pointer flex items-center gap-4"
              >
                {/* Unread dot */}
                <div className="flex-shrink-0">
                  {r.status === "sent" && isOwnerOrManager
                    ? <span className="w-2 h-2 rounded-full bg-brand-500 block" />
                    : <span className="w-2 h-2 block" />
                  }
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={clsx("text-xs font-medium", TYPE_COLORS[r.report_type])}>
                      {t(`reports.types.${r.report_type}`)}
                    </span>
                    {r.department && (
                      <span className="text-xs text-gray-600">· {t(`tasks.departments.${r.department}`, r.department)}</span>
                    )}
                  </div>
                  <p className="text-sm text-gray-200 mt-0.5 truncate">{r.title}</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {t("reports.from")}: {r.sent_by_name} · {new Date(r.created_at).toLocaleDateString()}
                  </p>
                </div>

                {/* Meta */}
                <div className="flex items-center gap-3 flex-shrink-0">
                  {r.comment_count > 0 && (
                    <span className="flex items-center gap-1 text-xs text-gray-500">
                      <MessageSquare size={12} /> {r.comment_count}
                    </span>
                  )}
                  <span className={clsx("badge", STATUS_COLORS[r.status])}>
                    {t(`reports.statuses.${r.status}`)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {selected && (
        <ReportDetailModal report={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}

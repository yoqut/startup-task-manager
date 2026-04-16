import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { AlertTriangle, ShieldCheck, Clock, CheckSquare, Bot, CheckCircle, XCircle } from "lucide-react";
import { tasksApi } from "../../api/tasks";
import { approvalsApi } from "../../api/agents";
import useAuthStore from "../../store/authStore";
import clsx from "clsx";

const PRIORITY_COLOR = {
  critical: "bg-red-500/15 text-red-400 border-red-500/30",
  high:     "bg-orange-500/15 text-orange-400 border-orange-500/30",
  medium:   "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
  low:      "bg-gray-700 text-gray-400 border-gray-600",
};

function StatCard({ icon: Icon, label, value, color = "brand" }) {
  const colorMap = {
    brand:  "bg-brand-500/15 text-brand-400",
    red:    "bg-red-500/15 text-red-400",
    yellow: "bg-yellow-500/15 text-yellow-400",
    green:  "bg-green-500/15 text-green-400",
  };
  return (
    <div className="card flex items-start gap-4">
      <div className={clsx("w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0", colorMap[color])}>
        <Icon size={18} />
      </div>
      <div>
        <p className="text-2xl font-bold text-white">{value ?? "—"}</p>
        <p className="text-sm text-gray-400">{label}</p>
      </div>
    </div>
  );
}

function getGreeting(t) {
  const h = new Date().getHours();
  if (h < 12) return t("dashboard.greeting.morning");
  if (h < 17) return t("dashboard.greeting.afternoon");
  return t("dashboard.greeting.evening");
}

export default function DashboardPage() {
  const { t } = useTranslation();
  const { user } = useAuthStore();

  const { data: overdue } = useQuery({
    queryKey: ["tasks", "overdue"],
    queryFn: () => tasksApi.overdue().then((r) => r.data),
  });

  const { data: blocked } = useQuery({
    queryKey: ["tasks", "blocked"],
    queryFn: () => tasksApi.blocked().then((r) => r.data),
  });

  const { data: pending, refetch: refetchPending } = useQuery({
    queryKey: ["approvals", "pending"],
    queryFn: () => approvalsApi.pending().then((r) => r.data),
    refetchInterval: 30_000,
  });

  const { data: myTasks } = useQuery({
    queryKey: ["tasks", "mine"],
    queryFn: () => tasksApi.myTasks().then((r) => r.data),
  });

  const handleApprove = async (id) => {
    await approvalsApi.approve(id, {});
    refetchPending();
  };
  const handleReject = async (id) => {
    await approvalsApi.reject(id, {});
    refetchPending();
  };

  return (
    <div className="p-4 sm:p-6 max-w-6xl mx-auto space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-lg sm:text-xl font-bold text-white">
          {getGreeting(t)}, {user?.first_name} 👋
        </h1>
        <p className="text-sm text-gray-400 mt-0.5">{t("dashboard.subtitle")}</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <StatCard icon={AlertTriangle} label={t("dashboard.overdueTasks")}     value={overdue?.length}  color="red" />
        <StatCard icon={ShieldCheck}   label={t("dashboard.pendingApprovals")} value={pending?.length}  color="yellow" />
        <StatCard icon={Clock}         label={t("dashboard.blockedTasks")}      value={blocked?.length}  color="red" />
        <StatCard icon={CheckSquare}   label={t("dashboard.myOpenTasks")}       value={myTasks?.length}  color="brand" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 sm:gap-5">
        {/* Overdue tasks */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white flex items-center gap-2">
              <AlertTriangle size={16} className="text-red-400" />
              {t("dashboard.overdueTasks")}
            </h2>
            <span className="badge bg-red-500/15 text-red-400">{overdue?.length ?? 0}</span>
          </div>
          {!overdue?.length ? (
            <p className="text-sm text-gray-500">{t("dashboard.noOverdue")}</p>
          ) : (
            <ul className="space-y-2">
              {overdue.slice(0, 6).map((task) => (
                <li key={task.id} className="flex items-start justify-between gap-3 py-2 border-b border-gray-800 last:border-0">
                  <div className="min-w-0">
                    <p className="text-sm text-gray-200 truncate">{task.title}</p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {task.assigned_to_name || t("dashboard.unassigned")} · {task.department}
                    </p>
                  </div>
                  <span className={clsx("badge border flex-shrink-0", PRIORITY_COLOR[task.priority])}>
                    {task.priority}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Pending Approvals */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white flex items-center gap-2">
              <Bot size={16} className="text-brand-400" />
              {t("dashboard.pendingAgentApprovals")}
            </h2>
            <span className="badge bg-yellow-500/15 text-yellow-400">{pending?.length ?? 0}</span>
          </div>
          {!pending?.length ? (
            <p className="text-sm text-gray-500">{t("dashboard.noPending")}</p>
          ) : (
            <ul className="space-y-2">
              {pending.slice(0, 5).map((approval) => (
                <li key={approval.id} className="py-2 border-b border-gray-800 last:border-0">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-sm text-gray-200 truncate">{approval.title}</p>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {approval.agent_type_display} · {Math.round(approval.confidence_score * 100)}% {t("dashboard.confidence")}
                      </p>
                    </div>
                    <div className="flex gap-1 flex-shrink-0">
                      <button
                        onClick={() => handleApprove(approval.id)}
                        className="text-xs px-2 py-1 bg-green-500/15 text-green-400 rounded hover:bg-green-500/25 transition-colors"
                        title={t("common.approve")}
                      >
                        <CheckCircle size={13} />
                      </button>
                      <button
                        onClick={() => handleReject(approval.id)}
                        className="text-xs px-2 py-1 bg-red-500/15 text-red-400 rounded hover:bg-red-500/25 transition-colors"
                        title={t("common.reject")}
                      >
                        <XCircle size={13} />
                      </button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

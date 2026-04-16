import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, Clock, FileText, MessageSquare, Plus } from "lucide-react";
import { tasksApi } from "../../api/tasks";
import { reportsApi } from "../../api/reports";
import useAuthStore from "../../store/authStore";
import clsx from "clsx";

const STATUS_COLORS = {
  backlog:     "bg-gray-700 text-gray-300",
  todo:        "bg-blue-500/15 text-blue-400",
  in_progress: "bg-brand-500/15 text-brand-400",
  blocked:     "bg-red-500/15 text-red-400",
  in_review:   "bg-purple-500/15 text-purple-400",
  done:        "bg-green-500/15 text-green-400",
  cancelled:   "bg-gray-700 text-gray-500",
};

export default function ManagerDashboard() {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const navigate = useNavigate();

  const hour = new Date().getHours();
  const greetKey = hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";

  const dept = user?.department || "";

  const { data: myTasks  = [] } = useQuery({
    queryKey: ["tasks", "my"],
    queryFn:  () => tasksApi.myTasks().then(r => r.data),
  });
  const { data: deptTasks = [] } = useQuery({
    queryKey: ["tasks", { department: dept }],
    queryFn:  () => tasksApi.list({ department: dept }).then(r => r.data.results ?? r.data),
    enabled:  !!dept,
  });
  const { data: reports = [] } = useQuery({
    queryKey: ["reports", {}],
    queryFn:  () => reportsApi.list({}).then(r => r.data.results ?? r.data),
  });

  const unread  = reports.filter(r => r.status === "sent").length;
  const blocked = deptTasks.filter(t => t.status === "blocked").length;

  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto space-y-6">
      {/* Greeting */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-lg sm:text-xl font-bold text-white">
            {t(`dashboard.greeting.${greetKey}`)}, {user?.first_name}
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {dept ? t(`tasks.departments.${dept}`, dept) : ""} {t("manager.deptOverview")}
          </p>
        </div>
        <button
          onClick={() => navigate("/reports/new")}
          className="btn-primary flex items-center gap-2 text-sm"
        >
          <Plus size={15} /> {t("reports.sendReport")}
        </button>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4">
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold text-brand-400">{myTasks.length}</p>
          <p className="text-xs text-gray-500 mt-1">{t("dashboard.myOpenTasks")}</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold text-red-400">{blocked}</p>
          <p className="text-xs text-gray-500 mt-1">{t("dashboard.blockedTasks")}</p>
        </div>
        <div className="card p-4 text-center cursor-pointer hover:border-gray-600 transition-colors" onClick={() => navigate("/reports")}>
          <p className="text-2xl font-bold text-purple-400">{unread}</p>
          <p className="text-xs text-gray-500 mt-1">{t("owner.unreadReports")}</p>
        </div>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-2 gap-3">
        <button onClick={() => navigate("/reports")}     className="card flex items-center gap-3 p-4 hover:border-gray-600 transition-colors text-left">
          <FileText size={18} className="text-purple-400" />
          <span className="text-sm font-medium text-gray-200">{t("nav.reports")}</span>
        </button>
        <button onClick={() => navigate("/discussions")} className="card flex items-center gap-3 p-4 hover:border-gray-600 transition-colors text-left">
          <MessageSquare size={18} className="text-blue-400" />
          <span className="text-sm font-medium text-gray-200">{t("nav.discussions")}</span>
        </button>
      </div>

      {/* Dept tasks */}
      <div className="card p-0 overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-800 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">{t("manager.deptTasks")}</h2>
          <button onClick={() => navigate("/tasks")} className="text-xs text-brand-400 hover:text-brand-300">{t("common.all")}</button>
        </div>
        {deptTasks.length === 0 ? (
          <p className="p-5 text-sm text-gray-600">{t("tasks.noTasks")}</p>
        ) : (
          <div className="divide-y divide-gray-800">
            {deptTasks.slice(0, 6).map(task => (
              <div key={task.id} className="px-5 py-3 flex items-center gap-3">
                {task.is_overdue && <AlertTriangle size={13} className="text-red-400 flex-shrink-0" />}
                <span className="flex-1 text-sm text-gray-200 truncate">{task.title}</span>
                <span className={clsx("badge", STATUS_COLORS[task.status])}>
                  {t(`tasks.statuses.${task.status}`)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent reports received */}
      {reports.length > 0 && (
        <div className="card p-0 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-800 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">{t("reports.inbox")}</h2>
            <button onClick={() => navigate("/reports")} className="text-xs text-brand-400 hover:text-brand-300">{t("common.all")}</button>
          </div>
          <div className="divide-y divide-gray-800">
            {reports.slice(0, 4).map(r => (
              <div key={r.id} onClick={() => navigate("/reports")} className="px-5 py-3 flex items-center gap-3 cursor-pointer hover:bg-gray-800/40 transition-colors">
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-200 truncate">{r.title}</p>
                  <p className="text-xs text-gray-500">{r.sent_by_name}</p>
                </div>
                {r.status === "sent" && (
                  <span className="w-2 h-2 rounded-full bg-brand-500 flex-shrink-0" />
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

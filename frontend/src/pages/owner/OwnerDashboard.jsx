import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import {
  AlertTriangle, Clock, ShieldCheck, Users,
  TrendingUp, Bot, FileText, MessageSquare,
} from "lucide-react";
import { tasksApi } from "../../api/tasks";
import { reportsApi } from "../../api/reports";
import useAuthStore from "../../store/authStore";
import clsx from "clsx";

const PRIORITY_COLORS = {
  critical: "text-red-400",
  high:     "text-orange-400",
  medium:   "text-yellow-400",
  low:      "text-gray-500",
};

function StatCard({ icon: Icon, label, value, color, onClick }) {
  return (
    <div
      onClick={onClick}
      className={clsx(
        "card flex items-center gap-4 p-5",
        onClick && "cursor-pointer hover:border-gray-600 transition-colors"
      )}
    >
      <div className={clsx("w-11 h-11 rounded-xl flex items-center justify-center", color)}>
        <Icon size={20} className="text-white" />
      </div>
      <div>
        <p className="text-2xl font-bold text-white">{value ?? "—"}</p>
        <p className="text-xs text-gray-500 mt-0.5">{label}</p>
      </div>
    </div>
  );
}

export default function OwnerDashboard() {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const navigate = useNavigate();

  const hour = new Date().getHours();
  const greetKey = hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";

  const { data: overdue  = [] } = useQuery({ queryKey: ["tasks", "overdue"],  queryFn: () => tasksApi.overdue().then(r => r.data) });
  const { data: blocked  = [] } = useQuery({ queryKey: ["tasks", "blocked"],  queryFn: () => tasksApi.blocked().then(r => r.data) });
  const { data: allTasks = [] } = useQuery({ queryKey: ["tasks", {}],          queryFn: () => tasksApi.list({}).then(r => r.data.results ?? r.data) });
  const { data: reports  = [] } = useQuery({ queryKey: ["reports", {}],        queryFn: () => reportsApi.list({}).then(r => r.data.results ?? r.data) });

  const unreadReports = reports.filter(r => r.status === "sent").length;
  const openTasks     = allTasks.filter(t => !["done","cancelled"].includes(t.status)).length;

  const deptStats = allTasks.reduce((acc, t) => {
    acc[t.department] = (acc[t.department] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="p-4 sm:p-6 max-w-6xl mx-auto space-y-6">
      {/* Greeting */}
      <div>
        <h1 className="text-lg sm:text-xl font-bold text-white">
          {t(`dashboard.greeting.${greetKey}`)}, {user?.first_name}
        </h1>
        <p className="text-sm text-gray-500 mt-0.5">{t("dashboard.subtitle")}</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={AlertTriangle} label={t("dashboard.overdueTasks")}     value={overdue.length}   color="bg-red-500/20"    onClick={() => navigate("/tasks")} />
        <StatCard icon={Clock}        label={t("dashboard.blockedTasks")}      value={blocked.length}   color="bg-orange-500/20" onClick={() => navigate("/tasks")} />
        <StatCard icon={TrendingUp}   label={t("owner.openTasks")}             value={openTasks}        color="bg-brand-500/20"  onClick={() => navigate("/tasks")} />
        <StatCard icon={FileText}     label={t("owner.unreadReports")}         value={unreadReports}    color="bg-purple-500/20" onClick={() => navigate("/reports")} />
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { icon: Users,         label: t("nav.team"),        path: "/team"        },
          { icon: FileText,      label: t("nav.reports"),     path: "/reports"     },
          { icon: MessageSquare, label: t("nav.discussions"), path: "/discussions" },
          { icon: Bot,           label: t("nav.aiAgents"),    path: "/agents"      },
        ].map(({ icon: Icon, label, path }) => (
          <button
            key={path}
            onClick={() => navigate(path)}
            className="card flex items-center gap-3 p-4 hover:border-gray-600 transition-colors text-left"
          >
            <Icon size={18} className="text-brand-400 flex-shrink-0" />
            <span className="text-sm font-medium text-gray-200">{label}</span>
          </button>
        ))}
      </div>

      {/* Department overview */}
      <div className="card space-y-3">
        <h2 className="text-sm font-semibold text-white">{t("owner.tasksByDept")}</h2>
        <div className="space-y-2">
          {Object.entries(deptStats).map(([dept, count]) => (
            <div key={dept} className="flex items-center gap-3">
              <span className="text-xs text-gray-500 w-28 capitalize">
                {t(`tasks.departments.${dept}`, dept)}
              </span>
              <div className="flex-1 bg-gray-800 rounded-full h-2">
                <div
                  className="bg-brand-500 h-2 rounded-full"
                  style={{ width: `${Math.min((count / (allTasks.length || 1)) * 100, 100)}%` }}
                />
              </div>
              <span className="text-xs text-gray-400 w-6 text-right">{count}</span>
            </div>
          ))}
          {Object.keys(deptStats).length === 0 && (
            <p className="text-xs text-gray-600">{t("common.noData")}</p>
          )}
        </div>
      </div>

      {/* Recent overdue tasks */}
      {overdue.length > 0 && (
        <div className="card p-0 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-800">
            <h2 className="text-sm font-semibold text-white">{t("dashboard.overdueTasks")}</h2>
          </div>
          <div className="divide-y divide-gray-800">
            {overdue.slice(0, 5).map(task => (
              <div key={task.id} className="px-5 py-3 flex items-center gap-3">
                <AlertTriangle size={13} className="text-red-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-200 truncate">{task.title}</p>
                  <p className="text-xs text-gray-500">{t(`tasks.departments.${task.department}`)}</p>
                </div>
                <span className={clsx("text-xs font-medium", PRIORITY_COLORS[task.priority])}>
                  {t(`tasks.priorities.${task.priority}`)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

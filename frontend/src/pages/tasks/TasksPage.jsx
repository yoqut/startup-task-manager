import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Plus, Search, AlertTriangle, Bot, X, Send, MessageSquare, ChevronRight } from "lucide-react";
import { tasksApi } from "../../api/tasks";
import VoiceTaskButton from "../../components/ui/VoiceTaskButton";
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

const PRIORITY_COLORS = {
  critical: "text-red-400",
  high:     "text-orange-400",
  medium:   "text-yellow-400",
  low:      "text-gray-500",
};

// ── Create Task Modal ─────────────────────────────────────────────────────────
function CreateTaskModal({ onClose, onCreate }) {
  const { t } = useTranslation();
  const [form, setForm] = useState({
    title: "", description: "", priority: "medium",
    department: "general", status: "todo",
  });
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const PRIORITIES  = ["critical", "high", "medium", "low"];
  const DEPARTMENTS = ["operations", "sales", "marketing", "support", "finance", "hr", "general"];

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-md space-y-4">
        <h3 className="font-semibold text-white">{t("tasks.newTask")}</h3>
        <div>
          <label className="label">{t("tasks.taskTitle")} *</label>
          <input className="input" value={form.title} onChange={(e) => set("title", e.target.value)} placeholder={t("tasks.taskTitle")} />
        </div>
        <div>
          <label className="label">{t("tasks.description")}</label>
          <textarea className="input resize-none h-20" value={form.description} onChange={(e) => set("description", e.target.value)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">{t("tasks.priority")}</label>
            <select className="input" value={form.priority} onChange={(e) => set("priority", e.target.value)}>
              {PRIORITIES.map(p => <option key={p} value={p}>{t(`tasks.priorities.${p}`)}</option>)}
            </select>
          </div>
          <div>
            <label className="label">{t("tasks.department")}</label>
            <select className="input" value={form.department} onChange={(e) => set("department", e.target.value)}>
              {DEPARTMENTS.map(d => <option key={d} value={d}>{t(`tasks.departments.${d}`)}</option>)}
            </select>
          </div>
        </div>
        <div className="flex gap-2 pt-2">
          <button className="btn-primary flex-1" onClick={() => onCreate(form)} disabled={!form.title}>
            {t("common.create")}
          </button>
          <button className="btn-secondary" onClick={onClose}>{t("common.cancel")}</button>
        </div>
      </div>
    </div>
  );
}

// ── Send Report Modal ─────────────────────────────────────────────────────────
function SendReportModal({ task, onClose }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState({ body: "", report_type: "progress" });
  const TYPES = ["progress", "issue", "daily"];

  const mutation = useMutation({
    mutationFn: (data) => tasksApi.sendReport(task.id, data),
    onSuccess:  () => { qc.invalidateQueries(["tasks"]); onClose(); },
  });

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-md space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-white">{t("tasks.sendReport")}</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300"><X size={16} /></button>
        </div>
        <p className="text-sm text-gray-400 truncate">{task.title}</p>

        <div>
          <label className="label">{t("reports.reportType")}</label>
          <select className="input" value={form.report_type} onChange={e => setForm(f => ({ ...f, report_type: e.target.value }))}>
            {TYPES.map(tp => <option key={tp} value={tp}>{t(`reports.types.${tp}`)}</option>)}
          </select>
        </div>

        <div>
          <label className="label">{t("reports.body")} *</label>
          <textarea
            className="input resize-none h-28"
            placeholder={t("reports.bodyPlaceholder")}
            value={form.body}
            onChange={e => setForm(f => ({ ...f, body: e.target.value }))}
          />
        </div>

        {mutation.error && <p className="text-xs text-red-400">{t("common.noData")}</p>}

        <div className="flex gap-2 pt-1">
          <button
            className="btn-primary flex-1 flex items-center justify-center gap-2"
            onClick={() => mutation.mutate(form)}
            disabled={!form.body.trim() || mutation.isPending}
          >
            <Send size={14} />
            {mutation.isPending ? t("common.loading") : t("common.send")}
          </button>
          <button className="btn-secondary" onClick={onClose}>{t("common.cancel")}</button>
        </div>
      </div>
    </div>
  );
}

// ── Task Detail Modal ─────────────────────────────────────────────────────────
function TaskDetailModal({ task, onClose }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [comment, setComment] = useState("");
  const [showReport, setShowReport] = useState(false);

  const { data: comments = [] } = useQuery({
    queryKey: ["task-comments", task.id],
    queryFn:  () => tasksApi.getComments(task.id).then(r => r.data),
  });

  const STATUSES = ["backlog", "todo", "in_progress", "blocked", "in_review", "done", "cancelled"];

  const statusMutation = useMutation({
    mutationFn: (st) => tasksApi.update(task.id, { status: st }),
    onSuccess:  () => qc.invalidateQueries(["tasks"]),
  });

  const commentMutation = useMutation({
    mutationFn: (body) => tasksApi.addComment(task.id, { body }),
    onSuccess:  () => { qc.invalidateQueries(["task-comments", task.id]); setComment(""); },
  });

  const aiComments = comments.filter(c => c.is_ai_generated);
  const userComments = comments.filter(c => !c.is_ai_generated);

  return (
    <>
      <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
        <div className="card w-full max-w-xl space-y-4 max-h-[88vh] overflow-y-auto">
          {/* Header */}
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-white leading-snug">{task.title}</h3>
              <div className="flex flex-wrap items-center gap-2 mt-1">
                <span className={clsx("badge", STATUS_COLORS[task.status])}>
                  {t(`tasks.statuses.${task.status}`)}
                </span>
                <span className={clsx("text-xs font-medium", PRIORITY_COLORS[task.priority])}>
                  {t(`tasks.priorities.${task.priority}`)}
                </span>
                <span className="text-xs text-gray-500">
                  {t(`tasks.departments.${task.department}`)}
                </span>
              </div>
            </div>
            <button onClick={onClose} className="text-gray-500 hover:text-gray-300 flex-shrink-0">
              <X size={16} />
            </button>
          </div>

          {/* Description */}
          {task.description && (
            <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap border-l-2 border-gray-700 pl-3">
              {task.description}
            </p>
          )}

          {/* Meta */}
          <div className="grid grid-cols-2 gap-3 text-xs text-gray-500">
            <div>
              <p className="text-gray-600 uppercase tracking-wider mb-0.5">{t("tasks.assignedTo")}</p>
              <p className="text-gray-300">{task.assigned_to_name || t("dashboard.unassigned")}</p>
            </div>
            {task.due_date && (
              <div>
                <p className="text-gray-600 uppercase tracking-wider mb-0.5">{t("tasks.dueDate")}</p>
                <p className={clsx("text-gray-300", task.is_overdue && "text-red-400")}>
                  {new Date(task.due_date).toLocaleDateString()}
                  {task.is_overdue && " ⚠"}
                </p>
              </div>
            )}
          </div>

          {/* Status change */}
          <div>
            <label className="label">{t("common.status")}</label>
            <div className="flex flex-wrap gap-1.5">
              {STATUSES.map(st => (
                <button
                  key={st}
                  onClick={() => statusMutation.mutate(st)}
                  className={clsx(
                    "badge cursor-pointer transition-opacity",
                    STATUS_COLORS[st],
                    task.status === st ? "opacity-100 ring-1 ring-current" : "opacity-50 hover:opacity-80"
                  )}
                >
                  {t(`tasks.statuses.${st}`)}
                </button>
              ))}
            </div>
          </div>

          {/* AI Analysis */}
          {aiComments.length > 0 && (
            <div className="bg-brand-500/8 border border-brand-500/20 rounded-xl p-3 space-y-2">
              <div className="flex items-center gap-1.5 text-xs text-brand-400 font-medium">
                <Bot size={13} />
                {t("tasks.aiAnalysis")}
              </div>
              {aiComments.map(c => (
                <p key={c.id} className="text-xs text-gray-300 whitespace-pre-wrap leading-relaxed">
                  {c.body}
                </p>
              ))}
            </div>
          )}

          {/* User comments */}
          {userComments.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs text-gray-500 uppercase tracking-wider flex items-center gap-1">
                <MessageSquare size={11} /> {t("discussions.comments")}
              </p>
              {userComments.map(c => (
                <div key={c.id} className="bg-gray-800/50 rounded-lg px-3 py-2">
                  <p className="text-xs text-gray-500">{c.author_name}</p>
                  <p className="text-sm text-gray-200 mt-0.5 whitespace-pre-wrap">{c.body}</p>
                </div>
              ))}
            </div>
          )}

          {/* Add comment */}
          <div className="flex gap-2">
            <input
              className="input flex-1 text-sm"
              placeholder={t("discussions.addComment")}
              value={comment}
              onChange={e => setComment(e.target.value)}
              onKeyDown={e => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (comment.trim()) commentMutation.mutate(comment.trim());
                }
              }}
            />
            <button
              className="btn-secondary px-3"
              onClick={() => comment.trim() && commentMutation.mutate(comment.trim())}
              disabled={!comment.trim() || commentMutation.isPending}
            >
              <Send size={13} />
            </button>
          </div>

          {/* Send Report button */}
          <button
            onClick={() => setShowReport(true)}
            className="w-full flex items-center justify-center gap-2 py-2 rounded-lg border border-brand-500/30 text-brand-400 text-sm hover:bg-brand-500/10 transition-colors"
          >
            <Send size={14} /> {t("tasks.sendReport")}
          </button>
        </div>
      </div>

      {showReport && (
        <SendReportModal task={task} onClose={() => setShowReport(false)} />
      )}
    </>
  );
}

// ── Main Tasks Page ───────────────────────────────────────────────────────────
export default function TasksPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);

  const { data: tasks = [], isLoading } = useQuery({
    queryKey: ["tasks", { search, status: statusFilter }],
    queryFn: () => tasksApi.list({ search, status: statusFilter || undefined }).then((r) => r.data.results ?? r.data),
  });

  const createMutation = useMutation({
    mutationFn: tasksApi.create,
    onSuccess: () => { qc.invalidateQueries(["tasks"]); setShowCreate(false); },
  });

  const handleVoiceTask = (title) => {
    createMutation.mutate({ title, priority: "medium", department: "general", status: "todo" });
  };

  const STATUSES = ["backlog", "todo", "in_progress", "blocked", "in_review", "done"];

  return (
    <div className="p-4 sm:p-6 max-w-6xl mx-auto space-y-4 sm:space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg sm:text-xl font-bold text-white">{t("tasks.title")}</h1>
        <div className="flex items-center gap-2 ml-auto">
          <VoiceTaskButton onConfirm={handleVoiceTask} />
          <button className="btn-primary flex items-center gap-1.5 text-sm" onClick={() => setShowCreate(true)}>
            <Plus size={15} />
            <span className="hidden sm:inline">{t("tasks.newTask")}</span>
            <span className="sm:hidden">{t("common.create")}</span>
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 sm:gap-3">
        <div className="relative flex-1 min-w-[160px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            className="input pl-8 w-full"
            placeholder={t("tasks.searchTasks")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select className="input w-auto" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">{t("tasks.allStatuses")}</option>
          {STATUSES.map(s => (
            <option key={s} value={s}>{t(`tasks.statuses.${s}`)}</option>
          ))}
        </select>
      </div>

      {/* Task list */}
      <div className="card p-0 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500 text-sm">{t("common.loading")}</div>
        ) : tasks.length === 0 ? (
          <div className="p-8 text-center text-gray-500 text-sm">{t("tasks.noTasks")}</div>
        ) : (
          <>
            {/* Desktop table */}
            <div className="hidden sm:block overflow-x-auto">
              <table className="w-full text-sm min-w-[560px]">
                <thead>
                  <tr className="border-b border-gray-800">
                    <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">{t("tasks.taskTitle")}</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">{t("common.status")}</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">{t("tasks.priority")}</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">{t("tasks.assignedTo")}</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">{t("tasks.dueDate")}</th>
                    <th className="px-4 py-3 w-8" />
                  </tr>
                </thead>
                <tbody>
                  {tasks.map((task) => (
                    <tr
                      key={task.id}
                      onClick={() => setSelectedTask(task)}
                      className="border-b border-gray-800 last:border-0 hover:bg-gray-800/40 transition-colors cursor-pointer"
                    >
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2">
                          {task.is_overdue && <AlertTriangle size={13} className="text-red-400 flex-shrink-0" />}
                          {task.ai_priority_score != null && (
                            <Bot size={11} className="text-brand-400 flex-shrink-0" title="AI tahlil qildi" />
                          )}
                          <span className="text-gray-200 truncate max-w-[200px] lg:max-w-xs">{task.title}</span>
                        </div>
                        <p className="text-xs text-gray-500 mt-0.5">{t(`tasks.departments.${task.department}`)}</p>
                      </td>
                      <td className="px-4 py-3">
                        <span className={clsx("badge", STATUS_COLORS[task.status])}>
                          {t(`tasks.statuses.${task.status}`)}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={clsx("text-xs font-medium", PRIORITY_COLORS[task.priority])}>
                          {t(`tasks.priorities.${task.priority}`)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-xs">
                        {task.assigned_to_name || <span className="text-gray-600">{t("dashboard.unassigned")}</span>}
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-xs">
                        {task.due_date ? new Date(task.due_date).toLocaleDateString() : "—"}
                      </td>
                      <td className="px-4 py-3">
                        <ChevronRight size={14} className="text-gray-700" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile cards */}
            <div className="sm:hidden divide-y divide-gray-800">
              {tasks.map((task) => (
                <div
                  key={task.id}
                  onClick={() => setSelectedTask(task)}
                  className="px-4 py-3 space-y-1.5 active:bg-gray-800/40"
                >
                  <div className="flex items-start gap-2 justify-between">
                    <div className="flex items-center gap-1.5 min-w-0">
                      {task.is_overdue && <AlertTriangle size={13} className="text-red-400 flex-shrink-0" />}
                      {task.ai_priority_score != null && <Bot size={11} className="text-brand-400 flex-shrink-0" />}
                      <span className="text-sm text-gray-200 font-medium leading-snug">{task.title}</span>
                    </div>
                    <span className={clsx("badge flex-shrink-0", STATUS_COLORS[task.status])}>
                      {t(`tasks.statuses.${task.status}`)}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-gray-500 flex-wrap">
                    <span className={clsx("font-medium", PRIORITY_COLORS[task.priority])}>
                      {t(`tasks.priorities.${task.priority}`)}
                    </span>
                    <span>{t(`tasks.departments.${task.department}`)}</span>
                    {task.assigned_to_name && <span>{task.assigned_to_name}</span>}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {showCreate && (
        <CreateTaskModal
          onClose={() => setShowCreate(false)}
          onCreate={(data) => createMutation.mutate(data)}
        />
      )}

      {selectedTask && (
        <TaskDetailModal
          task={selectedTask}
          onClose={() => setSelectedTask(null)}
        />
      )}
    </div>
  );
}

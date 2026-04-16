import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { MessageSquare, Send, AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";
import { tasksApi } from "../../api/tasks";
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

function TaskThread({ task }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [open, setOpen] = useState(task.status === "blocked");
  const [newComment, setNewComment] = useState("");

  const { data: comments = [], isLoading } = useQuery({
    queryKey: ["task-comments", task.id],
    queryFn:  () => tasksApi.getComments(task.id).then(r => r.data),
    enabled:  open,
  });

  const mutation = useMutation({
    mutationFn: (body) => tasksApi.addComment(task.id, { body }),
    onSuccess: () => {
      qc.invalidateQueries(["task-comments", task.id]);
      setNewComment("");
    },
  });

  return (
    <div className="border border-gray-800 rounded-xl overflow-hidden">
      {/* Task header (clickable to expand) */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full px-5 py-3 flex items-center gap-3 hover:bg-gray-800/40 transition-colors text-left"
      >
        {task.is_overdue && <AlertTriangle size={13} className="text-red-400 flex-shrink-0" />}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-200 truncate">{task.title}</p>
          <p className="text-xs text-gray-500">{t(`tasks.departments.${task.department}`)}</p>
        </div>
        <span className={clsx("badge flex-shrink-0", STATUS_COLORS[task.status])}>
          {t(`tasks.statuses.${task.status}`)}
        </span>
        {open ? <ChevronUp size={14} className="text-gray-500 flex-shrink-0" /> : <ChevronDown size={14} className="text-gray-500 flex-shrink-0" />}
      </button>

      {/* Thread body */}
      {open && (
        <div className="border-t border-gray-800 p-4 space-y-3 bg-gray-900/50">
          {/* Description */}
          {task.description && (
            <p className="text-sm text-gray-400 italic">{task.description}</p>
          )}

          {/* Blocker reason */}
          {task.status === "blocked" && task.blocker_reason && (
            <div className="flex gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
              <AlertTriangle size={14} className="text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-300">{task.blocker_reason}</p>
            </div>
          )}

          {/* Comments */}
          {isLoading ? (
            <p className="text-xs text-gray-600">{t("common.loading")}</p>
          ) : comments.length === 0 ? (
            <p className="text-xs text-gray-600">{t("discussions.noComments")}</p>
          ) : (
            <div className="space-y-2">
              {comments.map(c => (
                <div key={c.id} className="flex gap-2">
                  <div className="w-6 h-6 rounded-full bg-brand-500/20 flex items-center justify-center text-xs font-bold text-brand-400 flex-shrink-0 mt-0.5">
                    {c.author_name?.[0]}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-baseline gap-2">
                      <span className="text-xs font-medium text-gray-300">{c.author_name}</span>
                      <span className="text-xs text-gray-600">{new Date(c.created_at).toLocaleDateString()}</span>
                      {c.is_ai_generated && (
                        <span className="text-xs text-brand-500">AI</span>
                      )}
                    </div>
                    <p className="text-sm text-gray-400 mt-0.5">{c.body}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Add comment */}
          <div className="flex gap-2 pt-1">
            <input
              className="input flex-1 text-sm h-9"
              placeholder={t("discussions.addComment")}
              value={newComment}
              onChange={e => setNewComment(e.target.value)}
              onKeyDown={e => {
                if (e.key === "Enter" && newComment.trim()) {
                  mutation.mutate(newComment.trim());
                }
              }}
            />
            <button
              onClick={() => newComment.trim() && mutation.mutate(newComment.trim())}
              disabled={!newComment.trim() || mutation.isPending}
              className="w-9 h-9 flex items-center justify-center bg-brand-500/20 text-brand-400 rounded-lg hover:bg-brand-500/30 transition-colors disabled:opacity-40"
            >
              <Send size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function DiscussionsPage() {
  const { t } = useTranslation();
  const [statusFilter, setStatusFilter] = useState("blocked");
  const [deptFilter, setDeptFilter] = useState("");

  const { data: tasks = [], isLoading } = useQuery({
    queryKey: ["tasks", { status: statusFilter, department: deptFilter }],
    queryFn:  () => tasksApi.list({
      status:     statusFilter || undefined,
      department: deptFilter   || undefined,
    }).then(r => r.data.results ?? r.data),
  });

  const STATUSES   = ["", "blocked", "in_progress", "in_review", "todo"];
  const DEPARTMENTS = ["", "operations", "sales", "marketing", "support", "finance", "hr", "general"];

  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto space-y-5">
      <div className="flex items-center gap-2">
        <MessageSquare size={20} className="text-brand-400" />
        <h1 className="text-lg sm:text-xl font-bold text-white">{t("nav.discussions")}</h1>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <select className="input max-w-[200px]" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="">{t("tasks.allStatuses")}</option>
          {STATUSES.filter(Boolean).map(s => (
            <option key={s} value={s}>{t(`tasks.statuses.${s}`)}</option>
          ))}
        </select>
        <select className="input max-w-[180px]" value={deptFilter} onChange={e => setDeptFilter(e.target.value)}>
          <option value="">{t("tasks.department")}: {t("common.all")}</option>
          {DEPARTMENTS.filter(Boolean).map(d => (
            <option key={d} value={d}>{t(`tasks.departments.${d}`)}</option>
          ))}
        </select>
      </div>

      {/* Task threads */}
      {isLoading ? (
        <div className="text-center text-gray-500 text-sm py-8">{t("common.loading")}</div>
      ) : tasks.length === 0 ? (
        <div className="text-center text-gray-500 text-sm py-8">{t("discussions.noDiscussions")}</div>
      ) : (
        <div className="space-y-2">
          {tasks.map(task => (
            <TaskThread key={task.id} task={task} />
          ))}
        </div>
      )}
    </div>
  );
}

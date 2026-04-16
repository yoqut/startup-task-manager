import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { UserPlus, Mail, Clock, Shield } from "lucide-react";
import { authApi } from "../../api/auth";
import useAuthStore from "../../store/authStore";
import clsx from "clsx";

const ROLE_COLORS = {
  owner:   "bg-yellow-500/15 text-yellow-400",
  admin:   "bg-red-500/15 text-red-400",
  manager: "bg-blue-500/15 text-blue-400",
  member:  "bg-gray-700 text-gray-300",
  viewer:  "bg-gray-800 text-gray-500",
};

function InviteModal({ onClose }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState({ email: "", role: "member" });

  const mutation = useMutation({
    mutationFn: authApi.inviteMember,
    onSuccess:  () => { qc.invalidateQueries(["team"]); onClose(); },
  });

  const ROLES = ["manager", "member", "viewer"];

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-sm space-y-4">
        <h3 className="font-semibold text-white">{t("team.inviteMember")}</h3>

        <div>
          <label className="label">{t("team.inviteEmail")} *</label>
          <input
            className="input"
            type="email"
            placeholder="email@example.com"
            value={form.email}
            onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
          />
        </div>

        <div>
          <label className="label">{t("team.inviteRole")}</label>
          <select
            className="input"
            value={form.role}
            onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
          >
            {ROLES.map(r => <option key={r} value={r}>{t(`team.roles.${r}`)}</option>)}
          </select>
        </div>

        {mutation.error && (
          <p className="text-xs text-red-400">{mutation.error.response?.data?.error?.message || t("common.noData")}</p>
        )}

        <div className="flex gap-2 pt-1">
          <button
            className="btn-primary flex-1 flex items-center justify-center gap-2"
            onClick={() => form.email && mutation.mutate(form)}
            disabled={!form.email || mutation.isPending}
          >
            <Mail size={15} />
            {mutation.isPending ? t("common.loading") : t("team.sendInvite")}
          </button>
          <button className="btn-secondary" onClick={onClose}>{t("common.cancel")}</button>
        </div>
      </div>
    </div>
  );
}

export default function TeamPage() {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const [showInvite, setShowInvite] = useState(false);

  const { data: members = [], isLoading } = useQuery({
    queryKey: ["team"],
    queryFn:  () => authApi.team().then(r => r.data.results ?? r.data),
  });

  const canInvite = user?.role && ["owner", "admin"].includes(user.role);

  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto space-y-4 sm:space-y-5">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-lg sm:text-xl font-bold text-white">{t("nav.team")}</h1>
        {canInvite && (
          <button
            onClick={() => setShowInvite(true)}
            className="btn-primary flex items-center gap-1.5 text-sm"
          >
            <UserPlus size={15} />
            <span className="hidden sm:inline">{t("team.inviteMember")}</span>
            <span className="sm:hidden">{t("common.create")}</span>
          </button>
        )}
      </div>

      {/* Members — table on sm+, cards on mobile */}
      <div className="card p-0 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500 text-sm">{t("common.loading")}</div>
        ) : members.length === 0 ? (
          <div className="p-8 text-center text-gray-500 text-sm">{t("team.noMembers")}</div>
        ) : (
          <>
            {/* Desktop table */}
            <div className="hidden sm:block overflow-x-auto">
              <table className="w-full text-sm min-w-[480px]">
                <thead>
                  <tr className="border-b border-gray-800">
                    <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">{t("team.member")}</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">{t("team.inviteRole")}</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">{t("tasks.department")}</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">{t("team.lastSeen")}</th>
                  </tr>
                </thead>
                <tbody>
                  {members.map(m => (
                    <tr key={m.id} className="border-b border-gray-800 last:border-0 hover:bg-gray-800/40 transition-colors">
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-brand-500/20 flex items-center justify-center text-xs font-bold text-brand-400 flex-shrink-0">
                            {m.first_name?.[0]}{m.last_name?.[0]}
                          </div>
                          <div className="min-w-0">
                            <p className="text-gray-200 font-medium truncate">
                              {m.first_name} {m.last_name}
                              {m.id === user?.id && <span className="ml-1.5 text-xs text-gray-600">({t("team.you")})</span>}
                            </p>
                            <p className="text-xs text-gray-500 truncate">{m.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={clsx("badge", ROLE_COLORS[m.role] || "bg-gray-700 text-gray-400")}>
                          {t(`team.roles.${m.role}`, m.role)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-xs">
                        {m.dept_name ?? <span className="text-gray-600">—</span>}
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-xs">
                        <div className="flex items-center gap-1.5">
                          <Clock size={11} />
                          {m.last_seen_at ? new Date(m.last_seen_at).toLocaleDateString() : "—"}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile cards */}
            <div className="sm:hidden divide-y divide-gray-800">
              {members.map(m => (
                <div key={m.id} className="flex items-center gap-3 px-4 py-3">
                  <div className="w-9 h-9 rounded-full bg-brand-500/20 flex items-center justify-center text-xs font-bold text-brand-400 flex-shrink-0">
                    {m.first_name?.[0]}{m.last_name?.[0]}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-200 font-medium truncate">
                      {m.first_name} {m.last_name}
                      {m.id === user?.id && <span className="ml-1 text-xs text-gray-600">({t("team.you")})</span>}
                    </p>
                    <p className="text-xs text-gray-500 truncate">{m.email}</p>
                    {m.dept_name && <p className="text-xs text-gray-600">{m.dept_name}</p>}
                  </div>
                  <span className={clsx("badge flex-shrink-0", ROLE_COLORS[m.role] || "bg-gray-700 text-gray-400")}>
                    {t(`team.roles.${m.role}`, m.role)}
                  </span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {showInvite && <InviteModal onClose={() => setShowInvite(false)} />}
    </div>
  );
}

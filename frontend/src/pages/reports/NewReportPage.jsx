import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Send, ArrowLeft } from "lucide-react";
import { reportsApi } from "../../api/reports";
import { authApi } from "../../api/auth";
import useAuthStore from "../../store/authStore";

export default function NewReportPage() {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [form, setForm] = useState({
    title:       "",
    body:        "",
    report_type: "daily",
    sent_to:     "",
  });
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  // Load managers/owners to send to
  const { data: team = [] } = useQuery({
    queryKey: ["team"],
    queryFn:  () => authApi.team().then(r => r.data.results ?? r.data),
  });
  const managers = team.filter(m => ["owner", "admin", "manager"].includes(m.role) && m.id !== user?.id);

  const mutation = useMutation({
    mutationFn: reportsApi.create,
    onSuccess:  () => { qc.invalidateQueries(["reports"]); navigate("/reports"); },
  });

  const handleSubmit = () => {
    if (!form.title || !form.body) return;
    mutation.mutate({
      ...form,
      sent_to: form.sent_to || null,
    });
  };

  const TYPES = ["daily", "weekly", "issue", "progress", "request"];

  return (
    <div className="p-4 sm:p-6 max-w-2xl mx-auto space-y-5">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(-1)} className="text-gray-400 hover:text-gray-200 transition-colors">
          <ArrowLeft size={20} />
        </button>
        <h1 className="text-lg sm:text-xl font-bold text-white">{t("reports.sendReport")}</h1>
      </div>

      <div className="card space-y-4">
        <div>
          <label className="label">{t("reports.reportType")}</label>
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
            {TYPES.map(tp => (
              <button
                key={tp}
                onClick={() => set("report_type", tp)}
                className={`px-3 py-2 rounded-lg text-xs font-medium transition-colors border ${
                  form.report_type === tp
                    ? "bg-brand-500/20 text-brand-400 border-brand-500/40"
                    : "bg-gray-800 text-gray-400 border-gray-700 hover:border-gray-600"
                }`}
              >
                {t(`reports.types.${tp}`)}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="label">{t("reports.titleField")} *</label>
          <input
            className="input"
            placeholder={t("reports.titleField")}
            value={form.title}
            onChange={e => set("title", e.target.value)}
          />
        </div>

        <div>
          <label className="label">{t("reports.body")} *</label>
          <textarea
            className="input resize-none h-36"
            placeholder={t("reports.bodyPlaceholder")}
            value={form.body}
            onChange={e => set("body", e.target.value)}
          />
        </div>

        <div>
          <label className="label">{t("reports.sendTo")} <span className="text-gray-600">({t("common.optional")})</span></label>
          <select className="input" value={form.sent_to} onChange={e => set("sent_to", e.target.value)}>
            <option value="">{t("reports.allManagers")}</option>
            {managers.map(m => (
              <option key={m.id} value={m.id}>{m.full_name} ({t(`team.roles.${m.role}`)})</option>
            ))}
          </select>
        </div>

        <div className="flex gap-2 pt-2">
          <button
            className="btn-primary flex items-center gap-2 flex-1"
            onClick={handleSubmit}
            disabled={!form.title || !form.body || mutation.isPending}
          >
            <Send size={15} />
            {mutation.isPending ? t("common.loading") : t("reports.sendReport")}
          </button>
          <button className="btn-secondary" onClick={() => navigate(-1)}>{t("common.cancel")}</button>
        </div>
      </div>
    </div>
  );
}

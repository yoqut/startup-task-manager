import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import useAuthStore from "../../store/authStore";

export default function RegisterPage() {
  const { t } = useTranslation();
  const { register, isLoading, error, clearError } = useAuthStore();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    company_name: "", industry: "other",
    first_name: "", last_name: "", email: "", password: "",
  });

  const set = (key, val) => { clearError(); setForm((f) => ({ ...f, [key]: val })); };

  const INDUSTRIES = [
    ["it_software", t("auth.industries.it_software")],
    ["marketing_agency", t("auth.industries.marketing_agency")],
    ["ecommerce", t("auth.industries.ecommerce")],
    ["consulting", t("auth.industries.consulting")],
    ["saas", t("auth.industries.saas")],
    ["digital_services", t("auth.industries.digital_services")],
    ["other", t("auth.industries.other")],
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    const result = await register(form);
    if (result.success) navigate("/");
  };

  return (
    <div className="card">
      <h2 className="text-lg font-semibold text-white mb-1">{t("auth.createWorkspace")}</h2>
      <p className="text-sm text-gray-400 mb-6">{t("auth.setupCompany")}</p>

      {error && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">{t("auth.firstName")}</label>
            <input className="input" value={form.first_name} onChange={(e) => set("first_name", e.target.value)} required />
          </div>
          <div>
            <label className="label">{t("auth.lastName")}</label>
            <input className="input" value={form.last_name} onChange={(e) => set("last_name", e.target.value)} required />
          </div>
        </div>
        <div>
          <label className="label">{t("auth.email")}</label>
          <input type="email" className="input" placeholder="siz@kompaniya.com" value={form.email} onChange={(e) => set("email", e.target.value)} required />
        </div>
        <div>
          <label className="label">{t("auth.password")}</label>
          <input type="password" className="input" placeholder={t("auth.atLeast8Chars")} value={form.password} onChange={(e) => set("password", e.target.value)} required minLength={8} />
        </div>
        <hr className="border-gray-800" />
        <div>
          <label className="label">{t("auth.companyName")}</label>
          <input className="input" placeholder="Acme Corp" value={form.company_name} onChange={(e) => set("company_name", e.target.value)} required />
        </div>
        <div>
          <label className="label">{t("auth.industry")}</label>
          <select className="input" value={form.industry} onChange={(e) => set("industry", e.target.value)}>
            {INDUSTRIES.map(([val, label]) => <option key={val} value={val}>{label}</option>)}
          </select>
        </div>
        <button type="submit" className="btn-primary w-full" disabled={isLoading}>
          {isLoading ? t("auth.creatingWorkspace") : t("auth.createWorkspace")}
        </button>
      </form>

      <p className="mt-5 text-center text-sm text-gray-400">
        {t("auth.alreadyHaveAccount")}{" "}
        <Link to="/login" className="text-brand-400 hover:text-brand-300 font-medium">
          {t("auth.signIn")}
        </Link>
      </p>
    </div>
  );
}

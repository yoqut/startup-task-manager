import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import useAuthStore from "../../store/authStore";

export default function LoginPage() {
  const { t } = useTranslation();
  const { login, isLoading, error, clearError } = useAuthStore();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });

  const handleSubmit = async (e) => {
    e.preventDefault();
    const result = await login(form.email, form.password);
    if (result.success) navigate("/");
  };

  return (
    <div className="card">
      <h2 className="text-lg font-semibold text-white mb-1">{t("auth.signIn")}</h2>
      <p className="text-sm text-gray-400 mb-6">{t("auth.accessWorkspace")}</p>

      {error && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="label">{t("auth.email")}</label>
          <input
            type="email"
            className="input"
            placeholder="siz@kompaniya.com"
            value={form.email}
            onChange={(e) => { clearError(); setForm({ ...form, email: e.target.value }); }}
            required
          />
        </div>
        <div>
          <label className="label">{t("auth.password")}</label>
          <input
            type="password"
            className="input"
            placeholder="••••••••"
            value={form.password}
            onChange={(e) => { clearError(); setForm({ ...form, password: e.target.value }); }}
            required
          />
        </div>
        <button type="submit" className="btn-primary w-full" disabled={isLoading}>
          {isLoading ? t("auth.signingIn") : t("auth.signIn")}
        </button>
      </form>

      <p className="mt-5 text-center text-sm text-gray-400">
        {t("auth.noAccount")}{" "}
        <Link to="/register" className="text-brand-400 hover:text-brand-300 font-medium">
          {t("auth.createWorkspace")}
        </Link>
      </p>
    </div>
  );
}

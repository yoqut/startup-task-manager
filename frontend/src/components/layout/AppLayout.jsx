import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  LayoutDashboard, CheckSquare, Bot, ShieldCheck,
  LogOut, Building2, FileText, MessageSquare, Users, Network, Hash,
  Menu, X, Zap,
} from "lucide-react";
import useAuthStore from "../../store/authStore";
import LangSwitcher from "../ui/LangSwitcher";
import clsx from "clsx";

const ROLE_BADGE = {
  owner:   "text-yellow-400",
  admin:   "text-red-400",
  manager: "text-blue-400",
  member:  "text-gray-400",
  viewer:  "text-gray-500",
};

export default function AppLayout() {
  const { t } = useTranslation();
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const role = user?.role || "member";
  const isOwnerOrAdmin   = role === "owner" || role === "admin";
  const isManagerOrAbove = isOwnerOrAdmin || role === "manager";

  const NAV = [
    { to: "/",            icon: LayoutDashboard, label: t("nav.commandCenter"), show: true },
    { to: "/tasks",       icon: CheckSquare,     label: t("nav.tasks"),         show: true },
    { to: "/discussions", icon: MessageSquare,   label: t("nav.discussions"),   show: true },
    { to: "/chat",        icon: Hash,            label: t("nav.chat"),          show: true },
    { to: "/reports",     icon: FileText,        label: t("nav.reports"),       show: true },
    { to: "/team",        icon: Users,           label: t("nav.team"),          show: true },
    { to: "/approvals",     icon: ShieldCheck, label: t("nav.approvals"),     show: isManagerOrAbove },
    { to: "/organizations", icon: Network,     label: t("nav.organizations"), show: isOwnerOrAdmin },
    { to: "/agents",        icon: Bot,         label: t("nav.aiAgents"),      show: isOwnerOrAdmin },
    { to: "/integrations",  icon: Zap,         label: t("nav.integrations"),  show: isOwnerOrAdmin },
  ].filter(n => n.show);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const closeSidebar = () => setOpen(false);

  return (
    <div className="flex h-screen overflow-hidden">

      {/* ── Mobile overlay ── */}
      {open && (
        <div
          className="fixed inset-0 bg-black/60 z-30 md:hidden"
          onClick={closeSidebar}
        />
      )}

      {/* ── Sidebar ── */}
      <aside className={clsx(
        "flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col z-40",
        // Mobile: fixed drawer that slides in/out
        "fixed inset-y-0 left-0 w-60 transition-transform duration-200 ease-in-out",
        // Desktop: always visible, part of normal flow
        "md:relative md:translate-x-0",
        open ? "translate-x-0" : "-translate-x-full md:translate-x-0",
      )}>
        {/* Logo + mobile close */}
        <div className="px-5 py-4 border-b border-gray-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-brand-500 rounded-lg flex items-center justify-center">
              <Bot size={16} className="text-white" />
            </div>
            <span className="font-semibold text-white">AIManager</span>
          </div>
          <button
            className="md:hidden p-1 text-gray-500 hover:text-gray-300"
            onClick={closeSidebar}
          >
            <X size={18} />
          </button>
        </div>

        {/* Company */}
        {user?.company_name && (
          <div className="flex items-center gap-1.5 px-5 py-2 text-xs text-gray-400 border-b border-gray-800">
            <Building2 size={11} />
            <span className="truncate">{user.company_name}</span>
          </div>
        )}

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={closeSidebar}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                  isActive
                    ? "bg-brand-500/15 text-brand-400"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
                )
              }
            >
              <Icon size={17} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Language switcher + user footer */}
        <div className="px-3 py-3 border-t border-gray-800 space-y-1">
          <div className="px-3 py-1.5">
            <LangSwitcher />
          </div>
          <div className="flex items-center gap-3 px-3 py-2 rounded-lg">
            <div className="w-7 h-7 rounded-full bg-brand-500 flex items-center justify-center text-xs font-bold text-white flex-shrink-0">
              {user?.first_name?.[0]}{user?.last_name?.[0]}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-200 truncate">
                {user?.first_name} {user?.last_name}
              </p>
              <p className={clsx("text-xs truncate capitalize", ROLE_BADGE[role])}>
                {t(`team.roles.${role}`, role)}
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-400 hover:text-red-400 rounded-lg hover:bg-gray-800 transition-colors"
          >
            <LogOut size={15} />
            {t("nav.signOut")}
          </button>
        </div>
      </aside>

      {/* ── Main content ── */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Mobile top bar */}
        <header className="md:hidden flex items-center gap-3 px-4 py-3 bg-gray-900 border-b border-gray-800 flex-shrink-0 z-20">
          <button
            onClick={() => setOpen(true)}
            className="p-1 text-gray-400 hover:text-gray-200 transition-colors"
          >
            <Menu size={20} />
          </button>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-brand-500 rounded flex items-center justify-center">
              <Bot size={12} className="text-white" />
            </div>
            <span className="font-semibold text-white text-sm">AIManager</span>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto bg-gray-950">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

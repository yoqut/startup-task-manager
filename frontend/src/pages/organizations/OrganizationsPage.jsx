import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  Plus, Pencil, Trash2, Users, X, Crown,
  Building, GitBranch, Layers, ChevronDown, ChevronRight,
} from "lucide-react";
import { organizationsApi } from "../../api/organizations";
import { authApi } from "../../api/auth";
import useAuthStore from "../../store/authStore";
import clsx from "clsx";

// ─────────────────────────────────────────────────────────────────────────────
// Unit Form Modal — creates / edits head office, branch, or department
// ─────────────────────────────────────────────────────────────────────────────
function UnitFormModal({ unit, forcedType, forcedParent, onClose }) {
  const { t } = useTranslation();
  const qc = useQueryClient();

  const [form, setForm] = useState({
    name:        unit?.name        ?? "",
    description: unit?.description ?? "",
    type:        unit?.type        ?? forcedType ?? "department",
    parent:      unit?.parent      ?? forcedParent ?? null,
  });
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const mutation = useMutation({
    mutationFn: unit
      ? (data) => organizationsApi.update(unit.id, data)
      : (data) => organizationsApi.create(data),
    onSuccess: () => { qc.invalidateQueries(["departments"]); onClose(); },
  });

  const typeLabel = t(`org.types.${form.type}`);

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-sm space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-white">
            {unit ? `${t("common.edit")}: ${unit.name}` : `${t("org.create")}: ${typeLabel}`}
          </h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300"><X size={16} /></button>
        </div>

        <div>
          <label className="label">{t("org.name")} *</label>
          <input
            className="input"
            placeholder={t("org.namePlaceholder")}
            value={form.name}
            autoFocus
            onChange={e => set("name", e.target.value)}
          />
        </div>

        <div>
          <label className="label">{t("org.description")} <span className="text-gray-600">({t("common.optional")})</span></label>
          <textarea
            className="input resize-none h-16"
            placeholder={t("org.descriptionPlaceholder")}
            value={form.description}
            onChange={e => set("description", e.target.value)}
          />
        </div>

        {mutation.error && (
          <p className="text-xs text-red-400">
            {mutation.error.response?.data?.name?.[0]
              || mutation.error.response?.data?.type?.[0]
              || t("common.noData")}
          </p>
        )}

        <div className="flex gap-2 pt-1">
          <button
            className="btn-primary flex-1"
            onClick={() => form.name.trim() && mutation.mutate({ ...form })}
            disabled={!form.name.trim() || mutation.isPending}
          >
            {mutation.isPending ? t("common.loading") : (unit ? t("common.save") : t("common.create"))}
          </button>
          <button className="btn-secondary" onClick={onClose}>{t("common.cancel")}</button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Members Modal — manage who belongs to a unit + who is the head
// ─────────────────────────────────────────────────────────────────────────────
function MembersModal({ unit, onClose }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { user } = useAuthStore();
  const isAdmin = user?.role === "owner" || user?.role === "admin";

  const { data: members = [], isLoading } = useQuery({
    queryKey: ["unit-members", unit.id],
    queryFn:  () => organizationsApi.getMembers(unit.id).then(r => r.data),
  });

  const { data: allTeam = [] } = useQuery({
    queryKey: ["team"],
    queryFn:  () => authApi.team().then(r => r.data.results ?? r.data),
  });

  const memberIds = new Set(members.map(m => m.id));
  const unassigned = allTeam.filter(m => !memberIds.has(m.id));

  const assignMut = useMutation({
    mutationFn: (uid) => organizationsApi.assignMembers(unit.id, { user_ids: [uid] }),
    onSuccess:  () => { qc.invalidateQueries(["unit-members", unit.id]); qc.invalidateQueries(["departments"]); },
  });
  const removeMut = useMutation({
    mutationFn: (uid) => organizationsApi.removeMember(unit.id, { user_id: uid }),
    onSuccess:  () => { qc.invalidateQueries(["unit-members", unit.id]); qc.invalidateQueries(["departments"]); },
  });
  const headMut = useMutation({
    mutationFn: (uid) => organizationsApi.setHead(unit.id, { user_id: uid || null }),
    onSuccess:  () => qc.invalidateQueries(["departments"]),
  });

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-md flex flex-col max-h-[80vh]">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-semibold text-white">{unit.name}</h3>
            <p className="text-xs text-gray-500">{members.length} {t("org.members")}</p>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300"><X size={16} /></button>
        </div>

        {/* Head selector */}
        {isAdmin && (
          <div className="mb-4">
            <label className="label flex items-center gap-1.5"><Crown size={11} className="text-yellow-500" />{t("org.head")}</label>
            <select
              className="input"
              value={unit.head ?? ""}
              onChange={e => headMut.mutate(e.target.value || null)}
            >
              <option value="">{t("org.noHead")}</option>
              {members.map(m => (
                <option key={m.id} value={m.id}>{m.full_name} ({t(`team.roles.${m.role}`, m.role)})</option>
              ))}
            </select>
          </div>
        )}

        {/* Current members */}
        <div className="flex-1 overflow-y-auto space-y-1 min-h-0">
          <p className="text-xs text-gray-500 font-medium uppercase tracking-wider mb-2">{t("org.currentMembers")}</p>
          {isLoading ? (
            <p className="text-sm text-gray-500 text-center py-6">{t("common.loading")}</p>
          ) : members.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-6">{t("org.noMembers")}</p>
          ) : members.map(m => (
            <div key={m.id} className="flex items-center justify-between px-3 py-2 rounded-lg bg-gray-800/50">
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-full bg-brand-500/20 flex items-center justify-center text-xs font-bold text-brand-400 flex-shrink-0">
                  {m.first_name?.[0]}{m.last_name?.[0]}
                </div>
                <div>
                  <p className="text-sm text-gray-200 leading-none">
                    {m.full_name}
                    {m.id === unit.head && <Crown size={10} className="inline ml-1 text-yellow-400" />}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">{t(`team.roles.${m.role}`, m.role)}</p>
                </div>
              </div>
              {isAdmin && (
                <button onClick={() => removeMut.mutate(m.id)} className="text-gray-600 hover:text-red-400 transition-colors p-1">
                  <X size={13} />
                </button>
              )}
            </div>
          ))}
        </div>

        {/* Add unassigned members */}
        {isAdmin && unassigned.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-800">
            <p className="text-xs text-gray-500 font-medium uppercase tracking-wider mb-2">{t("org.addMember")}</p>
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {unassigned.map(m => (
                <div key={m.id} className="flex items-center justify-between px-3 py-1.5 rounded-lg hover:bg-gray-800/40">
                  <span className="text-sm text-gray-300">{m.full_name}</span>
                  <button onClick={() => assignMut.mutate(m.id)} className="text-xs text-brand-400 hover:text-brand-300">
                    + {t("org.add")}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        <button className="btn-secondary w-full mt-4" onClick={onClose}>{t("common.close")}</button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Department Row — one dept inside a head-office or branch card
// ─────────────────────────────────────────────────────────────────────────────
function DeptRow({ dept, isAdmin, onEdit, onDelete, onMembers }) {
  const { t } = useTranslation();
  return (
    <div className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-gray-800/40 group">
      <div className="flex items-center gap-2.5">
        <Layers size={13} className="text-gray-600 flex-shrink-0" />
        <div>
          <span className="text-sm text-gray-200">{dept.name}</span>
          {dept.head_name && (
            <span className="ml-2 text-xs text-gray-500">
              <Crown size={9} className="inline text-yellow-600 mr-0.5" />{dept.head_name}
            </span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <span className="text-xs text-gray-600 mr-2 flex items-center gap-1">
          <Users size={10} />{dept.member_count ?? 0}
        </span>
        <button onClick={() => onMembers(dept)} className="p-1 text-gray-600 hover:text-brand-400 transition-colors" title={t("org.manageMembers")}>
          <Users size={13} />
        </button>
        {isAdmin && (
          <>
            <button onClick={() => onEdit(dept)} className="p-1 text-gray-600 hover:text-gray-300 transition-colors">
              <Pencil size={12} />
            </button>
            <button onClick={() => onDelete(dept)} className="p-1 text-gray-600 hover:text-red-400 transition-colors">
              <Trash2 size={12} />
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Branch Card — one branch with its departments
// ─────────────────────────────────────────────────────────────────────────────
function BranchCard({ branch, depts, isAdmin, onEdit, onDelete, onMembers, onAddDept }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(true);
  const children = depts.filter(d => d.parent === branch.id);

  return (
    <div className="border border-gray-800 rounded-xl overflow-hidden">
      {/* Branch header */}
      <div className="flex items-center gap-3 px-4 py-3 bg-gray-900/80">
        <button onClick={() => setOpen(o => !o)} className="text-gray-500 hover:text-gray-300 flex-shrink-0">
          {open ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
        </button>
        <GitBranch size={15} className="text-purple-400 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-gray-100 font-medium">{branch.name}</p>
          <p className="text-xs text-gray-500">
            {branch.head_name
              ? <><Crown size={9} className="inline text-yellow-500 mr-0.5" />{branch.head_name} · </>
              : null}
            {branch.member_count ?? 0} {t("org.members")} · {children.length} {t("org.departmentsSection").toLowerCase()}
          </p>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <button onClick={() => onMembers(branch)} className="p-1.5 text-gray-500 hover:text-brand-400 transition-colors" title={t("org.manageMembers")}>
            <Users size={14} />
          </button>
          {isAdmin && (
            <>
              <button onClick={() => onEdit(branch)} className="p-1.5 text-gray-500 hover:text-gray-300 transition-colors">
                <Pencil size={13} />
              </button>
              <button onClick={() => onDelete(branch)} className="p-1.5 text-gray-500 hover:text-red-400 transition-colors">
                <Trash2 size={13} />
              </button>
            </>
          )}
        </div>
      </div>

      {/* Departments under this branch */}
      {open && (
        <div className="border-t border-gray-800/60 px-2 py-1.5 bg-gray-900/30 space-y-0.5">
          {children.length === 0 ? (
            <p className="text-xs text-gray-600 px-3 py-1">{t("org.noDepartments")}</p>
          ) : (
            children.map(d => (
              <DeptRow
                key={d.id}
                dept={d}
                isAdmin={isAdmin}
                onEdit={onEdit}
                onDelete={onDelete}
                onMembers={onMembers}
              />
            ))
          )}
          {isAdmin && (
            <button
              onClick={() => onAddDept(branch.id)}
              className="w-full flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-600 hover:text-brand-400 transition-colors rounded"
            >
              <Plus size={11} /> {t("org.addDepartment")}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Head Office Card — singular, shows its departments
// ─────────────────────────────────────────────────────────────────────────────
function HeadOfficeCard({ hq, depts, isAdmin, onEdit, onDelete, onMembers, onAddDept }) {
  const { t } = useTranslation();

  return (
    <div className="border border-brand-500/30 rounded-xl overflow-hidden bg-brand-500/5">
      {/* HQ header */}
      <div className="flex items-center gap-3 px-4 py-3">
        <Building size={16} className="text-brand-400 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-gray-100 font-semibold">{hq.name}</p>
            <span className="badge bg-brand-500/15 text-brand-400 text-xs">{t("org.types.head_office")}</span>
          </div>
          <p className="text-xs text-gray-500">
            {hq.head_name
              ? <><Crown size={9} className="inline text-yellow-500 mr-0.5" />{hq.head_name} · </>
              : null}
            {hq.member_count ?? 0} {t("org.members")} · {depts.filter(d => d.parent === hq.id).length} {t("org.departmentsSection").toLowerCase()}
          </p>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <button onClick={() => onMembers(hq)} className="p-1.5 text-gray-500 hover:text-brand-400 transition-colors" title={t("org.manageMembers")}>
            <Users size={14} />
          </button>
          {isAdmin && (
            <button onClick={() => onEdit(hq)} className="p-1.5 text-gray-500 hover:text-gray-300 transition-colors">
              <Pencil size={13} />
            </button>
          )}
        </div>
      </div>

      {/* Departments under HQ */}
      <div className="border-t border-brand-500/20 px-2 py-1.5 space-y-0.5">
        {depts.filter(d => d.parent === hq.id).length === 0 ? (
          <p className="text-xs text-gray-600 px-3 py-1">{t("org.noDepartments")}</p>
        ) : (
          depts
            .filter(d => d.parent === hq.id)
            .map(d => (
              <DeptRow
                key={d.id}
                dept={d}
                isAdmin={isAdmin}
                onEdit={onEdit}
                onDelete={onDelete}
                onMembers={onMembers}
              />
            ))
        )}
        {isAdmin && (
          <button
            onClick={() => onAddDept(hq.id)}
            className="w-full flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-600 hover:text-brand-400 transition-colors rounded"
          >
            <Plus size={11} /> {t("org.addDepartment")}
          </button>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Page
// ─────────────────────────────────────────────────────────────────────────────
export default function OrganizationsPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { user } = useAuthStore();
  const isAdmin = user?.role === "owner" || user?.role === "admin";

  // Modal state: { type, forcedType, forcedParent, unit }
  const [modal,   setModal]   = useState(null);
  const [members, setMembers] = useState(null);   // unit whose members we're managing

  const { data: depts = [], isLoading } = useQuery({
    queryKey: ["departments"],
    queryFn:  () => organizationsApi.list().then(r => r.data.results ?? r.data),
  });

  const deleteMut = useMutation({
    mutationFn: (id) => organizationsApi.remove(id),
    onSuccess:  () => qc.invalidateQueries(["departments"]),
  });

  const headOffice = depts.find(d => d.type === "head_office");
  const branches   = depts.filter(d => d.type === "branch");
  const totalUnits = depts.length;

  const openCreate = (forcedType, forcedParent = null) =>
    setModal({ forcedType, forcedParent, unit: null });

  const handleDelete = (unit) => {
    if (window.confirm(t("org.confirmDelete", { name: unit.name }))) {
      deleteMut.mutate(unit.id);
    }
  };

  return (
    <div className="p-4 sm:p-6 max-w-3xl mx-auto space-y-6">

      {/* ── Page header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg sm:text-xl font-bold text-white">{t("org.title")}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{totalUnits} {t("org.units")}</p>
        </div>
        {isAdmin && (
          <div className="flex gap-2">
            {!headOffice && (
              <button onClick={() => openCreate("head_office")} className="btn-secondary flex items-center gap-1.5 text-sm">
                <Building size={14} /> {t("org.createHeadOffice")}
              </button>
            )}
            <button onClick={() => openCreate("branch")} className="btn-secondary flex items-center gap-1.5 text-sm">
              <GitBranch size={14} /> {t("org.addBranch")}
            </button>
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="card p-10 text-center text-gray-500 text-sm">{t("common.loading")}</div>
      ) : (
        <>
          {/* ── HEAD OFFICE ── */}
          <section>
            <p className="text-xs text-gray-500 font-semibold uppercase tracking-widest mb-3">
              {t("org.headOfficeSection")}
            </p>
            {headOffice ? (
              <HeadOfficeCard
                hq={headOffice}
                depts={depts}
                isAdmin={isAdmin}
                onEdit={(u) => setModal({ unit: u, forcedType: null, forcedParent: null })}
                onDelete={handleDelete}
                onMembers={setMembers}
                onAddDept={(parentId) => openCreate("department", parentId)}
              />
            ) : (
              <div className="border border-dashed border-gray-700 rounded-xl p-8 text-center space-y-2">
                <Building size={28} className="mx-auto text-gray-700" />
                <p className="text-gray-500 text-sm">{t("org.noHeadOffice")}</p>
                <p className="text-gray-600 text-xs">{t("org.noHeadOfficeHint")}</p>
                {isAdmin && (
                  <button onClick={() => openCreate("head_office")} className="btn-secondary mt-2 mx-auto flex items-center gap-1.5 text-sm">
                    <Plus size={13} /> {t("org.createHeadOffice")}
                  </button>
                )}
              </div>
            )}
          </section>

          {/* ── BRANCHES ── */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs text-gray-500 font-semibold uppercase tracking-widest">
                {t("org.branchesSection")} ({branches.length})
              </p>
              {isAdmin && (
                <button
                  onClick={() => openCreate("branch")}
                  className="flex items-center gap-1 text-xs text-brand-400 hover:text-brand-300 transition-colors"
                >
                  <Plus size={12} /> {t("org.addBranch")}
                </button>
              )}
            </div>

            {branches.length === 0 ? (
              <div className="border border-dashed border-gray-700 rounded-xl p-8 text-center space-y-2">
                <GitBranch size={28} className="mx-auto text-gray-700" />
                <p className="text-gray-500 text-sm">{t("org.noBranches")}</p>
                <p className="text-gray-600 text-xs">{t("org.noBranchesHint")}</p>
              </div>
            ) : (
              <div className="space-y-3">
                {branches.map(branch => (
                  <BranchCard
                    key={branch.id}
                    branch={branch}
                    depts={depts}
                    isAdmin={isAdmin}
                    onEdit={(u) => setModal({ unit: u, forcedType: null, forcedParent: null })}
                    onDelete={handleDelete}
                    onMembers={setMembers}
                    onAddDept={(parentId) => openCreate("department", parentId)}
                  />
                ))}
              </div>
            )}
          </section>
        </>
      )}

      {/* ── Modals ── */}
      {modal !== null && (
        <UnitFormModal
          unit={modal.unit}
          forcedType={modal.forcedType}
          forcedParent={modal.forcedParent}
          onClose={() => setModal(null)}
        />
      )}
      {members !== null && (
        <MembersModal unit={members} onClose={() => setMembers(null)} />
      )}
    </div>
  );
}

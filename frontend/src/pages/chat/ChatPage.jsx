import { useState, useEffect, useRef, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  Plus, X, Send, Building, GitBranch, Layers, Users, Globe,
  FileText, CheckSquare, Wifi, WifiOff, Trash2, Hash, Send as TelegramIcon,
} from "lucide-react";
import clsx from "clsx";
import { chatApi } from "../../api/chat";
import { organizationsApi } from "../../api/organizations";
import { authApi } from "../../api/auth";
import { useChatSocket } from "../../hooks/useChatSocket";
import useAuthStore from "../../store/authStore";

// ── Type icons & colors ───────────────────────────────────────────────────────
const TYPE_META = {
  company:    { Icon: Globe,    color: "text-brand-400",  bg: "bg-brand-500/15"   },
  branch:     { Icon: GitBranch,color: "text-purple-400", bg: "bg-purple-500/15"  },
  department: { Icon: Layers,   color: "text-blue-400",   bg: "bg-blue-500/15"    },
  direct:     { Icon: Users,    color: "text-green-400",  bg: "bg-green-500/15"   },
};

function RoomIcon({ type, size = 14 }) {
  const { Icon, color } = TYPE_META[type] || TYPE_META.company;
  return <Icon size={size} className={color} />;
}

// ── Create Room Modal ─────────────────────────────────────────────────────────
function CreateRoomModal({ onClose }) {
  const { t } = useTranslation();
  const qc = useQueryClient();

  const [form, setForm] = useState({
    name:             "",
    description:      "",
    type:             "company",
    org_units:        [],
    members:          [],
    related_task:     null,
    related_report:   null,
    telegram_chat_id: "",
  });
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const toggleArr = (k, id) =>
    setForm(f => ({
      ...f,
      [k]: f[k].includes(id) ? f[k].filter(x => x !== id) : [...f[k], id],
    }));

  const { data: orgUnits = [] } = useQuery({
    queryKey: ["departments"],
    queryFn:  () => organizationsApi.list().then(r => r.data.results ?? r.data),
  });
  const { data: team = [] } = useQuery({
    queryKey: ["team"],
    queryFn:  () => authApi.team().then(r => r.data.results ?? r.data),
  });
  const { user } = useAuthStore();

  const mutation = useMutation({
    mutationFn: chatApi.createRoom,
    onSuccess:  () => { qc.invalidateQueries(["chat-rooms"]); onClose(); },
  });

  const branches = orgUnits.filter(u => u.type === "branch");
  const depts    = orgUnits.filter(u => u.type === "department");
  const others   = team.filter(m => m.id !== user?.id);

  const handleSubmit = () => {
    if (!form.name.trim()) return;
    mutation.mutate({
      ...form,
      org_units: form.type === "branch" || form.type === "department" ? form.org_units : [],
      members:   form.type === "direct"                               ? form.members   : [],
    });
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-md space-y-4 max-h-[88vh] overflow-y-auto">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-white">{t("chat.createRoom")}</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300"><X size={16} /></button>
        </div>

        {/* Name */}
        <div>
          <label className="label">{t("chat.roomName")} *</label>
          <input
            className="input" autoFocus
            placeholder={t("chat.roomNamePlaceholder")}
            value={form.name}
            onChange={e => set("name", e.target.value)}
          />
        </div>

        {/* Type */}
        <div>
          <label className="label">{t("chat.roomType")}</label>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(TYPE_META).map(([tp, { Icon, color, bg }]) => (
              <button
                key={tp}
                onClick={() => set("type", tp)}
                className={clsx(
                  "flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm border transition-colors",
                  form.type === tp
                    ? `${bg} border-current ${color}`
                    : "bg-gray-800 text-gray-400 border-gray-700 hover:border-gray-600"
                )}
              >
                <Icon size={14} />
                {t(`chat.types.${tp}`)}
              </button>
            ))}
          </div>
        </div>

        {/* Branch selector */}
        {form.type === "branch" && (
          <div>
            <label className="label">{t("chat.selectBranches")}</label>
            <div className="space-y-1 max-h-36 overflow-y-auto">
              {branches.length === 0
                ? <p className="text-xs text-gray-600">{t("chat.noUnits")}</p>
                : branches.map(b => (
                  <label key={b.id} className="flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer hover:bg-gray-800/50">
                    <input
                      type="checkbox"
                      className="accent-brand-500"
                      checked={form.org_units.includes(b.id)}
                      onChange={() => toggleArr("org_units", b.id)}
                    />
                    <span className="text-sm text-gray-300">{b.name}</span>
                  </label>
                ))}
            </div>
          </div>
        )}

        {/* Department selector */}
        {form.type === "department" && (
          <div>
            <label className="label">{t("chat.selectDepts")}</label>
            <div className="space-y-1 max-h-36 overflow-y-auto">
              {depts.length === 0
                ? <p className="text-xs text-gray-600">{t("chat.noUnits")}</p>
                : depts.map(d => (
                  <label key={d.id} className="flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer hover:bg-gray-800/50">
                    <input
                      type="checkbox"
                      className="accent-brand-500"
                      checked={form.org_units.includes(d.id)}
                      onChange={() => toggleArr("org_units", d.id)}
                    />
                    <span className="text-sm text-gray-300">{d.name}</span>
                    {d.parent_name && <span className="text-xs text-gray-600">({d.parent_name})</span>}
                  </label>
                ))}
            </div>
          </div>
        )}

        {/* Direct members */}
        {form.type === "direct" && (
          <div>
            <label className="label">{t("chat.selectMembers")}</label>
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {others.map(m => (
                <label key={m.id} className="flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer hover:bg-gray-800/50">
                  <input
                    type="checkbox"
                    className="accent-brand-500"
                    checked={form.members.includes(m.id)}
                    onChange={() => toggleArr("members", m.id)}
                  />
                  <div className="w-5 h-5 rounded-full bg-brand-500/20 flex items-center justify-center text-xs font-bold text-brand-400 flex-shrink-0">
                    {m.first_name?.[0]}{m.last_name?.[0]}
                  </div>
                  <span className="text-sm text-gray-300">{m.full_name}</span>
                  <span className="text-xs text-gray-600 ml-auto">{t(`team.roles.${m.role}`, m.role)}</span>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Description */}
        <div>
          <label className="label">{t("common.optional")}: {t("org.description")}</label>
          <input
            className="input"
            placeholder="..."
            value={form.description}
            onChange={e => set("description", e.target.value)}
          />
        </div>

        {/* Telegram bridge */}
        <div>
          <label className="label flex items-center gap-1.5">
            <span className="text-blue-400">✈</span>
            {t("common.optional")}: {t("chat.telegramChatId")}
          </label>
          <input
            className="input font-mono text-sm"
            placeholder="-100123456789"
            value={form.telegram_chat_id}
            onChange={e => set("telegram_chat_id", e.target.value)}
          />
          <p className="text-xs text-gray-600 mt-1">{t("chat.telegramChatIdHint")}</p>
        </div>

        {mutation.error && (
          <p className="text-xs text-red-400">{mutation.error.response?.data?.name?.[0] || t("common.noData")}</p>
        )}

        <div className="flex gap-2 pt-1">
          <button
            className="btn-primary flex-1"
            onClick={handleSubmit}
            disabled={!form.name.trim() || mutation.isPending}
          >
            {mutation.isPending ? t("common.loading") : t("common.create")}
          </button>
          <button className="btn-secondary" onClick={onClose}>{t("common.cancel")}</button>
        </div>
      </div>
    </div>
  );
}

// ── Single message bubble ─────────────────────────────────────────────────────
function MessageBubble({ msg, isOwn }) {
  const initials = msg.author_name
    ? msg.author_name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase()
    : "?";
  const time = new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return (
    <div className={clsx("flex gap-2.5 group", isOwn && "flex-row-reverse")}>
      {/* Avatar */}
      <div className={clsx(
        "w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5",
        isOwn ? "bg-brand-500/30 text-brand-300" : "bg-gray-700 text-gray-300"
      )}>
        {initials}
      </div>

      <div className={clsx("max-w-[72%]", isOwn && "items-end flex flex-col")}>
        {/* Name + time */}
        <div className={clsx("flex items-center gap-1.5 mb-1", isOwn && "flex-row-reverse")}>
          <span className="text-xs font-medium text-gray-400">{msg.author_name}</span>
          <span className="text-xs text-gray-600">{time}</span>
        </div>

        {/* Bubble */}
        <div className={clsx(
          "px-3 py-2 rounded-2xl text-sm leading-relaxed",
          isOwn
            ? "bg-brand-500/25 text-gray-100 rounded-tr-sm"
            : "bg-gray-800 text-gray-200 rounded-tl-sm"
        )}>
          {msg.related_task && (
            <div className="flex items-center gap-1 text-xs text-blue-400 mb-1">
              <CheckSquare size={10} /> Task reference
            </div>
          )}
          {msg.related_report && (
            <div className="flex items-center gap-1 text-xs text-yellow-400 mb-1">
              <FileText size={10} /> Report reference
            </div>
          )}
          {msg.body}
        </div>
      </div>
    </div>
  );
}

// ── Room list item ────────────────────────────────────────────────────────────
function RoomItem({ room, active, onClick }) {
  const { t } = useTranslation();
  const last = room.last_message;
  return (
    <button
      onClick={onClick}
      className={clsx(
        "w-full flex items-start gap-3 px-3 py-2.5 rounded-lg text-left transition-colors",
        active ? "bg-brand-500/15" : "hover:bg-gray-800/60"
      )}
    >
      <div className={clsx("w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5",
        TYPE_META[room.type]?.bg || "bg-gray-700"
      )}>
        <RoomIcon type={room.type} size={15} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-1">
          <div className="flex items-center gap-1 min-w-0">
            <p className={clsx("text-sm font-medium truncate", active ? "text-brand-300" : "text-gray-200")}>
              {room.name}
            </p>
            {room.telegram_chat_id && (
              <span className="text-blue-400 flex-shrink-0" title="Telegram bridge">✈</span>
            )}
          </div>
          {last && (
            <span className="text-xs text-gray-600 flex-shrink-0">
              {new Date(last.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
          )}
        </div>
        {last ? (
          <p className="text-xs text-gray-500 truncate">
            <span className="text-gray-600">{last.author_name}: </span>{last.body}
          </p>
        ) : (
          <p className="text-xs text-gray-600">{t("chat.noMessages")}</p>
        )}
      </div>
    </button>
  );
}

// ── Message input ─────────────────────────────────────────────────────────────
function MessageInput({ onSend, disabled }) {
  const { t } = useTranslation();
  const [text, setText] = useState("");

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  };

  return (
    <div className="flex items-end gap-2 p-3 border-t border-gray-800">
      <textarea
        className="flex-1 input resize-none min-h-[40px] max-h-32 py-2 text-sm"
        placeholder={t("chat.inputPlaceholder")}
        value={text}
        disabled={disabled}
        onChange={e => setText(e.target.value)}
        onKeyDown={e => {
          if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
        }}
        rows={1}
      />
      <button
        onClick={handleSend}
        disabled={!text.trim() || disabled}
        className="btn-primary px-3 py-2 flex items-center gap-1.5"
      >
        <Send size={14} />
      </button>
    </div>
  );
}

// ── Active room view ──────────────────────────────────────────────────────────
function RoomView({ room, onDelete, isAdmin }) {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const qc = useQueryClient();
  const bottomRef = useRef(null);

  // Load message history — single source of truth
  const { data: messages = [] } = useQuery({
    queryKey: ["chat-messages", room.id],
    queryFn:  () => chatApi.getMessages(room.id).then(r => r.data),
    staleTime: Infinity,   // WS keeps the cache fresh; no polling needed
  });

  // When a new WS message arrives, append it directly to the query cache
  const handleMessage = useCallback((msg) => {
    qc.setQueryData(["chat-messages", room.id], (prev = []) => {
      if (prev.some(m => m.id === msg.id)) return prev;   // dedup
      return [...prev, msg];
    });
  }, [qc, room.id]);

  const { connected, send } = useChatSocket(room.id, handleMessage);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  const deleteMut = useMutation({
    mutationFn: () => chatApi.deleteRoom(room.id),
    onSuccess:  () => { qc.invalidateQueries(["chat-rooms"]); onDelete(); },
  });

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800 flex-shrink-0">
        <div className={clsx("w-8 h-8 rounded-lg flex items-center justify-center", TYPE_META[room.type]?.bg)}>
          <RoomIcon type={room.type} size={16} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-gray-100 font-semibold truncate">{room.name}</p>
          <p className="text-xs text-gray-500">
            {t(`chat.types.${room.type}`)}
            {room.org_unit_names?.length > 0 && ` · ${room.org_unit_names.join(", ")}`}
            {room.description && ` · ${room.description}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={clsx("flex items-center gap-1 text-xs", connected ? "text-green-400" : "text-gray-600")}>
            {connected ? <Wifi size={12} /> : <WifiOff size={12} />}
            {connected ? t("chat.connected") : t("chat.disconnected")}
          </span>
          {isAdmin && (
            <button
              onClick={() => { if (window.confirm(t("chat.confirmDelete", { name: room.name }))) deleteMut.mutate(); }}
              className="p-1.5 text-gray-600 hover:text-red-400 transition-colors"
            >
              <Trash2 size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-gray-600 space-y-2">
            <Hash size={32} />
            <p className="text-sm">{t("chat.noMessages")}</p>
          </div>
        ) : (
          messages.map(msg => (
            <MessageBubble
              key={msg.id}
              msg={msg}
              isOwn={msg.author_id === user?.id || msg.author === user?.id}
            />
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <MessageInput onSend={send} disabled={!connected} />
    </div>
  );
}

// ── Main ChatPage ─────────────────────────────────────────────────────────────
export default function ChatPage() {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const isManager = user?.is_manager_or_above ||
    ["owner", "admin", "manager"].includes(user?.role);
  const isAdmin = ["owner", "admin"].includes(user?.role);

  const [activeId,    setActiveId]    = useState(null);
  const [showCreate,  setShowCreate]  = useState(false);

  const { data: rooms = [], isLoading } = useQuery({
    queryKey: ["chat-rooms"],
    queryFn:  () => chatApi.listRooms().then(r => r.data.results ?? r.data),
  });

  const activeRoom = rooms.find(r => r.id === activeId) ?? null;

  // Auto-select first room
  useEffect(() => {
    if (!activeId && rooms.length > 0) setActiveId(rooms[0].id);
  }, [rooms.length]);

  // Group rooms by type for sidebar
  const grouped = {
    company:    rooms.filter(r => r.type === "company"),
    branch:     rooms.filter(r => r.type === "branch"),
    department: rooms.filter(r => r.type === "department"),
    direct:     rooms.filter(r => r.type === "direct"),
  };

  return (
    <div className="flex h-full overflow-hidden">

      {/* ── Sidebar ── */}
      <aside className="w-64 flex-shrink-0 border-r border-gray-800 flex flex-col bg-gray-900/50">
        {/* Sidebar header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
          <h2 className="font-semibold text-white text-sm">{t("nav.chat")}</h2>
          {isManager && (
            <button
              onClick={() => setShowCreate(true)}
              className="p-1 text-gray-500 hover:text-brand-400 transition-colors"
              title={t("chat.createRoom")}
            >
              <Plus size={16} />
            </button>
          )}
        </div>

        {/* Room groups */}
        <div className="flex-1 overflow-y-auto px-2 py-2 space-y-4">
          {isLoading ? (
            <p className="text-xs text-gray-500 text-center py-6">{t("common.loading")}</p>
          ) : rooms.length === 0 ? (
            <div className="text-center py-8 space-y-2">
              <Hash size={24} className="mx-auto text-gray-700" />
              <p className="text-xs text-gray-600">{t("chat.noRooms")}</p>
              {isManager && (
                <button onClick={() => setShowCreate(true)} className="text-xs text-brand-400 hover:text-brand-300">
                  + {t("chat.createRoom")}
                </button>
              )}
            </div>
          ) : (
            Object.entries(grouped).map(([type, list]) =>
              list.length === 0 ? null : (
                <div key={type}>
                  <p className="flex items-center gap-1.5 px-3 py-1 text-xs text-gray-600 font-semibold uppercase tracking-wider">
                    <RoomIcon type={type} size={11} />
                    {t(`chat.types.${type}`)}
                  </p>
                  {list.map(room => (
                    <RoomItem
                      key={room.id}
                      room={room}
                      active={room.id === activeId}
                      onClick={() => setActiveId(room.id)}
                    />
                  ))}
                </div>
              )
            )
          )}
        </div>
      </aside>

      {/* ── Main area ── */}
      <main className="flex-1 overflow-hidden">
        {activeRoom ? (
          <RoomView
            key={activeRoom.id}
            room={activeRoom}
            isAdmin={isAdmin}
            onDelete={() => setActiveId(null)}
          />
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-gray-600 space-y-3">
            <Hash size={40} />
            <p className="text-sm">{t("chat.selectRoom")}</p>
            {isManager && (
              <button onClick={() => setShowCreate(true)} className="btn-secondary flex items-center gap-2">
                <Plus size={14} /> {t("chat.createRoom")}
              </button>
            )}
          </div>
        )}
      </main>

      {showCreate && <CreateRoomModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}

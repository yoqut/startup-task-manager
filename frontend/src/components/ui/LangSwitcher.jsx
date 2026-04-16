import { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { ChevronDown } from "lucide-react";
import clsx from "clsx";

const LANGS = [
  { code: "uz",      label: "O'zbekcha",  flag: "🇺🇿", script: "Lotin"  },
  { code: "uz_cyrl", label: "Ўзбекча",    flag: "🇺🇿", script: "Кирил"  },
  { code: "ru",      label: "Русский",    flag: "🇷🇺", script: null      },
  { code: "en",      label: "English",    flag: "🇬🇧", script: null      },
];

export default function LangSwitcher() {
  const { i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const current = LANGS.find((l) => l.code === (i18n.language?.split("-")[0] === "uz" && !i18n.language?.includes("cyrl")
    ? "uz"
    : i18n.language)) ?? LANGS[0];

  // close on outside click
  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const select = (code) => {
    i18n.changeLanguage(code);
    setOpen(false);
  };

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs font-medium text-gray-400 hover:text-gray-200 hover:bg-gray-800 transition-colors w-full"
      >
        <span>{current.flag}</span>
        <span className="flex-1 text-left">
          {current.label}
          {current.script && <span className="text-gray-600 ml-1">({current.script})</span>}
        </span>
        <ChevronDown size={11} className={clsx("transition-transform", open && "rotate-180")} />
      </button>

      {open && (
        <div className="absolute bottom-full left-0 mb-1 w-44 bg-gray-900 border border-gray-800 rounded-xl shadow-xl overflow-hidden z-50">
          {LANGS.map((lang) => (
            <button
              key={lang.code}
              onClick={() => select(lang.code)}
              className={clsx(
                "flex items-center gap-2 w-full px-3 py-2 text-xs transition-colors text-left",
                lang.code === current.code
                  ? "bg-brand-500/15 text-brand-400"
                  : "text-gray-400 hover:bg-gray-800 hover:text-gray-200"
              )}
            >
              <span>{lang.flag}</span>
              <span>
                {lang.label}
                {lang.script && <span className="text-gray-600 ml-1">({lang.script})</span>}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

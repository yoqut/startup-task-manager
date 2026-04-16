import { useState, useRef, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Mic, MicOff, X, CheckCircle, Loader } from "lucide-react";
import clsx from "clsx";

// Map i18n language codes → Speech Recognition BCP-47 codes
const SPEECH_LANG = {
  uz:      "uz-UZ",
  uz_cyrl: "uz-UZ",
  ru:      "ru-RU",
  en:      "en-US",
};

const SpeechRecognition =
  typeof window !== "undefined"
    ? window.SpeechRecognition || window.webkitSpeechRecognition
    : null;

/**
 * VoiceTaskButton — microphone button that opens a voice-capture overlay.
 * Props:
 *   onConfirm(title: string) — called when user taps the tick button
 */
export default function VoiceTaskButton({ onConfirm }) {
  const { t, i18n } = useTranslation();
  const [phase, setPhase] = useState("idle"); // idle | listening | result | error
  const [transcript, setTranscript] = useState("");
  const [editedTitle, setEditedTitle] = useState("");
  const recognitionRef = useRef(null);

  const isSupported = Boolean(SpeechRecognition);

  const startListening = useCallback(() => {
    if (!isSupported) {
      setPhase("error");
      return;
    }

    const langCode = i18n.language?.split("-")[0];
    const speechLang = SPEECH_LANG[langCode] || SPEECH_LANG[i18n.language] || "uz-UZ";

    const rec = new SpeechRecognition();
    rec.lang = speechLang;
    rec.continuous = false;
    rec.interimResults = true;
    rec.maxAlternatives = 1;

    recognitionRef.current = rec;

    rec.onstart = () => setPhase("listening");

    rec.onresult = (e) => {
      const text = Array.from(e.results)
        .map((r) => r[0].transcript)
        .join(" ")
        .trim();
      setTranscript(text);
      setEditedTitle(text);
    };

    rec.onerror = () => {
      setPhase("error");
      setTranscript("");
    };

    rec.onend = () => {
      setPhase((prev) => (prev === "listening" ? "result" : prev));
    };

    setPhase("listening");
    setTranscript("");
    setEditedTitle("");
    rec.start();
  }, [i18n.language, isSupported]);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  const reset = useCallback(() => {
    recognitionRef.current?.abort();
    setPhase("idle");
    setTranscript("");
    setEditedTitle("");
  }, []);

  const confirm = () => {
    const title = editedTitle.trim();
    if (!title) return;
    onConfirm(title);
    reset();
  };

  // ── Overlay (listening / result / error) ─────────────────────────────────
  const showOverlay = phase !== "idle";

  return (
    <>
      {/* Mic trigger button */}
      <button
        onClick={isSupported ? startListening : () => setPhase("error")}
        disabled={phase === "listening"}
        title={t("tasks.voiceTask")}
        className={clsx(
          "flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium border transition-colors",
          phase === "listening"
            ? "bg-red-500/20 border-red-500/40 text-red-400 animate-pulse"
            : "bg-gray-800 border-gray-700 text-gray-400 hover:text-gray-200 hover:bg-gray-700"
        )}
      >
        {phase === "listening" ? <MicOff size={15} /> : <Mic size={15} />}
        <span className="hidden sm:inline">
          {phase === "listening" ? t("tasks.voiceListening") : t("tasks.voiceTask")}
        </span>
      </button>

      {/* Overlay modal */}
      {showOverlay && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="card w-full max-w-sm space-y-5">
            {/* Header */}
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-white text-sm">{t("tasks.voiceTask")}</h3>
              <button onClick={reset} className="text-gray-500 hover:text-gray-300">
                <X size={16} />
              </button>
            </div>

            {/* Listening state */}
            {phase === "listening" && (
              <div className="flex flex-col items-center py-6 gap-4">
                {/* Animated pulse rings */}
                <div className="relative flex items-center justify-center">
                  <span className="absolute w-20 h-20 rounded-full bg-red-500/20 animate-ping" />
                  <span className="absolute w-14 h-14 rounded-full bg-red-500/20 animate-ping [animation-delay:150ms]" />
                  <button
                    onClick={stopListening}
                    className="relative w-12 h-12 rounded-full bg-red-500 flex items-center justify-center shadow-lg hover:bg-red-600 transition-colors"
                  >
                    <MicOff size={20} className="text-white" />
                  </button>
                </div>
                <p className="text-sm text-gray-400">{t("tasks.voiceListening")}</p>
                <p className="text-xs text-gray-600">{t("tasks.voiceHint")}</p>
                {transcript && (
                  <p className="text-sm text-gray-300 text-center italic">"{transcript}"</p>
                )}
              </div>
            )}

            {/* Result / confirm state */}
            {phase === "result" && (
              <div className="space-y-4">
                <div>
                  <label className="label">{t("tasks.voiceTranscript")}</label>
                  <input
                    className="input"
                    value={editedTitle}
                    onChange={(e) => setEditedTitle(e.target.value)}
                    autoFocus
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    className="flex-1 flex items-center justify-center gap-2 py-2 bg-brand-500/20 text-brand-400 rounded-lg text-sm font-medium hover:bg-brand-500/30 transition-colors"
                    onClick={confirm}
                    disabled={!editedTitle.trim()}
                  >
                    <CheckCircle size={15} />
                    {t("tasks.voiceConfirm")}
                  </button>
                  <button
                    className="px-3 py-2 bg-gray-800 text-gray-400 rounded-lg text-sm hover:bg-gray-700 transition-colors"
                    onClick={startListening}
                    title={t("tasks.voiceTask")}
                  >
                    <Mic size={15} />
                  </button>
                </div>
              </div>
            )}

            {/* Error state */}
            {phase === "error" && (
              <div className="flex flex-col items-center py-4 gap-3 text-center">
                <MicOff size={28} className="text-red-400" />
                <p className="text-sm text-gray-400">
                  {isSupported ? t("tasks.voiceError") : t("tasks.voiceNotSupported")}
                </p>
                {isSupported && (
                  <button
                    className="btn-primary text-sm"
                    onClick={startListening}
                  >
                    {t("tasks.voiceTask")}
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}

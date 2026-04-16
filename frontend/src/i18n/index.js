import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import uz      from "./uz";
import en      from "./en";
import ru      from "./ru";
import uz_cyrl from "./uz_cyrl";

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      uz:      uz,
      en:      en,
      ru:      ru,
      uz_cyrl: uz_cyrl,
    },
    fallbackLng: "uz",
    defaultNS: "translation",
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
      lookupLocalStorage: "aimanager_lang",
    },
    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;

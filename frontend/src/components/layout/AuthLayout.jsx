import { Outlet } from "react-router-dom";
import { Bot } from "lucide-react";
import LangSwitcher from "../ui/LangSwitcher";

export default function AuthLayout() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-950 px-4">
      <div className="absolute top-4 right-4">
        <LangSwitcher />
      </div>
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-brand-500 rounded-2xl mb-4">
            <Bot size={24} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">AIManager</h1>
          <p className="text-gray-400 text-sm mt-1">AI-powered company operations platform</p>
        </div>
        <Outlet />
      </div>
    </div>
  );
}

"use client";

import { useState } from "react";
import { X } from "lucide-react";
import type { Project } from "@/lib/types";
import { api } from "@/lib/api";

interface ProjectSettingsProps {
  project: Project;
  onClose: () => void;
  onUpdate: (p: Project) => void;
}

export function ProjectSettings({ project, onClose, onUpdate }: ProjectSettingsProps) {
  const [confluenceUrl, setConfluenceUrl] = useState("");
  const [confluenceToken, setConfluenceToken] = useState("");
  const [spaceKeys, setSpaceKeys] = useState("");
  const [allowLlm, setAllowLlm] = useState(project.allow_external_llm);
  const [message, setMessage] = useState("");

  const saveProject = async () => {
    const updated = await api<Project>(`/projects/${project.id}`, {
      method: "PATCH",
      body: JSON.stringify({ allow_external_llm: allowLlm }),
    });
    onUpdate(updated);
    setMessage("Настройки сохранены");
  };

  const connectConfluence = async () => {
    await api(`/projects/${project.id}/confluence`, {
      method: "POST",
      body: JSON.stringify({
        base_url: confluenceUrl,
        api_token: confluenceToken,
        space_keys: spaceKeys.split(",").map((s) => s.trim()).filter(Boolean),
      }),
    });
    setMessage("Confluence подключён, синхронизация запущена");
  };

  const syncConfluence = async () => {
    const bindings = await api<{ id: string }[]>(`/projects/${project.id}/confluence`);
    if (bindings[0]) {
      await api(`/projects/${project.id}/confluence/${bindings[0].id}/sync`, { method: "POST" });
      setMessage("Синхронизация запущена");
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="w-full max-w-lg bg-quazar-panel rounded-2xl border border-quazar-border p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold">Настройки: {project.name}</h2>
          <button onClick={onClose} className="p-1 hover:bg-quazar-border rounded">
            <X size={20} />
          </button>
        </div>

        {message && <p className="text-sm text-green-400 mb-4">{message}</p>}

        <section className="mb-6">
          <h3 className="text-sm font-medium mb-2">Политика данных</h3>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={allowLlm}
              onChange={(e) => setAllowLlm(e.target.checked)}
            />
            Разрешить отправку данных во внешние LLM
          </label>
          <button
            onClick={saveProject}
            className="mt-3 px-4 py-1.5 text-sm rounded-lg bg-quazar-accent hover:bg-quazar-accentHover"
          >
            Сохранить
          </button>
        </section>

        <section>
          <h3 className="text-sm font-medium mb-2">Confluence</h3>
          <input
            placeholder="https://confluence.company.com"
            value={confluenceUrl}
            onChange={(e) => setConfluenceUrl(e.target.value)}
            className="w-full mb-2 px-3 py-2 rounded-lg bg-quazar-bg border border-quazar-border text-sm"
          />
          <input
            placeholder="API Token"
            type="password"
            value={confluenceToken}
            onChange={(e) => setConfluenceToken(e.target.value)}
            className="w-full mb-2 px-3 py-2 rounded-lg bg-quazar-bg border border-quazar-border text-sm"
          />
          <input
            placeholder="Space keys (DEV, HR)"
            value={spaceKeys}
            onChange={(e) => setSpaceKeys(e.target.value)}
            className="w-full mb-3 px-3 py-2 rounded-lg bg-quazar-bg border border-quazar-border text-sm"
          />
          <div className="flex gap-2">
            <button
              onClick={connectConfluence}
              className="px-4 py-1.5 text-sm rounded-lg bg-quazar-accent hover:bg-quazar-accentHover"
            >
              Подключить
            </button>
            <button
              onClick={syncConfluence}
              className="px-4 py-1.5 text-sm rounded-lg border border-quazar-border hover:bg-quazar-border/30"
            >
              Синхронизировать
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}

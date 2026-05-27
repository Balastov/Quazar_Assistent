"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/Sidebar";
import { ChatArea } from "@/components/ChatArea";
import { ProjectSettings } from "@/components/ProjectSettings";
import { api, getToken, clearTokens } from "@/lib/api";
import type { Chat, Folder, LlmModel, Project } from "@/lib/types";

export default function HomePage() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [chats, setChats] = useState<Chat[]>([]);
  const [selectedChat, setSelectedChat] = useState<Chat | null>(null);
  const [models, setModels] = useState<LlmModel[]>([]);
  const [showSettings, setShowSettings] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadProjects = useCallback(async () => {
    const data = await api<Project[]>("/projects");
    setProjects(data);
    if (data.length && !selectedProject) {
      setSelectedProject(data[0]);
    }
  }, [selectedProject]);

  const loadProjectData = useCallback(async (projectId: string) => {
    const [folderTree, chatList] = await Promise.all([
      api<Folder[]>(`/projects/${projectId}/folders/tree`),
      api<Chat[]>(`/projects/${projectId}/chats`),
    ]);
    setFolders(folderTree);
    setChats(chatList);
    if (chatList.length && !selectedChat) {
      setSelectedChat(chatList[0]);
    }
  }, [selectedChat]);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    Promise.all([loadProjects(), api<LlmModel[]>("/llm/models")])
      .then(([, modelData]) => setModels(modelData))
      .catch(() => {
        clearTokens();
        router.push("/login");
      })
      .finally(() => setLoading(false));
  }, [router, loadProjects]);

  useEffect(() => {
    if (selectedProject) {
      loadProjectData(selectedProject.id);
    }
  }, [selectedProject, loadProjectData]);

  const handleNewChat = async () => {
    if (!selectedProject) return;
    const chat = await api<Chat>(`/projects/${selectedProject.id}/chats`, {
      method: "POST",
      body: JSON.stringify({
        project_id: selectedProject.id,
        title: "Новый чат",
        model_id: models[0]?.id || "gpt-4o-mini",
      }),
    });
    setChats((c) => [chat, ...c]);
    setSelectedChat(chat);
  };

  const handleNewProject = async () => {
    const name = prompt("Название проекта:");
    if (!name) return;
    const project = await api<Project>("/projects", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    setProjects((p) => [project, ...p]);
    setSelectedProject(project);
  };

  const handleModelChange = async (modelId: string) => {
    if (!selectedChat) return;
    const updated = await api<Chat>(`/chats/${selectedChat.id}`, {
      method: "PATCH",
      body: JSON.stringify({ model_id: modelId }),
    });
    setSelectedChat(updated);
    setChats((cs) => cs.map((c) => (c.id === updated.id ? updated : c)));
  };

  const handleSearchScopeChange = async (scope: string) => {
    if (!selectedChat) return;
    const updated = await api<Chat>(`/chats/${selectedChat.id}`, {
      method: "PATCH",
      body: JSON.stringify({ search_scope: scope }),
    });
    setSelectedChat(updated);
  };

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-quazar-bg">
        <p className="text-quazar-muted">Загрузка...</p>
      </div>
    );
  }

  return (
    <div className="h-screen flex bg-quazar-bg">
      <Sidebar
        projects={projects}
        selectedProject={selectedProject}
        onSelectProject={(p) => {
          setSelectedProject(p);
          setSelectedChat(null);
        }}
        folders={folders}
        chats={chats}
        selectedChat={selectedChat}
        onSelectChat={setSelectedChat}
        onNewChat={handleNewChat}
        onNewProject={handleNewProject}
        onOpenSettings={() => setShowSettings(true)}
      />
      <ChatArea
        chatId={selectedChat?.id ?? null}
        projectId={selectedProject?.id ?? null}
        modelId={selectedChat?.model_id || models[0]?.id || "gpt-4o-mini"}
        onModelChange={handleModelChange}
        models={models}
        searchScope={selectedChat?.search_scope || selectedProject?.search_scope || "files_only"}
        onSearchScopeChange={handleSearchScopeChange}
      />
      {showSettings && selectedProject && (
        <ProjectSettings
          project={selectedProject}
          onClose={() => setShowSettings(false)}
          onUpdate={(p) => {
            setSelectedProject(p);
            setProjects((ps) => ps.map((x) => (x.id === p.id ? p : x)));
          }}
        />
      )}
    </div>
  );
}

"use client";

import {
  ChevronDown,
  ChevronRight,
  Folder,
  FolderOpen,
  MessageSquare,
  Plus,
  Settings,
} from "lucide-react";
import { useState } from "react";
import clsx from "clsx";
import type { Chat, Folder as FolderType, Project } from "@/lib/types";

interface SidebarProps {
  projects: Project[];
  selectedProject: Project | null;
  onSelectProject: (p: Project) => void;
  folders: FolderType[];
  chats: Chat[];
  selectedChat: Chat | null;
  onSelectChat: (c: Chat) => void;
  onNewChat: () => void;
  onNewProject: () => void;
  onOpenSettings: () => void;
}

function FolderTree({
  folders,
  level = 0,
}: {
  folders: FolderType[];
  level?: number;
}) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  return (
    <ul className="space-y-0.5">
      {folders.map((folder) => {
        const hasChildren = folder.children && folder.children.length > 0;
        const isOpen = expanded[folder.id];
        return (
          <li key={folder.id}>
            <button
              onClick={() => hasChildren && setExpanded((e) => ({ ...e, [folder.id]: !e[folder.id] }))}
              className="flex items-center gap-1 w-full px-2 py-1 text-sm text-quazar-muted hover:text-quazar-text hover:bg-quazar-border/30 rounded"
              style={{ paddingLeft: `${level * 12 + 8}px` }}
            >
              {hasChildren ? (
                isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />
              ) : (
                <span className="w-3.5" />
              )}
              {isOpen ? <FolderOpen size={14} /> : <Folder size={14} />}
              <span className="truncate">{folder.name}</span>
            </button>
            {hasChildren && isOpen && (
              <FolderTree folders={folder.children!} level={level + 1} />
            )}
          </li>
        );
      })}
    </ul>
  );
}

export function Sidebar({
  projects,
  selectedProject,
  onSelectProject,
  folders,
  chats,
  selectedChat,
  onSelectChat,
  onNewChat,
  onNewProject,
  onOpenSettings,
}: SidebarProps) {
  const [projectsOpen, setProjectsOpen] = useState(true);

  return (
    <aside className="w-72 flex flex-col border-r border-quazar-border bg-quazar-panel h-full">
      <div className="p-4 border-b border-quazar-border">
        <h1 className="text-lg font-bold text-quazar-accent">Quazar</h1>
        <p className="text-xs text-quazar-muted">Assistent</p>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        <div className="flex items-center gap-1 w-full px-2 py-1.5 text-sm font-medium">
          <button onClick={() => setProjectsOpen(!projectsOpen)} className="flex items-center gap-1">
            {projectsOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            Проекты
          </button>
          <button
            onClick={onNewProject}
            className="ml-auto p-1 hover:bg-quazar-border rounded"
          >
            <Plus size={14} />
          </button>
        </div>

        {projectsOpen && (
          <ul className="mb-4">
            {projects.map((p) => (
              <li key={p.id}>
                <button
                  onClick={() => onSelectProject(p)}
                  className={clsx(
                    "w-full text-left px-3 py-1.5 rounded-lg text-sm truncate",
                    selectedProject?.id === p.id
                      ? "bg-quazar-accent/20 text-quazar-accent"
                      : "hover:bg-quazar-border/30"
                  )}
                >
                  {p.name}
                </button>
              </li>
            ))}
          </ul>
        )}

        {selectedProject && (
          <>
            <p className="px-2 py-1 text-xs text-quazar-muted uppercase">Папки</p>
            <FolderTree folders={folders} />

            <div className="mt-4 flex items-center justify-between px-2">
              <p className="text-xs text-quazar-muted uppercase">Чаты</p>
              <button onClick={onNewChat} className="p-1 hover:bg-quazar-border rounded">
                <Plus size={14} />
              </button>
            </div>
            <ul className="mt-1 space-y-0.5">
              {chats.map((chat) => (
                <li key={chat.id}>
                  <button
                    onClick={() => onSelectChat(chat)}
                    className={clsx(
                      "flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm truncate",
                      selectedChat?.id === chat.id
                        ? "bg-quazar-accent/20 text-quazar-accent"
                        : "hover:bg-quazar-border/30"
                    )}
                  >
                    <MessageSquare size={14} />
                    {chat.title}
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>

      <div className="p-2 border-t border-quazar-border">
        <button
          onClick={onOpenSettings}
          className="flex items-center gap-2 w-full px-3 py-2 text-sm rounded-lg hover:bg-quazar-border/30"
        >
          <Settings size={16} />
          Настройки проекта
        </button>
      </div>
    </aside>
  );
}

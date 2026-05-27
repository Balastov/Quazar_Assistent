"use client";

import { useEffect, useRef, useState } from "react";
import { Paperclip, Send, Square } from "lucide-react";
import clsx from "clsx";
import type { Citation, Message } from "@/lib/types";
import { api } from "@/lib/api";
import { streamChat } from "@/lib/api";

interface ChatAreaProps {
  chatId: string | null;
  projectId: string | null;
  modelId: string;
  onModelChange: (id: string) => void;
  models: { id: string; display_name: string }[];
  searchScope: string;
  onSearchScopeChange: (scope: string) => void;
}

export function ChatArea({
  chatId,
  projectId,
  modelId,
  onModelChange,
  models,
  searchScope,
  onSearchScopeChange,
}: ChatAreaProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chatId) {
      setMessages([]);
      return;
    }
    api<Message[]>(`/chats/${chatId}/messages`).then(setMessages).catch(console.error);
  }, [chatId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  const handleSend = async () => {
    if (!chatId || !input.trim() || streaming) return;
    const userContent = input.trim();
    setInput("");
    setMessages((m) => [...m, { id: "temp", role: "user", content: userContent }]);
    setStreaming(true);
    setStreamingContent("");

    let full = "";
    try {
      await streamChat(
        chatId,
        userContent,
        (token) => {
          full += token;
          setStreamingContent(full);
        },
        () => {
          setMessages((m) => [
            ...m.filter((x) => x.id !== "temp"),
            { id: "temp-user", role: "user", content: userContent },
            { id: "temp-assistant", role: "assistant", content: full },
          ]);
          setStreamingContent("");
          api<Message[]>(`/chats/${chatId}/messages`).then(setMessages);
        }
      );
    } catch (e) {
      console.error(e);
    } finally {
      setStreaming(false);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!projectId || !e.target.files?.[0]) return;
    const form = new FormData();
    form.append("file", e.target.files[0]);
    await api(`/projects/${projectId}/documents/upload`, { method: "POST", body: form });
    e.target.value = "";
  };

  if (!chatId) {
    return (
      <div className="flex-1 flex items-center justify-center text-quazar-muted">
        <p>Выберите или создайте чат</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-w-0">
      <header className="flex items-center gap-3 px-4 py-3 border-b border-quazar-border bg-quazar-panel/50">
        <select
          value={modelId}
          onChange={(e) => onModelChange(e.target.value)}
          className="px-3 py-1.5 rounded-lg bg-quazar-bg border border-quazar-border text-sm"
        >
          {models.map((m) => (
            <option key={m.id} value={m.id}>{m.display_name}</option>
          ))}
        </select>
        <select
          value={searchScope}
          onChange={(e) => onSearchScopeChange(e.target.value)}
          className="px-3 py-1.5 rounded-lg bg-quazar-bg border border-quazar-border text-sm"
        >
          <option value="files_only">Только файлы</option>
          <option value="confluence_only">Только Confluence</option>
          <option value="files_and_confluence">Файлы + Confluence</option>
        </select>
      </header>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {streaming && streamingContent && (
          <MessageBubble message={{ id: "stream", role: "assistant", content: streamingContent }} />
        )}
        <div ref={bottomRef} />
      </div>

      <div className="p-4 border-t border-quazar-border">
        <div className="flex items-end gap-2 max-w-4xl mx-auto">
          <label className="p-2 cursor-pointer hover:bg-quazar-border/30 rounded-lg">
            <Paperclip size={20} className="text-quazar-muted" />
            <input type="file" className="hidden" onChange={handleUpload} />
          </label>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Задайте вопрос..."
            rows={1}
            className="flex-1 px-4 py-3 rounded-xl bg-quazar-panel border border-quazar-border resize-none focus:outline-none focus:border-quazar-accent"
          />
          <button
            onClick={handleSend}
            disabled={streaming || !input.trim()}
            className="p-3 rounded-xl bg-quazar-accent hover:bg-quazar-accentHover disabled:opacity-50"
          >
            {streaming ? <Square size={20} /> : <Send size={20} />}
          </button>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <div className={clsx("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={clsx(
          "max-w-[80%] px-4 py-3 rounded-2xl text-sm whitespace-pre-wrap",
          isUser
            ? "bg-quazar-accent text-white rounded-br-md"
            : "bg-quazar-panel border border-quazar-border rounded-bl-md"
        )}
      >
        {message.content}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-3 pt-3 border-t border-quazar-border/50 space-y-1">
            <p className="text-xs text-quazar-muted font-medium">Источники:</p>
            {message.citations.map((c: Citation, i: number) => (
              <p key={i} className="text-xs text-quazar-muted">
                [{i + 1}] {c.document_name}
                {c.url && (
                  <a href={c.url} target="_blank" rel="noopener noreferrer" className="text-quazar-accent ml-1">
                    ↗
                  </a>
                )}
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

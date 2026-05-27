export type SearchScope = "files_only" | "confluence_only" | "files_and_confluence";

export interface User {
  id: string;
  email: string;
  full_name: string;
  organization_id: string;
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  search_scope: SearchScope;
  allow_external_llm: boolean;
}

export interface Folder {
  id: string;
  project_id: string;
  parent_id: string | null;
  name: string;
  path_materialized: string;
  children?: Folder[];
}

export interface Chat {
  id: string;
  project_id: string;
  title: string;
  model_id: string;
  search_scope: SearchScope | null;
  mode: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations?: Citation[];
}

export interface Citation {
  chunk_id: string;
  document_name: string;
  source_type: string;
  excerpt: string;
  page?: number;
  url?: string;
}

export interface LlmModel {
  id: string;
  provider: string;
  display_name: string;
  context_window: number;
}

export interface Document {
  id: string;
  name: string;
  index_status: string;
  size_bytes: number;
}

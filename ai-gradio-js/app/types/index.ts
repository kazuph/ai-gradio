import type { INTEGRATED_MODELS } from "../constants/models";

export type ModelType = typeof INTEGRATED_MODELS[number];

export type PromptType = "text" | "webapp" | "excalidraw" | "graphviz" | "mermaid";

export interface GenerationRequest {
  query: string;
  selectedModels: ModelType[];
  systemPrompt: string;
  promptType: PromptType;
  usePlanning: boolean;
}

export interface GenerationResponse {
  results: LLMResponse[];
  plan?: string;
}

export interface LLMResponse {
  model: string;
  output: string;
  error?: string;
  startTime?: number;
  endTime?: number;
}

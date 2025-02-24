import { INTEGRATED_MODELS } from "../constants/models";

export type ModelType = typeof INTEGRATED_MODELS[number];

export type PromptType = "text" | "webapp";

export interface GenerationRequest {
  query: string;
  selectedModels: ModelType[];
  systemPrompt: string;
  promptType: PromptType;
  usePlanning: boolean;
}

export interface GenerationResponse {
  results: {
    model: ModelType;
    output: string;
    error?: string;
    startTime?: number;
    endTime?: number;
  }[];
  plan?: string;
}

export interface LLMResponse {
  content: string;
  error?: string;
}

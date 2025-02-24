export type ModelType = string;
export type PromptType = 'text' | 'webapp';

export interface LLMResponse {
  model: string;
  output: string;
  error?: string;
  startTime?: number;
  endTime?: number;
}

export interface GenerationRequest {
  query: string;
  selectedModels: ModelType[];
  systemPrompt: string;
  promptType: PromptType;
  usePlanning: boolean;
  env: { OPENAI_API_KEY: string; ANTHROPIC_API_KEY: string; GEMINI_API_KEY: string; };
}

export interface GenerationResponse {
  results: LLMResponse[];
  plan?: string;
}

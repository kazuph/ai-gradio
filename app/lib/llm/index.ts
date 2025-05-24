import { generateOpenAI } from "./openai";
import { generateAnthropic } from "./anthropic";
import { generateGemini } from "./gemini";
import { generateDeepSeek } from "./deepseek";
import type { GenerationRequest, GenerationResponse, LLMResponse, ModelType } from "../../types";
import { DEFAULT_TEXT_SYSTEM_PROMPT } from "../../constants/models";

async function getImplementationPlan(query: string, env: Env): Promise<string> {
  try {
    const response = await generateOpenAI(
      query,
      "openai:o3-mini",
      DEFAULT_TEXT_SYSTEM_PROMPT,
      env,
    );
    return response.output;
  } catch (error) {
    console.error("Error getting implementation plan:", error);
    return "";
  }
}

async function generateForModel(
  model: ModelType,
  query: string,
  systemPrompt: string,
  env: Env,
) {
  const provider = model.split(":")[0];
  try {
    switch (provider) {
      case "openai":
        return await generateOpenAI(query, model, systemPrompt, env);
      case "anthropic":
        return await generateAnthropic(query, model, systemPrompt, env);
      case "gemini":
        return await generateGemini(query, model, systemPrompt, env);
      case "deepseek":
        return await generateDeepSeek(query, model, systemPrompt, env);
      default:
        throw new Error(`Unsupported provider: ${provider}`);
    }
  } catch (error) {
    return {
      model: model,
      output: "",
      error: error instanceof Error ? error.message : "Unknown error occurred",
    };
  }
}

export async function generate({
  query,
  selectedModels,
  systemPrompt,
  promptType,
  usePlanning,
  env,
}: GenerationRequest): Promise<GenerationResponse> {
  let plan = "";
  if (usePlanning) {
    plan = await getImplementationPlan(query, env);
  }

  // 各モデルの生成を開始し、結果を格納する配列
  const results: LLMResponse[] = [];
  
  // 各モデルの生成を開始
  const modelPromises = selectedModels.map(async (model) => {
    const startTime = Date.now();
    try {
      console.log(`Generating with ${model}...`);
      const response = await generateForModel(model, query, systemPrompt, env);
      const result = {
        model,
        output: response.output,
        error: response.error,
        startTime,
        endTime: Date.now(),
      };
      console.log(`Response from ${model}:`, result);
      return result;
    } catch (error) {
      const errorResult = {
        model,
        output: "",
        error: error instanceof Error ? error.message : 'Unknown error',
        startTime,
        endTime: Date.now(),
      };
      console.error(`Error from ${model}:`, errorResult);
      return errorResult;
    }
  });

  // すべてのモデルの結果を待つ
  const allResults = await Promise.all(modelPromises);
  
  return {
    results: allResults,
    plan: plan || undefined,
  };
}

import OpenAI from "openai";
import { LLMResponse } from "../../types";

export async function generateOpenAI(
  query: string,
  model: string,
  systemPrompt: string,
  env: Env,
): Promise<LLMResponse> {
  try {
    const client = new OpenAI({
      apiKey: env.OPENAI_API_KEY,
    });

    // -highサフィックスを処理
    const isHighMode = model.includes("-high");
    const modelName = model.replace("openai:", "").replace("-high", "");
    
    const baseParams: OpenAI.ChatCompletionCreateParams = {
      model: modelName,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: query },
      ],
    };

    // o3/o4-mini系モデルの場合はtemperatureを含めない
    const isMiniModel = modelName.includes("o3") || modelName.includes("o4-mini");
    let params = isMiniModel
      ? baseParams
      : { ...baseParams, temperature: 0.7 };

    // -highモードの場合はreasoning_effortを追加（o3/o4-mini系のみ）
    if (isHighMode && isMiniModel) {
      params = {
        ...params,
        reasoning_effort: "high" as const,
      };
    }

    const response = await client.chat.completions.create(params);

    return {
      model: modelName,
      output: response.choices[0]?.message?.content || "",
    };
  } catch (error) {
    const modelName = model.replace("openai:", "").replace("-high", "");
    return {
      model: modelName,
      output: "",
      error: error instanceof Error ? error.message : "Unknown error occurred",
    };
  }
}

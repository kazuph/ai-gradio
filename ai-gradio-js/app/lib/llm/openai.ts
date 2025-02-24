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

    const modelName = model.replace("openai:", "");
    const baseParams = {
      model: modelName,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: query },
      ],
    };

    // O3モデルの場合はtemperatureを含めない
    const params = modelName.includes("o3") 
      ? baseParams
      : { ...baseParams, temperature: 0.7 };

    const response = await client.chat.completions.create(params);

    return {
      model: modelName,
      output: response.choices[0]?.message?.content || "",
    };
  } catch (error) {
    const modelName = model.replace("openai:", "");
    return {
      model: modelName,
      output: "",
      error: error instanceof Error ? error.message : "Unknown error occurred",
    };
  }
}

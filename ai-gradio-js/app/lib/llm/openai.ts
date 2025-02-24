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

    const response = await client.chat.completions.create({
      model: model.replace("openai:", ""),
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: query },
      ],
      temperature: 0.7,
    });

    const modelName = model.replace("openai:", "");
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

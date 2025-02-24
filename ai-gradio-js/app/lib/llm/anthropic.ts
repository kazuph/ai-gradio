import Anthropic from "@anthropic-ai/sdk";
import { LLMResponse } from "../../types";

export async function generateAnthropic(
  query: string,
  model: string,
  systemPrompt: string,
  env: Env,
): Promise<LLMResponse> {
  try {
    const client = new Anthropic({
      apiKey: env.ANTHROPIC_API_KEY,
    });

    const response = await client.messages.create({
      model: model.replace("anthropic:", ""),
      messages: [
        { role: "user", content: `${systemPrompt}\n\n${query}` },
      ],
      max_tokens: 4096,
    });

    const modelName = model.replace("anthropic:", "");
    return {
      model: modelName,
      output: response.content[0]?.text || "",
    };
  } catch (error) {
    const modelName = model.replace("anthropic:", "");
    return {
      model: modelName,
      output: "",
      error: error instanceof Error ? error.message : "Unknown error occurred",
    };
  }
}

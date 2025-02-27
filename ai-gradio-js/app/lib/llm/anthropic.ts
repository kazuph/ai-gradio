import Anthropic from "@anthropic-ai/sdk";
import type { LLMResponse } from "../../types";

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

    // モデル名から-thinkingを削除
    const actualModel = model.replace("anthropic:", "").replace("-thinking", "");
    // 拡張思考が有効かどうか
    const useThinking = model.includes("-thinking");

    console.log(`Anthropic API Request - Model: ${actualModel}`, {
      systemPrompt,
      query,
      useThinking,
    });

    const response = await client.messages.create({
      model: actualModel,
      messages: [
        { role: "user", content: `${systemPrompt}\n\n${query}` },
      ],
      max_tokens: useThinking ? 4096 * 2 : 4096,
      ...(useThinking ? {
        thinking: {
          type: "enabled",
          budget_tokens: 4096
        }
      } : {})
    });

    console.log(`Anthropic API Response - Model: ${actualModel}`, {
      contentLength: response.content.length,
      contentTypes: response.content.map(c => c.type),
    });

    // レスポンスの内容を詳細にログ出力
    response.content.forEach((content, index) => {
      if (content.type === 'text') {
        console.log(`Content ${index} (text):`, content.text);
      } else if (content.type === 'thinking') {
        console.log(`Content ${index} (thinking): [thinking content available]`);
        // thinkingコンテンツの構造をログに出力
        console.log(`Thinking content structure:`, Object.keys(content));
      } else if (content.type === 'redacted_thinking') {
        console.log(`Content ${index} (redacted_thinking): [redacted thinking content]`);
      } else {
        console.log(`Content ${index} (${content.type}):`, content);
      }
    });

    // テキストコンテンツを抽出
    const textContent = response.content.find(c => c.type === 'text') as { type: 'text', text: string } | undefined;
    // 思考コンテンツを抽出
    const thinkingContent = response.content.find(c => c.type === 'thinking');

    const modelName = model.replace("anthropic:", "");
    
    // テキストコンテンツがある場合はそれを返す
    // なければ思考コンテンツを返す（あれば）
    // どちらもなければ空文字を返す
    let output = "";
    if (textContent?.text) {
      output = textContent.text;
    } else if (thinkingContent) {
      // thinkingコンテンツの構造に応じて適切に処理
      const thinkingText = typeof thinkingContent === 'object' && thinkingContent !== null
        ? JSON.stringify(thinkingContent)
        : String(thinkingContent);
      output = `<thinking>\n${thinkingText}\n</thinking>`;
    }
    
    return {
      model: modelName,
      output: output,
    };
  } catch (error) {
    console.error('Anthropic API Error:', error);
    const modelName = model.replace("anthropic:", "");
    return {
      model: modelName,
      output: "",
      error: error instanceof Error ? error.message : "Unknown error occurred",
    };
  }
}

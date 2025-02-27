import Anthropic from "@anthropic-ai/sdk";
import type { LLMResponse } from "../../types";

export async function generateAnthropic(
  query: string,
  model: string,
  systemPrompt: string,
  env: Env,
): Promise<LLMResponse> {
  const originalModelName = model.replace("anthropic:", "");
  const isThinkingModel = originalModelName.includes("-thinking");
  const modelName = isThinkingModel 
    ? originalModelName.replace("-thinking", "") 
    : originalModelName;
  
  const maxRetries = 3;
  let retries = 0;
  
  while (retries < maxRetries) {
    try {
      const client = new Anthropic({
        apiKey: env.ANTHROPIC_API_KEY,
        timeout: 120000, // タイムアウトを120秒に設定（Thinkingモードは処理に時間がかかる可能性があるため）
      });

      // リクエストオプションを設定
      const requestOptions: any = {
        model: modelName,
        max_tokens: 4096,
        messages: [
          { role: "user", content: query },
        ],
      };

      // システムプロンプトが提供されている場合は追加
      if (systemPrompt) {
        requestOptions.system = systemPrompt;
      }

      // Thinkingモデルの場合、thinking関連のパラメータを追加
      if (isThinkingModel) {
        requestOptions.thinking = {
          type: "enabled",
          budget_tokens: 16000, // 推論プロセスに使用するトークンの最大数
        };
      }
      
      // ストリーミングを有効化
      const stream = await client.messages.stream(requestOptions);
      
      let fullContent = '';
      let thinkingContent = '';
      
      // ストリーミングモードでの処理
      for await (const event of stream) {
        // any型を使用して型エラーを回避
        const typedEvent = event as any;
        
        if (typedEvent.type === 'content_block_start') {
          console.log(`Starting ${typedEvent.content_block?.type} block...`);
        } else if (typedEvent.type === 'content_block_delta') {
          if (typedEvent.delta?.type === 'thinking_delta' && typedEvent.delta?.thinking) {
            thinkingContent += typedEvent.delta.thinking;
          } else if (typedEvent.delta?.type === 'text_delta' && typedEvent.delta?.text) {
            fullContent += typedEvent.delta.text;
          } else if (typedEvent.delta?.text) {
            // 通常のテキストデルタの場合
            if (typedEvent.content_block?.type === 'thinking') {
              thinkingContent += typedEvent.delta.text;
            } else {
              fullContent += typedEvent.delta.text;
            }
          }
        } else if (typedEvent.type === 'content_block_stop') {
          console.log('Block complete.');
        }
      }
      
      console.log("Processing complete. Thinking content length:", thinkingContent.length);
      console.log("Text content length:", fullContent.length);
      
      // Thinkingモデルの場合、思考プロセスと最終回答を組み合わせる
      if (isThinkingModel && thinkingContent) {
        return {
          model: originalModelName,
          output: `<thinking>\n${thinkingContent}\n</thinking>\n\n${fullContent}`,
        };
      }
      
      return {
        model: originalModelName,
        output: fullContent,
      };
    } catch (error) {
      retries++;
      if (retries >= maxRetries) {
        return {
          model: modelName,
          output: "",
          error: error instanceof Error 
            ? `${error.message} (after ${maxRetries} retries)` 
            : `Unknown error occurred (after ${maxRetries} retries)`,
        };
      }
      
      // エクスポネンシャルバックオフを実装
      const waitTime = Math.min(1000 * 2 ** retries, 10000);
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }
  }
  
  return {
    model: modelName,
    output: "",
    error: "Maximum retries exceeded",
  };
}

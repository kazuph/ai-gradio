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
      console.log("Anthropic API リクエスト開始 - モデル:", modelName);
      
      const client = new Anthropic({
        apiKey: env.ANTHROPIC_API_KEY,
        timeout: 180000, // タイムアウトを3分に延長
      });

      // リクエストオプションを設定
      const requestOptions: Anthropic.MessageCreateParams = {
        model: modelName,
        max_tokens: isThinkingModel ? 36000 : 20000,
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
          budget_tokens: 16000, // 思考プロセスに使用するトークンの最大数
        };
      }
      
      console.log("Anthropic API Request - パラメータ:", {
        model: modelName,
        isThinkingModel,
      });
      
      // ストリーミングを有効化
      const stream = await client.messages.stream(requestOptions);
      
      let fullContent = '';
      let thinkingContent = '';
      
      try {
        // ストリーミングモードでの処理
        for await (const event of stream) {
          try {
            // 型エラーを回避
            const typedEvent = event as {
              type: string;
              content_block?: { type?: string };
              delta?: {
                type?: string;
                thinking?: string;
                text?: string;
              };
            };
            
            if (typedEvent.type === 'content_block_start') {
              console.log("ブロック開始:", typedEvent.content_block?.type);
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
              console.log('ブロック完了');
            } else if (typedEvent.type === 'message_stop') {
              console.log('メッセージ完了');
            }
          } catch (innerError) {
            console.error('ストリーミングイベント処理エラー:', innerError);
          }
        }
      } catch (streamError) {
        console.error('ストリーミング処理エラー:', streamError);
        throw streamError;
      }
      
      console.log("処理完了. 思考コンテンツ長さ:", thinkingContent.length);
      console.log("テキストコンテンツ長さ:", fullContent.length);
      
      // Thinkingモデルの場合、思考プロセスと最終回答を組み合わせる
      if (isThinkingModel && thinkingContent) {
        // 出力処理の改善: Claudeは様々な形式の出力を返すため、柔軟に対応
        let cleanedContent = fullContent;
        let extractedContent = false;
        
        // 1. <html>タグがある場合、その内容のみを抽出（タグを含む）
        const htmlMatch = fullContent.match(/<html>[\s\S]*?<\/html>/);
        if (htmlMatch?.[0]) {
          cleanedContent = htmlMatch[0];
          extractedContent = true;
          console.log("HTMLタグを検出しました");
        } 
        
        // 2. コードブロックの処理
        if (!extractedContent) {
          const codeBlockRegex = /```[\s\S]*?```/g;
          const codeBlocks = fullContent.match(codeBlockRegex);
          
          if (codeBlocks && codeBlocks.length > 0) {
            // コードブロックが1つ以上ある場合
            const firstCodeBlock = codeBlocks[0];
            const startIndex = fullContent.indexOf(firstCodeBlock);
            const endIndex = startIndex + firstCodeBlock.length;
            
            // コードブロックの前後の余分なテキストを削除
            cleanedContent = fullContent.substring(startIndex, endIndex);
            extractedContent = true;
            console.log("コードブロックを検出しました");
          }
        }
        
        // 3. 特定のパターンが見つからない場合は、fullContentをそのまま使用
        if (!extractedContent) {
          console.log("特定のパターンが見つからないため、全文を使用します");
          cleanedContent = fullContent;
        }
        
        console.log("最終的な処理済みコンテンツ長さ:", cleanedContent.length);
        
        return {
          model: originalModelName,
          // デバッグが必要な場合はコメントを解除
          // output: `<thinking>\n${thinkingContent}\n</thinking>\n\n${fullContent}`,
          output: cleanedContent,
        };
      }
      
      return {
        model: originalModelName,
        output: fullContent,
      };
    } catch (error) {
      console.error('Anthropic API エラー:', error);
      retries++;
      if (retries >= maxRetries) {
        return {
          model: originalModelName,
          output: "",
          error: error instanceof Error 
            ? `${error.message} (${maxRetries}回リトライ後)` 
            : `不明なエラーが発生しました (${maxRetries}回リトライ後)`,
        };
      }
      
      // エクスポネンシャルバックオフを実装
      const waitTime = Math.min(1000 * 2 ** retries, 10000);
      console.log(`${waitTime}ms後にリトライします... (試行 ${retries}/${maxRetries})`);
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }
  }
  
  return {
    model: originalModelName,
    output: "",
    error: "最大リトライ回数を超えました",
  };
}


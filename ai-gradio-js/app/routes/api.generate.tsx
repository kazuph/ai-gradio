import type { ActionFunctionArgs, LoaderFunctionArgs } from 'react-router';
import { generateGemini } from '../lib/llm/gemini';
import { generateOpenAI } from '../lib/llm/openai';
import { generateAnthropic } from '../lib/llm/anthropic';
import { DEFAULT_TEXT_SYSTEM_PROMPT } from '../constants/models';
import type { GenerationRequest, GenerationResponse, LLMResponse, ModelType, PromptType } from '../types';

// アクティブなSSE接続を保持するためのマップ
// キー: クライアントID、値: コントローラー
const activeStreams = new Map<string, ReadableStreamDefaultController>();

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

// 指定されたクライアントIDのストリームにイベントを送信する関数
function sendEventToStream(clientId: string, eventType: string, data: Record<string, unknown>) {
  const controller = activeStreams.get(clientId);
  if (controller) {
    try {
      const event = `data: ${JSON.stringify({ type: eventType, ...data })}\n\n`;
      controller.enqueue(new TextEncoder().encode(event));
      return true;
    } catch (error) {
      console.error(`Error sending event to stream ${clientId}:`, error);
      return false;
    }
  }
  return false;
}

export async function action({ request, context }: ActionFunctionArgs) {
  // リクエストがPOSTメソッドかチェック
  if (request.method !== 'POST') {
    return new Response('Method Not Allowed', { status: 405 });
  }

  try {
    // フォームデータを取得
    const formData = await request.formData();
    const data: GenerationRequest = {
      query: formData.get('query') as string,
      selectedModels: JSON.parse(formData.get('selectedModels') as string),
      systemPrompt: formData.get('systemPrompt') as string,
      promptType: formData.get('promptType') as PromptType,
      usePlanning: formData.get('usePlanning') === 'true',
      env: context.cloudflare.env,
    };

    // クライアントIDを取得（URLパラメータまたはヘッダーから）
    const clientId = formData.get('clientId') as string;
    
    if (!clientId || !activeStreams.has(clientId)) {
      return new Response(JSON.stringify({ 
        error: 'No active SSE connection found for this client ID' 
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // 非同期で処理を開始（レスポンスを待たずに返す）
    (async () => {
      try {
        // プランニングが有効な場合は実行
        let plan = "";
        if (data.usePlanning) {
          plan = await getImplementationPlan(data.query, data.env);
          // プランをクライアントに送信
          sendEventToStream(clientId, 'plan', { plan });
        }

        // 各モデルの生成を並列で開始し、結果が得られ次第送信
        const modelPromises = data.selectedModels.map(async (model) => {
          const startTime = Date.now();
          try {
            console.log(`Generating with ${model}...`);
            const response = await generateForModel(model, data.query, data.systemPrompt, data.env);
            const result: LLMResponse = {
              model,
              output: response.output,
              error: response.error,
              startTime,
              endTime: Date.now(),
            };
            console.log(`Response from ${model}:`, result);
            
            // 結果をクライアントに送信
            sendEventToStream(clientId, 'result', { result });
            
            return result;
          } catch (error) {
            const errorResult: LLMResponse = {
              model,
              output: "",
              error: error instanceof Error ? error.message : 'Unknown error',
              startTime,
              endTime: Date.now(),
            };
            console.error(`Error from ${model}:`, errorResult);
            
            // エラー結果をクライアントに送信
            sendEventToStream(clientId, 'result', { result: errorResult });
            
            return errorResult;
          }
        });

        // すべてのモデルの処理が完了したことを通知
        await Promise.all(modelPromises);
        sendEventToStream(clientId, 'complete', {});
      } catch (error) {
        console.error('Stream error:', error);
        sendEventToStream(clientId, 'error', { 
          error: error instanceof Error ? error.message : 'Unknown error' 
        });
      }
    })();

    // 処理開始の確認を即座に返す
    return new Response(JSON.stringify({ status: 'processing' }), {
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Generation error:', error);
    return new Response(JSON.stringify({
      error: error instanceof Error ? error.message : 'Failed to generate response'
    }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

// GETリクエストを処理するloaderハンドラを追加
export async function loader({ request, context }: LoaderFunctionArgs) {
  // SSEのリクエストはGETメソッドで来るため、ここで処理
  if (request.method === 'GET') {
    // クエリパラメータを取得
    const url = new URL(request.url);
    // ユニークなクライアントIDを生成または取得
    const clientId = url.searchParams.get('clientId') || `client-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    
    // SSEのレスポンスを作成
    const stream = new ReadableStream({
      start(controller) {
        // コントローラーをアクティブストリームに保存
        activeStreams.set(clientId, controller);
        
        // 接続確立メッセージを送信
        const connectEvent = `data: ${JSON.stringify({ type: 'connected', clientId })}\n\n`;
        controller.enqueue(new TextEncoder().encode(connectEvent));
        
        // クライアントが切断したときにストリームをクリーンアップ
        request.signal.addEventListener('abort', () => {
          activeStreams.delete(clientId);
          controller.close();
        });
      },
      cancel() {
        // ストリームがキャンセルされたときにクリーンアップ
        activeStreams.delete(clientId);
      }
    });

    // SSEレスポンスを返す
    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
      },
    });
  }

  // GETメソッド以外は405エラー
  return new Response('Method Not Allowed', { status: 405 });
} 
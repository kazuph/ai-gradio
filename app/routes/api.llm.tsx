import type { ActionFunctionArgs } from 'react-router';
import { generateGemini } from '../lib/llm/gemini';
import { DEFAULT_TEXT_SYSTEM_PROMPT } from '../constants/models';

// コードブロックを除去する関数
function removeCodeBlock(text: string): string {
  // ```json や ``` で囲まれたブロックから中身だけを抽出
  const pattern = /```(?:json)?\n?(.*?)\n?```/s;
  const match = pattern.exec(text);
  if (match) {
    return match[1].trim();
  }
  return text.trim();
}

interface LLMRequestBody {
  prompt: string;
  format_type?: 'text' | 'json';
}

export async function action({ request, context }: ActionFunctionArgs) {
  // リクエストがPOSTメソッドかチェック
  if (request.method !== 'POST') {
    return new Response('Method Not Allowed', { status: 405 });
  }

  try {
    // リクエストボディをJSONとしてパース
    const requestData = await request.json() as LLMRequestBody;
    const { prompt, format_type = 'text' } = requestData;

    // promptが提供されていることを確認
    if (!prompt || typeof prompt !== 'string') {
      return new Response(JSON.stringify({ error: 'Prompt is required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // リファラーをチェックしてセキュリティを確保
    const referer = request.headers.get('referer');
    const origin = request.headers.get('origin');
    
    // 同一オリジンからのリクエストとsrcdoc（オリジンがnull）からのリクエストを許可
    const url = new URL(request.url);
    const requestHost = url.host;
    
    let isAllowed = false;
    
    // srcdocからのリクエスト（オリジンがnull）を許可
    if (origin === 'null') {
      isAllowed = true;
    }
    
    if (referer) {
      const refererUrl = new URL(referer);
      isAllowed = isAllowed || refererUrl.host === requestHost;
    }
    
    if (origin && origin !== 'null') {
      const originUrl = new URL(origin);
      isAllowed = isAllowed || originUrl.host === requestHost;
    }
    
    if (!isAllowed) {
      return new Response(JSON.stringify({ error: 'Forbidden: Cross-origin request denied' }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // デフォルトモデルでLLM呼び出し
    const defaultModel = "gemini:gemini-2.0-flash";
    const response = await generateGemini(
      prompt,
      defaultModel,
      DEFAULT_TEXT_SYSTEM_PROMPT,
      context.cloudflare.env,
      format_type
    );

    // レスポンステキストからコードブロックを除去
    const cleanedOutput = removeCodeBlock(response.output);

    // format_typeに応じてレスポンス形式を変更
    if (format_type === 'json') {
      try {
        // JSONモードの場合は、応答をJSONとしてパースして返す
        const jsonResponse = JSON.parse(cleanedOutput);
        return new Response(JSON.stringify(jsonResponse), {
          headers: { 
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
          }
        });
      } catch (e) {
        console.error('JSON parse error:', e, 'Raw output:', cleanedOutput);
        
        // JSONパースに失敗した場合は、テキストとして返す
        return new Response(JSON.stringify({ 
          error: 'Response could not be parsed as JSON',
          text: cleanedOutput,
          format_type: 'text'
        }), {
          status: 200, // エラーではなく成功として返す
          headers: { 
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
          }
        });
      }
    } else {
      // テキストモードの場合は、そのまま平文で返す
      return new Response(cleanedOutput, {
        headers: { 
          'Content-Type': 'text/plain',
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type'
        }
      });
    }
  } catch (error) {
    console.error('LLM API Error:', error);
    return new Response(JSON.stringify({ 
      error: error instanceof Error ? error.message : 'Unknown error occurred' 
    }), {
      status: 500,
      headers: { 
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
      }
    });
  }
}

// OPTIONSリクエスト（プリフライトリクエスト）に対応
export function loader({ request }: { request: Request }) {
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
      }
    });
  }
  
  return new Response('Method Not Allowed', { status: 405 });
} 
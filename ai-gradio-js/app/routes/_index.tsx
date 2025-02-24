import { useState, useEffect } from 'react';
import { useFetcher, type ActionFunctionArgs, type MetaFunction } from 'react-router';
import { ModelSelector } from '../components/ModelSelector';
import { QueryInput } from '../components/QueryInput';
import { ResultDisplay } from '../components/ResultDisplay';
import { DEFAULT_TEXT_SYSTEM_PROMPT, DEFAULT_WEBAPP_SYSTEM_PROMPT } from '../constants/models';
import type { GenerationRequest, GenerationResponse, LLMResponse, ModelType, PromptType } from '../types';

import { generate } from '../lib/llm';

export const meta: MetaFunction = () => {
  return [
    { title: 'AI Gradio JS' },
    { name: 'description', content: 'AI Gradio ported to React and Cloudflare Workers' },
  ];
};

// SSEイベントを処理するための関数
function handleSSEEvents(eventSource: EventSource, callbacks: {
  onPlan?: (plan: string) => void;
  onResult?: (result: LLMResponse) => void;
  onComplete?: () => void;
  onError?: (error: string) => void;
  onConnected?: (receivedClientId: string) => void;
}) {
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'connected':
          console.log('SSE connection established');
          callbacks.onConnected?.(data.clientId);
          break;
        case 'plan':
          callbacks.onPlan?.(data.plan);
          break;
        case 'result':
          callbacks.onResult?.(data.result);
          break;
        case 'complete':
          callbacks.onComplete?.();
          break;
        case 'error':
          callbacks.onError?.(data.error);
          break;
        default:
          console.warn('Unknown event type:', data.type);
      }
    } catch (error) {
      console.error('Error parsing SSE event:', error);
    }
  };

  eventSource.onerror = (error) => {
    console.error('SSE connection error:', error);
    
    // 接続が確立される前にエラーが発生した場合は、再試行せずにエラーを通知
    if (eventSource.readyState === EventSource.CONNECTING) {
      callbacks.onError?.('接続の確立に失敗しました。サーバーが応答していません。');
      eventSource.close();
    } 
    // 接続が確立された後にエラーが発生した場合は、自動的に再接続を試みる
    else if (eventSource.readyState === EventSource.OPEN) {
      console.log('接続が一時的に切断されました。再接続を試みています...');
    }
    // 接続が閉じられた場合
    else if (eventSource.readyState === EventSource.CLOSED) {
      callbacks.onError?.('Connection error');
      eventSource.close();
    }
  };

  return eventSource;
}

export async function action({ request, context }: ActionFunctionArgs) {
  const formData = await request.formData();
  const data: GenerationRequest = {
    query: formData.get('query') as string,
    selectedModels: JSON.parse(formData.get('selectedModels') as string),
    systemPrompt: formData.get('systemPrompt') as string,
    promptType: formData.get('promptType') as PromptType,
    usePlanning: formData.get('usePlanning') === 'true',
    env: context.cloudflare.env,
  };
  
  try {
    console.log('Generating with data:', data);
    const response = await generate(data);
    return new Response(JSON.stringify(response), {
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Generation error:', error);
    return new Response(JSON.stringify({
      results: [{
        model: 'error',
        output: '',
        error: error instanceof Error ? error.message : 'Failed to generate response'
      }]
    }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

export default function Index() {
  const [query, setQuery] = useState('make todo app');
  const [selectedModels, setSelectedModels] = useState<ModelType[]>(['gemini:gemini-2.0-flash']);
  const [promptType, setPromptType] = useState<PromptType>('webapp');
  const [usePlanning, setUsePlanning] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [allResponses, setAllResponses] = useState<LLMResponse[]>([]);
  const [currentPlan, setCurrentPlan] = useState<string | undefined>(undefined);
  const [systemPrompt, setSystemPrompt] = useState(DEFAULT_TEXT_SYSTEM_PROMPT);
  const [showSystemPrompt, setShowSystemPrompt] = useState(false);
  const [eventSource, setEventSource] = useState<EventSource | null>(null);
  const [clientId, setClientId] = useState<string | null>(null);

  useEffect(() => {
    setSystemPrompt(
      promptType === 'text' ? DEFAULT_TEXT_SYSTEM_PROMPT : DEFAULT_WEBAPP_SYSTEM_PROMPT
    );
  }, [promptType]);

  // コンポーネントがアンマウントされたときにSSE接続を閉じる
  useEffect(() => {
    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [eventSource]);

  const fetcher = useFetcher<typeof action>();
  
  useEffect(() => {
    if (fetcher.data) {
      // 新しいレスポンスを既存のレスポンスに追加
      const responseData = fetcher.data as unknown as GenerationResponse;
      setAllResponses(prev => [...prev, ...responseData.results]);
      // 新しいプランがあれば更新
      if (responseData.plan) {
        setCurrentPlan(responseData.plan);
      }
    }
  }, [fetcher.data]);

  useEffect(() => {
    setIsLoading(fetcher.state !== 'idle');
  }, [fetcher.state]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    
    // 既存のSSE接続を閉じる
    if (eventSource) {
      eventSource.close();
    }
    
    // 状態をリセット
    setIsLoading(true);
    setAllResponses([]);
    setCurrentPlan(undefined);
    setClientId(null);
    
    // フォームデータの準備
    const formData = new FormData();
    formData.append('selectedModels', JSON.stringify(selectedModels));
    formData.append('systemPrompt', systemPrompt);
    formData.append('promptType', promptType);
    formData.append('usePlanning', String(usePlanning));
    formData.append('query', query);
    
    try {
      // SSE接続を開始
      const es = new EventSource(`/api/generate?${new URLSearchParams({
        timestamp: Date.now().toString() // キャッシュ防止
      })}`);
      
      // SSEイベントハンドラを設定
      handleSSEEvents(es, {
        onPlan: (plan) => {
          setCurrentPlan(plan);
        },
        onResult: (result) => {
          setAllResponses(prev => [...prev, result]);
        },
        onComplete: () => {
          setIsLoading(false);
          es.close();
        },
        onError: (error) => {
          console.error('SSE error:', error);
          setIsLoading(false);
          es.close();
          // エラーメッセージを表示
          setAllResponses(prev => [...prev, {
            model: 'error',
            output: '',
            error: error,
            startTime: Date.now(),
            endTime: Date.now()
          }]);
        },
        onConnected: (receivedClientId) => {
          console.log('SSE connection established with client ID:', receivedClientId);
          setClientId(receivedClientId);
          
          // クライアントIDを取得したら、POSTリクエストを送信
          const updatedFormData = new FormData();
          updatedFormData.append('selectedModels', JSON.stringify(selectedModels));
          updatedFormData.append('systemPrompt', systemPrompt);
          updatedFormData.append('promptType', promptType);
          updatedFormData.append('usePlanning', String(usePlanning));
          updatedFormData.append('query', query);
          updatedFormData.append('clientId', receivedClientId);
          
          // SSE接続が確立された後にPOSTリクエストを送信
          fetch('/api/generate', {
            method: 'POST',
            body: updatedFormData,
          }).catch(error => {
            console.error('Fetch error:', error);
            if (es) es.close();
            setIsLoading(false);
            // エラーメッセージを表示
            setAllResponses(prev => [...prev, {
              model: 'error',
              output: '',
              error: error instanceof Error ? error.message : 'Failed to generate response',
              startTime: Date.now(),
              endTime: Date.now()
            }]);
          });
        }
      });
      
      setEventSource(es);
      
      // POSTリクエストをSSE接続確立後に送信するため、ここでは送信しない
    } catch (error) {
      console.error('Error setting up SSE:', error);
      setIsLoading(false);
      // エラーメッセージを表示
      setAllResponses(prev => [...prev, {
        model: 'error',
        output: '',
        error: error instanceof Error ? error.message : 'Failed to set up SSE connection',
        startTime: Date.now(),
        endTime: Date.now()
      }]);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left Sidebar */}
      <div className="w-[400px] min-w-[400px] border-r border-[var(--color-border)] p-4 overflow-y-auto">
        <div className="space-y-6">
          <div className="space-y-4">
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">AI Gradio JS</h1>
              <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
                Generate responses using multiple LLM models in parallel
              </p>
            </div>

            {/* Query Input at the top */}
            <fetcher.Form method="post" onSubmit={handleSubmit}>
              <input type="hidden" name="selectedModels" value={JSON.stringify(selectedModels)} />
              <input type="hidden" name="systemPrompt" value={systemPrompt} />
              <input type="hidden" name="promptType" value={promptType} />
              <input type="hidden" name="usePlanning" value={String(usePlanning)} />
              <QueryInput
                query={query}
                onChange={setQuery}
                isLoading={isLoading}
              />
            </fetcher.Form>

            <div className="flex space-x-4">
              <label className="inline-flex items-center">
                <input
                  type="radio"
                  value="text"
                  checked={promptType === 'text'}
                  onChange={(e) => setPromptType(e.target.value as PromptType)}
                  className="form-radio h-4 w-4 text-[var(--color-accent)]"
                />
                <span className="ml-2">Text Generation</span>
              </label>
              <label className="inline-flex items-center">
                <input
                  type="radio"
                  value="webapp"
                  checked={promptType === 'webapp'}
                  onChange={(e) => setPromptType(e.target.value as PromptType)}
                  className="form-radio h-4 w-4 text-[var(--color-accent)]"
                />
                <span className="ml-2">Web App Generation</span>
              </label>
            </div>

            {/* Toggleable System Prompt - Moved up */}
            <div className="space-y-2">
              <button
                type="button"
                onClick={() => setShowSystemPrompt(!showSystemPrompt)}
                className="flex items-center text-sm font-medium text-[var(--color-text-primary)]"
              >
                <span>System Prompt</span>
                <span className="ml-2">{showSystemPrompt ? '▼' : '▶'}</span>
              </button>
              {showSystemPrompt && (
                <textarea
                  id="systemPrompt"
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  className="input-field w-full min-h-[100px]"
                  placeholder="Enter system prompt..."
                />
              )}
            </div>

            <label className="inline-flex items-center">
              <input
                type="checkbox"
                checked={usePlanning}
                onChange={(e) => setUsePlanning(e.target.checked)}
                className="form-checkbox h-4 w-4 text-indigo-600"
              />
              <span className="ml-2">Use Planning</span>
            </label>

            <ModelSelector
              selectedModels={selectedModels}
              onChange={setSelectedModels}
            />
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 p-4 overflow-y-auto">
        {(isLoading || allResponses.length > 0) && (
          <div className="max-w-[1200px] mx-auto">
            {isLoading && <div className="text-center">Generating...</div>}
            <ResultDisplay responses={allResponses} plan={currentPlan} />
          </div>
        )}
      </div>
    </div>
  );
}

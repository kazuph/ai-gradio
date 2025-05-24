import { useState, useEffect, useCallback } from 'react';
import { useFetcher, type ActionFunctionArgs, type MetaFunction } from 'react-router';
import { ModelSelector } from '../components/ModelSelector';
import { QueryInput } from '../components/QueryInput';
import { ResultDisplay } from '../components/ResultDisplay';
import {
  DEFAULT_TEXT_SYSTEM_PROMPT,
  DEFAULT_WEBAPP_SYSTEM_PROMPT,
  DEFAULT_GRAPHVIZ_SYSTEM_PROMPT,
  DEFAULT_MERMAID_SYSTEM_PROMPT
} from '../constants/models';
import type { GenerationRequest, GenerationResponse, LLMResponse, ModelType, PromptType } from '../types';

import { generate } from '../lib/llm';

export const meta: MetaFunction = () => {
  return [
    { title: 'AI Gradio JS' },
    { name: 'description', content: 'AI Gradio ported to React and Cloudflare Workers' },
  ];
};

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
  const [query, setQuery] = useState('make chat app');
  const [selectedModels, setSelectedModels] = useState<ModelType[]>(['gemini:gemini-2.0-flash']);
  const [promptType, setPromptType] = useState<PromptType>('webapp');
  const [usePlanning, setUsePlanning] = useState(false);
  const [useLlmApi, setUseLlmApi] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [allResponses, setAllResponses] = useState<LLMResponse[]>([]);
  const [currentPlan, setCurrentPlan] = useState<string | undefined>(undefined);
  const [systemPrompt, setSystemPrompt] = useState(DEFAULT_WEBAPP_SYSTEM_PROMPT);
  const [showSystemPrompt, setShowSystemPrompt] = useState(false);
  const [completedRequests, setCompletedRequests] = useState(0);
  const [totalRequests, setTotalRequests] = useState(0);
  // 有名Webサービスのリスト
  const famousWebServices = [
    'AirBnB', 'Twitter', 'Instagram', 'Facebook', 'TikTok', 
    'Spotify', 'Netflix', 'YouTube', 'Amazon', 'Uber', 
    'Lyft', 'Pinterest', 'LinkedIn', 'Slack', 'Discord', 
    'Dropbox', 'Google Maps', 'Twitch', 'Reddit', 'Shopify'
  ];

  // ランダムにWebサービスを選択する関数
  const getRandomWebService = () => {
    const randomIndex = Math.floor(Math.random() * famousWebServices.length);
    return famousWebServices[randomIndex];
  };

  // デフォルトで選ばれるWebサービス
  const [selectedService, setSelectedService] = useState(getRandomWebService());

  const [defaultQueries, setDefaultQueries] = useState({
    text: 'Explain quantum computing in simple terms',
    webapp: 'Create a chat app',
    graphviz: `${selectedService}が成功した要因を示すラーニング（グロース）フローを書いてください。学びをフィードバックするので様々な箇所で循環があるはずです。`,
    mermaid: `${selectedService}が成功した要因を示すラーニング（グロース）フローを書いてください。学びをフィードバックするので様々な箇所で循環があるはずです。`
  });

  // 新しいWebサービスをランダムに選択する関数
  const refreshWebService = () => {
    const newService = getRandomWebService();
    setSelectedService(newService);
    
    setDefaultQueries(prev => ({
      ...prev,
      graphviz: `${newService}が成功した要因を示すラーニング（グロース）フローを書いてください。学びをフィードバックするので様々な箇所で循環があるはずです。`,
      mermaid: `${newService}が成功した要因を示すラーニング（グロース）フローを書いてください。学びをフィードバックするので様々な箇所で循環があるはずです。`
    }));
  };

  useEffect(() => {
    // プロンプトタイプに応じてシステムプロンプトを設定
    switch (promptType) {
      case 'text':
        setSystemPrompt(DEFAULT_TEXT_SYSTEM_PROMPT);
        setQuery(defaultQueries.text);
        break;
      case 'webapp':
        setSystemPrompt(DEFAULT_WEBAPP_SYSTEM_PROMPT);
        setQuery(defaultQueries.webapp);
        break;
      case 'graphviz':
        setSystemPrompt(DEFAULT_GRAPHVIZ_SYSTEM_PROMPT);
        setQuery(defaultQueries.graphviz);
        break;
      case 'mermaid':
        setSystemPrompt(DEFAULT_MERMAID_SYSTEM_PROMPT);
        setQuery(defaultQueries.mermaid);
        break;
      default:
        setSystemPrompt(DEFAULT_WEBAPP_SYSTEM_PROMPT);
        setQuery(defaultQueries.webapp);
    }
  }, [promptType, defaultQueries]);

  useEffect(() => {
    if (useLlmApi) {
      // LLM APIの詳細をシステムプロンプトに追加
      setSystemPrompt(prevPrompt => {
        return `${prevPrompt}\n\n10. Additionally, an internal LLM API is available at POST /api/llm.
   - To use this API, send a JSON object with:
     * 'prompt' field containing your textual prompt
     * 'format_type' field set to either "text" or "json"
   - Example request for JSON response:
     fetch('/api/llm', {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify({
         prompt: 'Convert 42 to Roman numerals and return as JSON',
         format_type: 'json'
       })
     })
   - When format_type is "json", ensure your prompt asks for JSON format.
   - Example JSON response format:
     {
       "number": 42,
       "roman": "XLII"
     }
   - Note: Even with format_type="json", the response might be wrapped in \`\`\`json code blocks.
     The API will automatically handle this and extract the JSON content.
   - For text responses, omit format_type or set it to "text"
   - The default model is gemini-2.0-flash
   - Ensure you include proper error handling when invoking this API.`;
      });
    } else {
      // LLM APIの詳細を削除して元のプロンプトに戻す
      setSystemPrompt(
        promptType === 'text' ? DEFAULT_TEXT_SYSTEM_PROMPT : DEFAULT_WEBAPP_SYSTEM_PROMPT
      );
    }
  }, [useLlmApi, promptType]);

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
    
    // 状態をリセット
    setIsLoading(true);
    setAllResponses([]);
    setCurrentPlan(undefined);
    setCompletedRequests(0);
    
    try {
      // 合計リクエスト数を設定（プランニング + 各モデル）
      const modelCount = selectedModels.length;
      const planningCount = usePlanning ? 1 : 0;
      setTotalRequests(modelCount + planningCount);
      
      // プランニングが有効な場合は最初にプランを取得
      if (usePlanning) {
        const planFormData = new FormData();
        planFormData.append('query', query);
        planFormData.append('type', 'plan');
        
        const planResponse = await fetch('/api/generate', {
          method: 'POST',
          body: planFormData,
        });
        
        if (planResponse.ok) {
          const planData = await planResponse.json() as { plan?: string };
          if (planData.plan) {
            setCurrentPlan(planData.plan);
          }
        }
        
        // プランニングリクエストが完了したのでカウントを更新
        setCompletedRequests(prev => prev + 1);
      }
      
      // 各モデルごとに個別のリクエストを送信
      const modelRequests = selectedModels.map(async (model) => {
        const modelFormData = new FormData();
        modelFormData.append('query', query);
        modelFormData.append('model', model);
        modelFormData.append('systemPrompt', systemPrompt);
        modelFormData.append('promptType', promptType);
        
        try {
          const startTime = Date.now();
          const response = await fetch('/api/generate', {
            method: 'POST',
            body: modelFormData,
          });
          
          if (response.ok) {
            const result = await response.json() as { output?: string; error?: string };
            const modelResponse = {
              model,
              output: result.output || '',
              error: result.error,
              startTime,
              endTime: Date.now(),
            };
            
            // 結果を状態に追加
            setAllResponses(prev => [...prev, modelResponse]);
          } else {
            // エラーレスポンスの処理
            const errorText = await response.text();
            setAllResponses(prev => [...prev, {
              model,
              output: '',
              error: `Request failed: ${errorText}`,
              startTime,
              endTime: Date.now(),
            }]);
          }
          
          // リクエストが完了したのでカウントを更新
          setCompletedRequests(prev => prev + 1);
        } catch (error) {
          // ネットワークエラーなどの処理
          setAllResponses(prev => [...prev, {
            model,
            output: '',
            error: error instanceof Error ? error.message : 'Failed to fetch response',
            startTime: Date.now(),
            endTime: Date.now(),
          }]);
          
          // エラーでもリクエストは完了したとみなす
          setCompletedRequests(prev => prev + 1);
        }
      });
      
      // すべてのリクエストが完了したらローディング状態を解除
      await Promise.all(modelRequests);
      setIsLoading(false);
    } catch (error) {
      console.error('Error in generation:', error);
      setIsLoading(false);
      setAllResponses(prev => [...prev, {
        model: 'error',
        output: '',
        error: error instanceof Error ? error.message : 'Failed to generate response',
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
              <input type="hidden" name="useLlmApi" value={String(useLlmApi)} />
              <QueryInput
                query={query}
                onChange={setQuery}
                isLoading={isLoading}
                completedRequests={completedRequests}
                totalRequests={totalRequests}
              />
            </fetcher.Form>

            <div className="space-y-2">
              <div className="flex flex-wrap gap-4">
                <label className="inline-flex items-center">
                  <input
                    type="radio"
                    value="text"
                    checked={promptType === 'text'}
                    onChange={(e) => {
                      const newType = e.target.value as PromptType;
                      // Text選択時は何もしない
                      setPromptType(newType);
                    }}
                    className="form-radio h-4 w-4 text-[var(--color-accent)]"
                  />
                  <span className="ml-2">Text</span>
                </label>
                <label className="inline-flex items-center">
                  <input
                    type="radio"
                    value="webapp"
                    checked={promptType === 'webapp'}
                    onChange={(e) => {
                      const newType = e.target.value as PromptType;
                      // ダイアグラムタイプを選択するたびに新しいWebサービスを選択
                      refreshWebService();
                      setPromptType(newType);
                    }}
                    className="form-radio h-4 w-4 text-[var(--color-accent)]"
                  />
                  <span className="ml-2">Web App</span>
                </label>
                <label className="inline-flex items-center">
                  <input
                    type="radio"
                    value="graphviz"
                    checked={promptType === 'graphviz'}
                    onChange={(e) => {
                      refreshWebService();
                      setPromptType(e.target.value as PromptType);
                    }}
                    className="form-radio h-4 w-4 text-[var(--color-accent)]"
                  />
                  <span className="ml-2">GraphViz</span>
                </label>
                <label className="inline-flex items-center">
                  <input
                    type="radio"
                    value="mermaid"
                    checked={promptType === 'mermaid'}
                    onChange={(e) => {
                      refreshWebService();
                      setPromptType(e.target.value as PromptType);
                    }}
                    className="form-radio h-4 w-4 text-[var(--color-accent)]"
                  />
                  <span className="ml-2">Mermaid</span>
                </label>
              </div>
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

            <div className="flex space-x-4">
              <label className="inline-flex items-center">
                <input
                  type="checkbox"
                  checked={usePlanning}
                  onChange={(e) => setUsePlanning(e.target.checked)}
                  className="form-checkbox h-4 w-4 text-indigo-600"
                />
                <span className="ml-2">Use Planning</span>
              </label>

              <label className="inline-flex items-center">
                <input
                  type="checkbox"
                  checked={useLlmApi}
                  onChange={(e) => setUseLlmApi(e.target.checked)}
                  className="form-checkbox h-4 w-4 text-indigo-600"
                />
                <span className="ml-2">Use LLM API</span>
              </label>
            </div>

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
            <ResultDisplay responses={allResponses} plan={currentPlan} promptType={promptType} isLoading={isLoading} />
          </div>
        )}
      </div>
    </div>
  );
}

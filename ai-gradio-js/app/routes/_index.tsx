import { useState, useEffect } from 'react';
import { useFetcher, type ActionFunctionArgs, type MetaFunction } from 'react-router';
import { ModelSelector } from '../components/ModelSelector';
import { QueryInput } from '../components/QueryInput';
import { ResultDisplay } from '../components/ResultDisplay';
import { DEFAULT_TEXT_SYSTEM_PROMPT, DEFAULT_WEBAPP_SYSTEM_PROMPT } from '../constants/models';
import type { GenerationRequest, GenerationResponse, ModelType, PromptType } from '../types';

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
  const [query, setQuery] = useState('make todo app');
  const [selectedModels, setSelectedModels] = useState<ModelType[]>(['gemini:gemini-2.0-flash']);
  const [promptType, setPromptType] = useState<PromptType>('webapp');
  const [usePlanning, setUsePlanning] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<GenerationResponse | null>(null);
  const [systemPrompt, setSystemPrompt] = useState(DEFAULT_TEXT_SYSTEM_PROMPT);

  useEffect(() => {
    setSystemPrompt(
      promptType === 'text' ? DEFAULT_TEXT_SYSTEM_PROMPT : DEFAULT_WEBAPP_SYSTEM_PROMPT
    );
  }, [promptType]);

  const fetcher = useFetcher<typeof action>();
  
  useEffect(() => {
    if (fetcher.data) {
      setResponse(fetcher.data);
    }
  }, [fetcher.data]);

  useEffect(() => {
    setIsLoading(fetcher.state !== 'idle');
  }, [fetcher.state]);

  return (
    <div className="min-h-screen flex">
      {/* Left Sidebar */}
      <div className="w-80 min-w-80 border-r border-[var(--color-border)] p-4 overflow-y-auto">
        <div className="space-y-6">
          <div className="space-y-8">
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">AI Gradio JS</h1>
              <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
                Generate responses using multiple LLM models in parallel
              </p>
            </div>

            <div className="space-y-2">
              <label 
                htmlFor="systemPrompt" 
                className="block text-sm font-medium text-[var(--color-text-primary)]"
              >
                System Prompt
              </label>
              <textarea
                id="systemPrompt"
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                className="input-field w-full min-h-[100px]"
                placeholder="Enter system prompt..."
              />
            </div>

            <div className="space-y-4">
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

              <fetcher.Form method="post">
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
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 p-4 overflow-y-auto">
        {(isLoading || response) && (
          <div className="max-w-[1200px] mx-auto">
            {isLoading && <div className="text-center">Generating...</div>}
            <ResultDisplay response={response} />
          </div>
        )}
      </div>
    </div>
  );
}

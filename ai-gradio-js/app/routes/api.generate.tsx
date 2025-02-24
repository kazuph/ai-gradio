import type { ActionFunctionArgs } from 'react-router';
import { generateGemini } from '../lib/llm/gemini';
import { generateOpenAI } from '../lib/llm/openai';
import { generateAnthropic } from '../lib/llm/anthropic';
import { DEFAULT_TEXT_SYSTEM_PROMPT } from '../constants/models';
import type { GenerationRequest, GenerationResponse, LLMResponse, ModelType, PromptType } from '../types';

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

    // プランニングが有効な場合は実行
    let plan = "";
    if (data.usePlanning) {
      plan = await getImplementationPlan(data.query, data.env);
    }

    // 各モデルの生成を並列で開始
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
        return errorResult;
      }
    });

    // すべてのモデルの結果を待つ
    const results = await Promise.all(modelPromises);

    // 結果を返す
    const response: GenerationResponse = {
      results,
      plan: plan || undefined,
    };

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
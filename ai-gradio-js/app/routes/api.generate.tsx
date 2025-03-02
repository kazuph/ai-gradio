import type { ActionFunctionArgs } from 'react-router';
import { generateGemini } from '../lib/llm/gemini';
import { generateOpenAI } from '../lib/llm/openai';
import { generateAnthropic } from '../lib/llm/anthropic';
import { DEFAULT_TEXT_SYSTEM_PROMPT, DEFAULT_EXCALIDRAW_SYSTEM_PROMPT, DEFAULT_GRAPHVIZ_SYSTEM_PROMPT, DEFAULT_MERMAID_SYSTEM_PROMPT } from '../constants/models';
import type { ModelType, PromptType } from '../types';
// @ts-ignore
import { json } from '@remix-run/cloudflare';
import { OpenAI } from 'openai';
import { Anthropic as AnthropicSDK } from '@anthropic-ai/sdk';
import { GoogleGenerativeAI } from '@google/generative-ai';
import { generateDiagramPreview } from '../lib/kroki';

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
  try {
    // フォームデータを取得
    const formData = await request.formData();
    const query = formData.get('query') as string;
    const model = formData.get('model') as string;
    let systemPrompt = formData.get('systemPrompt') as string;
    const promptType = formData.get('promptType') as string;
    const type = formData.get('type') as string;
    
    // Override systemPrompt if diagram type is selected
    if (promptType === 'excalidraw') {
      systemPrompt = DEFAULT_EXCALIDRAW_SYSTEM_PROMPT;
    } else if (promptType === 'graphviz') {
      systemPrompt = DEFAULT_GRAPHVIZ_SYSTEM_PROMPT;
    } else if (promptType === 'mermaid') {
      systemPrompt = DEFAULT_MERMAID_SYSTEM_PROMPT;
    }

    // プランニングリクエストの処理
    if (type === 'plan') {
      const plan = await getImplementationPlan(query, context.cloudflare.env);
      return new Response(JSON.stringify({ plan }), {
        headers: { 'Content-Type': 'application/json' },
      });
    }
    
    // 通常の生成リクエストの処理
    const startTime = Date.now();
    
    try {
      const response = await generateForModel(model as ModelType, query, systemPrompt, context.cloudflare.env);
      
      // 図表示用の処理
      if (promptType === 'excalidraw' || promptType === 'graphviz' || promptType === 'mermaid') {
        const diagramHtml = await generateDiagramPreview(response.output, promptType);
        return new Response(JSON.stringify({
          model,
          output: diagramHtml,
          startTime,
          endTime: Date.now(),
        }), {
          headers: { 'Content-Type': 'application/json' },
        });
      }
      
      return new Response(JSON.stringify({
        model,
        output: response.output,
        error: response.error,
        startTime,
        endTime: Date.now(),
      }), {
        headers: { 'Content-Type': 'application/json' },
      });
    } catch (error) {
      return new Response(JSON.stringify({
        model,
        output: "",
        error: error instanceof Error ? error.message : 'Unknown error',
        startTime,
        endTime: Date.now(),
      }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      });
    }
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

// loaderハンドラは不要になるため削除 
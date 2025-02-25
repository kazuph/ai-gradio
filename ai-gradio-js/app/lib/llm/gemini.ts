import { GoogleGenerativeAI } from "@google/generative-ai";
import type { LLMResponse } from "../../types";

export async function generateGemini(
  query: string,
  model: string,
  systemPrompt: string,
  env: Env,
  format_type: 'text' | 'json' = 'text'
): Promise<LLMResponse> {
  const modelName = model.replace("gemini:", "");
  try {
    const genAI = new GoogleGenerativeAI(env.GEMINI_API_KEY);
    // Initialize the model with additional configuration for experimental models
    const geminiModel = genAI.getGenerativeModel({ 
      model: modelName,
      generationConfig: {
        temperature: 1,
        topP: 0.95,
        topK: 64,
        maxOutputTokens: 8192,
        responseMimeType: "text/plain",
      },
      // @ts-ignore - apiVersion is supported but not in the type definitions
      apiVersion: "v1beta"  // Important for experimental models
    });

    const chat = geminiModel.startChat({
      history: [
        {
          role: "user",
          parts: [{ text: systemPrompt }]
        },
        {
          role: "model",
          parts: [{ text: "I understand and will follow these instructions." }]
        },
      ],
    });

    console.log(`Gemini API Request - Model: ${modelName}`, {
      systemPrompt,
      query,
    });

    const result = await chat.sendMessage([{ text: query }]);
    const response = await result.response;
    
    console.log(`Gemini API Response - Model: ${modelName}`, {
      text: response.text,
      textType: typeof response.text,
      textValue: response.text instanceof Function ? response.text() : response.text,
    });

    // Get the text content
    let responseText: string;
    if (typeof response.text === 'function') {
      responseText = response.text();
      console.log('Function response text:', responseText);
    } else {
      responseText = response.text as string;
      console.log('Direct response text:', responseText);
    }

    if (!responseText) {
      console.error('Empty response text from Gemini');
      throw new Error('Empty response from Gemini API');
    }

    // Extract content from code blocks if present
    let output = responseText;
    const codeBlockMatch = output.match(/```(?:html)?\n([\s\S]*?)```/i);
    if (codeBlockMatch) {
      output = codeBlockMatch[1].trim();
    } else {
      // テキストモードの場合は、HTMLタグで自動的に囲まないようにする
      const htmlMatch = output.match(/<[^>]+>/);
      if (!htmlMatch && format_type === 'json') {
        // JSONモードでHTMLタグがない場合のみ、<p>タグで囲む
        output = `<p>${output}</p>`;
      }
    }

    // Clean up HTML content
    output = output
      .replace(/class=/g, 'className=')  // React compatibility
      .trim();

    // Log for debugging
    console.log('Processed Gemini Response:', {
      responseText,
      processedOutput: output,
      hasCodeBlock: !!codeBlockMatch
    });

    const finalResponse = {
      model: modelName,
      output: output
    };
    
    console.log('Final Gemini Response:', finalResponse);
    return finalResponse;
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
    console.error('Gemini API Error:', errorMessage);
    return {
      model: modelName,
      output: "",
      error: errorMessage
    };
  }
}

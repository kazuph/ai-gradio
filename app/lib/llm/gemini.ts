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
    // Gemini 2.5系モデルかどうか判定
    const isGemini25 = modelName.startsWith("gemini-2.5-");
    let responseText = "";
    let output = "";

    if (isGemini25) {
      // Gemini 2.5系モデルのAPI呼び出し
      const geminiModel = genAI.getGenerativeModel({ model: modelName }, { systemInstruction: systemPrompt });
      // プロンプトを公式推奨の形式で渡す
      const result = await geminiModel.generateContent({
        contents: [
          { role: "user", parts: [{ text: query }] }
        ]
      });
      // レスポンスの取り出し
      const candidates = result.response.candidates;
      if (candidates && candidates.length > 0 && candidates[0].content && candidates[0].content.parts && candidates[0].content.parts.length > 0) {
        responseText = candidates[0].content.parts[0].text || "";
      } else {
        responseText = "";
      }
    } else {
      // 従来モデル（2.0系など）
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
        apiVersion: "v1beta"
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
      const result = await chat.sendMessage([{ text: query }]);
      const response = await result.response;
      if (typeof response.text === 'function') {
        responseText = response.text();
      } else {
        responseText = response.text as string;
      }
    }

    if (!responseText) {
      console.error('Empty response text from Gemini');
      throw new Error('Empty response from Gemini API');
    }

    // Extract content from code blocks if present
    output = responseText;
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
      isGemini25,
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
      model: model.replace("gemini:", ""),
      output: "",
      error: errorMessage
    };
  }
}

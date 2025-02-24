import { GoogleGenerativeAI } from "@google/generative-ai";
import { LLMResponse } from "../../types";

export async function generateGemini(
  query: string,
  model: string,
  systemPrompt: string,
  env: Env,
): Promise<LLMResponse> {
  const modelName = model.replace("gemini:", "");
  try {
    const genAI = new GoogleGenerativeAI(env.GOOGLE_API_KEY);
    const geminiModel = genAI.getGenerativeModel({ model: modelName });

    const chat = geminiModel.startChat({
      history: [
        {
          role: "user",
          parts: systemPrompt,
        },
        {
          role: "model",
          parts: "I understand and will follow these instructions.",
        },
      ],
    });

    console.log(`Gemini API Request - Model: ${modelName}`, {
      systemPrompt,
      query,
    });

    const result = await chat.sendMessage(query);
    const response = await result.response;
    
    console.log(`Gemini API Response - Model: ${modelName}`, {
      text: response.text,
      textType: typeof response.text,
      textValue: response.text instanceof Function ? response.text() : response.text,
    });

    // Get the text content
    let responseText;
    if (typeof response.text === 'function') {
      responseText = response.text();
      console.log('Function response text:', responseText);
    } else {
      responseText = response.text;
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
      // If no code block is found, check if the content looks like HTML
      const htmlMatch = output.match(/<[^>]+>/);
      if (!htmlMatch) {
        // If not HTML, wrap in a paragraph
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

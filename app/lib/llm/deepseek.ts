import type { LLMResponse } from "../../types";

export async function generateDeepSeek(
  query: string,
  model: string,
  systemPrompt: string,
  env: Env,
): Promise<LLMResponse> {
  const modelName = model.replace("deepseek:", "");
  try {
    console.log(`DeepSeek API Request - Model: ${modelName}`, {
      systemPrompt,
      query,
    });
    // DEEPSEEK_API_KEYがからじゃないかをチェック
    if (!env.DEEPSEEK_API_KEY) {
      throw new Error(" DEEPSEEK_API_KEY is not set");
    } else {
      console.log(" DEEPSEEK_API_KEY is set");
    }
    // DeepSeek API is compatible with OpenAI API format
    const response = await fetch("https://api.deepseek.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${env.DEEPSEEK_API_KEY}`
      },
      body: JSON.stringify({
        model: modelName,
        messages: [
          {
            role: "system",
            content: systemPrompt
          },
          {
            role: "user",
            content: query
          }
        ],
        temperature: 0.7,
        max_tokens: 4096
      })
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error('DeepSeek API Error:', errorData);
      throw new Error(`DeepSeek API Error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json() as { choices: [{ message?: { content?: string } }] }; 
    console.log('DeepSeek API Raw Response:', data);

    // Extract response text
    const responseText = data.choices[0]?.message?.content || '';

    console.log(`DeepSeek API Response - Model: ${modelName}`, {
      text: responseText,
    });

    if (!responseText) {
      console.error('Empty response text from DeepSeek');
      throw new Error('Empty response from DeepSeek API');
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
    console.log('Processed DeepSeek Response:', {
      responseText,
      processedOutput: output,
      hasCodeBlock: !!codeBlockMatch
    });

    const finalResponse = {
      model: modelName,
      output: output
    };

    console.log('Final DeepSeek Response:', finalResponse);
    return finalResponse;
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
    console.error('DeepSeek API Error:', errorMessage);
    return {
      model: modelName,
      output: "",
      error: errorMessage
    };
  }
}

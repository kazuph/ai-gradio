/**
 * Kroki.ioのAPIを使用して図のSVGを取得するユーティリティ関数
 */

/**
 * 図のソースコードからSVGを取得する
 * @param diagramSource 図のソースコード
 * @param diagramType 図のタイプ (excalidraw, graphviz, mermaid)
 * @returns SVG形式の図、エラーの場合はエラーメッセージ
 */
export async function getKrokiSvg(diagramSource: string, diagramType: string): Promise<string> {
  try {
    // POSTリクエストを使用する方法
    const url = `https://kroki.io/${diagramType}/svg`;
    const headers = {
      "Content-Type": "text/plain"
    };
    
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: diagramSource
    });
    
    if (response.ok) {
      return await response.text();
    }
    
    // エラーの場合はエラーメッセージを返す
    return `<div class='error'>Error: ${response.status} - ${await response.text()}</div>`;
  } catch (error) {
    console.error(`Error getting SVG from Kroki.io: ${error}`);
    return `<div class='error'>Error: ${error instanceof Error ? error.message : String(error)}</div>`;
  }
}

/**
 * 図のソースコードからコードブロックを抽出する
 * @param diagramSource 図のソースコード
 * @param diagramType 図のタイプ (excalidraw, graphviz, mermaid)
 * @returns 抽出されたソースコード
 */
export function extractDiagramCode(diagramSource: string, diagramType: string): string | null {
  // コードブロックから図のソースコードを抽出
  let pattern: RegExp;
  
  if (diagramType === 'excalidraw') {
    // Excalidrawの場合は、jsonコードブロックも対象にする
    pattern = new RegExp(`\`\`\`(?:${diagramType}|json)?\s*([\\s\\S]*?)\s*\`\`\``, 'i');
  } else {
    pattern = new RegExp(`\`\`\`(?:${diagramType})?\s*([\\s\\S]*?)\s*\`\`\``, 'i');
  }
  
  const match = pattern.exec(diagramSource);
  
  if (match) {
    return match[1].trim();
  }
  
  return null;
}

/**
 * 図のプレビューを表示するHTMLを生成する
 * @param diagramSource 図のソースコード
 * @param diagramType 図のタイプ (excalidraw, graphviz, mermaid)
 * @returns HTMLコンテンツ
 */
export async function generateDiagramPreview(diagramSource: string, diagramType: string): Promise<string> {
  // コードブロックから図のソースコードを抽出
  const sourceCode = extractDiagramCode(diagramSource, diagramType);
  
  if (!sourceCode) {
    return `<div class='error'>Error: No ${diagramType} code block found in the response.</div>`;
  }
  
  const svgContent = await getKrokiSvg(sourceCode, diagramType);
  
  const html = `
  <div class="result-card">
    <div class="card-header" style="display: flex; justify-content: space-between; padding: 8px 16px; align-items: center;">
      <div class="header-title">
        <strong>${diagramType.charAt(0).toUpperCase() + diagramType.slice(1)} Diagram</strong>
      </div>
    </div>
    <div class="diagram-preview" style="padding: 16px; overflow: auto;">
      ${svgContent}
    </div>
    <div class="code-content">
      <pre><code>${sourceCode}</code></pre>
    </div>
  </div>
  `;
  
  return html;
} 
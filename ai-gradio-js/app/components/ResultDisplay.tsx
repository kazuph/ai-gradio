import { useState, useEffect, useCallback, useRef } from 'react';
import type { LLMResponse, PromptType } from "../types";
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/cjs/styles/prism';
import ReactMarkdown from 'react-markdown';

interface ResultDisplayProps {
  responses: LLMResponse[];
  plan?: string;
  promptType: PromptType;
}

export function ResultDisplay({ responses, plan, promptType }: ResultDisplayProps) {
  const [copyStatus, setCopyStatus] = useState<{[key: string]: string}>({});
  const [isEditing, setIsEditing] = useState<{[key: string]: boolean}>({});
  const [editableCode, setEditableCode] = useState<{[key: string]: string}>({});
  const [showCode, setShowCode] = useState<{[key: string]: boolean}>({});
  const textareaRefs = useRef<{[key: string]: HTMLTextAreaElement}>({});

  // コードをクリップボードにコピーする関数
  const copyToClipboard = async (text: string, uniqueKey: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopyStatus(prev => ({ ...prev, [uniqueKey]: 'コピーしました！' }));
      setTimeout(() => {
        setCopyStatus(prev => ({ ...prev, [uniqueKey]: '' }));
      }, 2000);
    } catch (err) {
      setCopyStatus(prev => ({ ...prev, [uniqueKey]: 'コピーに失敗しました' }));
      setTimeout(() => {
        setCopyStatus(prev => ({ ...prev, [uniqueKey]: '' }));
      }, 2000);
    }
  };

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  const calculateSeconds = (start?: number, end?: number): string => {
    if (!start || !end) return '';
    const seconds = ((end - start) / 1000).toFixed(2);
    return `(${seconds}秒)`;
  };

  // 最新の結果が上に表示されるように並び替え
  const sortedResponses = [...responses].sort((a, b) => {
    return (b.startTime || 0) - (a.startTime || 0);
  });

  // マークダウンからダイアグラムコードを抽出する関数
  const extractDiagramCode = useCallback((text: string): string => {
    // まずコードブロックを探す
    const regex = new RegExp(`\`\`\`(?:${promptType}|json)?\\s*([\\s\\S]*?)\\s*\`\`\``);
    const match = regex.exec(text);
    if (match) {
      return match[1];
    }
    
    // コードブロックがない場合は、<code>タグ内のコンテンツを探す
    const codeTagRegex = /<code>([\s\S]*?)<\/code>/i;
    const codeTagMatch = codeTagRegex.exec(text);
    if (codeTagMatch) {
      return codeTagMatch[1];
    }
    
    // コードブロックもcodeタグもない場合は、出力全体を返す（SVGタグを除く）
    const withoutSvg = text.replace(/<svg[^>]*>[\s\S]*?<\/svg>/g, '').trim();
    return withoutSvg || text;
  }, [promptType]);

  // SVGを抽出する関数
  const extractSvg = (text: string): string | null => {
    const match = /<svg[^>]*>[\s\S]*?<\/svg>/i.exec(text);
    return match ? match[0] : null;
  };

  return (
    <div className="space-y-6">
      {plan && (
        <div className="card p-4">
          <h3 className="text-lg font-medium text-[var(--color-text-primary)] mb-2">
            Implementation Plan
          </h3>
          <pre className="whitespace-pre-wrap text-sm text-[var(--color-text-secondary)]">
            {plan}
          </pre>
        </div>
      )}

      <div className="space-y-4">
        {sortedResponses.map((result) => {
          const uniqueKey = `${result.model}-${result.startTime}`;
          
          // 図表示モード用のアクション
          if (promptType === 'excalidraw' || promptType === 'graphviz' || promptType === 'mermaid') {
            const diagramCode = extractDiagramCode(result.output);
            const svg = extractSvg(result.output);
            const diagramTypeDisplay = promptType.charAt(0).toUpperCase() + promptType.slice(1);
            
            // 編集中の場合は編集モードを表示
            if (isEditing[uniqueKey]) {
              return (
                <div key={uniqueKey} className="card">
                  <div className="card-header flex justify-between items-center p-4">
                    <div className="flex items-center">
                      <span className="font-medium">{result.model} - 編集モード</span>
                      <span className="text-sm text-[var(--color-text-secondary)] ml-2">
                        {result.startTime && formatTimestamp(result.startTime)} {calculateSeconds(result.startTime, result.endTime)}
                      </span>
                    </div>
                    <div className="flex space-x-2">
                      <button
                        type="button"
                        onClick={() => {
                          // 編集完了時に編集内容で上書き
                          const newCode = editableCode[uniqueKey] || diagramCode || '';
                          
                          // SVGを更新
                          fetch(`https://kroki.io/${promptType}/svg`, {
                            method: 'POST',
                            headers: { "Content-Type": "text/plain" },
                            body: newCode
                          })
                          .then(response => response.text())
                          .then(svg => {
                            // 結果オブジェクトを更新（実際には新しいオブジェクトを作成）
                            const updatedResult = {
                              ...result,
                              output: result.output.replace(/<svg[^>]*>[\s\S]*?<\/svg>/i, svg)
                                .replace(new RegExp(`\`\`\`(?:${promptType}|json)?\\s*[\\s\\S]*?\\s*\`\`\``), 
                                       `\`\`\`${promptType}\n${newCode}\n\`\`\``)
                            };
                            
                            // responsesの該当する要素を更新
                            const index = responses.findIndex(r => 
                              r.model === result.model && r.startTime === result.startTime);
                            if (index !== -1) {
                              const newResponses = [...responses];
                              newResponses[index] = updatedResult;
                              // ここでは直接responsesを更新できないので、親コンポーネントに通知する必要がある
                              // 今回は簡易的に対応
                            }
                            
                            setIsEditing(prev => ({ ...prev, [uniqueKey]: false }));
                          })
                          .catch(error => {
                            console.error('SVG更新エラー:', error);
                          });
                        }}
                        className="px-2 py-1 bg-blue-500 text-white rounded text-xs"
                      >
                        編集終了
                      </button>
                    </div>
                  </div>
                  
                  <div className="p-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <div className="mb-2 text-sm font-medium text-[var(--color-text-primary)]">
                          {diagramTypeDisplay} コードを編集
                        </div>
                        <textarea
                          ref={(el) => {
                            if (el) textareaRefs.current[uniqueKey] = el;
                          }}
                          value={editableCode[uniqueKey] || diagramCode || ''}
                          onChange={(e) => {
                            const newValue = e.target.value;
                            setEditableCode(prev => ({ ...prev, [uniqueKey]: newValue }));
                          }}
                          className="w-full h-[400px] p-2 font-mono text-sm bg-[var(--color-bg-primary)] text-[var(--color-text-primary)] border rounded"
                        />
                        <div className="flex justify-end mt-2 space-x-2">
                          <button 
                            type="button"
                            onClick={() => {
                              // SVGプレビュー更新処理
                              fetch(`https://kroki.io/${promptType}/svg`, {
                                method: 'POST',
                                headers: { "Content-Type": "text/plain" },
                                body: editableCode[uniqueKey] || diagramCode || ''
                              })
                              .then(response => response.text())
                              .then(svg => {
                                const previewElem = document.getElementById(`diagram-preview-${uniqueKey}`);
                                if (previewElem) {
                                  previewElem.innerHTML = svg;
                                }
                              })
                              .catch(error => {
                                console.error('SVG更新エラー:', error);
                              });
                            }}
                            className="px-2 py-1 bg-purple-500 text-white rounded text-xs"
                          >
                            プレビュー更新
                          </button>
                          <button 
                            type="button"
                            onClick={() => {
                              setEditableCode(prev => ({ ...prev, [uniqueKey]: diagramCode || '' }));
                            }}
                            className="px-2 py-1 bg-gray-500 text-white rounded text-xs"
                          >
                            リセット
                          </button>
                        </div>
                      </div>
                      
                      <div>
                        <div className="mb-2 text-sm font-medium text-[var(--color-text-primary)]">
                          {diagramTypeDisplay} プレビュー
                        </div>
                        <div className="border rounded p-4 bg-white overflow-auto" style={{ height: '400px' }}>
                          <div id={`diagram-preview-${uniqueKey}`} dangerouslySetInnerHTML={{ __html: svg || '' }} />
                        </div>
                        <div className="flex justify-end mt-2 space-x-2">
                          {/* 編集中もSVGをダウンロードできるようにする */}
                          <button
                            onClick={() => {
                              const previewElem = document.getElementById(`diagram-preview-${uniqueKey}`);
                              if (previewElem?.innerHTML) {
                                const blob = new Blob([previewElem.innerHTML], { type: 'image/svg+xml' });
                                const url = URL.createObjectURL(blob);
                                const a = document.createElement('a');
                                a.href = url;
                                a.download = `${promptType}-diagram-${new Date().getTime()}.svg`;
                                document.body.appendChild(a);
                                a.click();
                                document.body.removeChild(a);
                                URL.revokeObjectURL(url);
                              }
                            }}
                            className="px-2 py-1 bg-blue-500 text-white rounded text-xs"
                            type="button"
                          >
                            SVGダウンロード
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            }
            
            return (
              <div key={uniqueKey} className="card">
                <div className="card-header flex justify-between items-center p-4">
                  <div className="flex items-center">
                    <span className="font-medium">{result.model}</span>
                    <span className="text-sm text-[var(--color-text-secondary)] ml-2">
                      {result.startTime && formatTimestamp(result.startTime)} {calculateSeconds(result.startTime, result.endTime)}
                    </span>
                  </div>
                  <div className="flex space-x-2">
                    {/* SVGのダウンロードボタン */}
                    {svg && (
                      <button
                        onClick={() => {
                          const blob = new Blob([svg], { type: 'image/svg+xml' });
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = `${promptType}-diagram-${new Date().getTime()}.svg`;
                          document.body.appendChild(a);
                          a.click();
                          document.body.removeChild(a);
                          URL.revokeObjectURL(url);
                        }}
                        className="px-2 py-1 bg-blue-500 text-white rounded text-xs"
                        type="button"
                      >
                        SVGダウンロード
                      </button>
                    )}
                    
                    {/* ダイアグラムコードをコピーするボタン */}
                    {diagramCode && (
                      <button
                        onClick={() => copyToClipboard(diagramCode, uniqueKey)}
                        className="px-2 py-1 bg-green-500 text-white rounded text-xs"
                        type="button"
                      >
                        {copyStatus[uniqueKey] || 'コードコピー'}
                      </button>
                    )}
                    
                    {/* 編集ボタン */}
                    <button
                      onClick={() => {
                        // 編集モードを開始
                        setIsEditing(prev => ({ ...prev, [uniqueKey]: true }));
                        // 編集するコードを初期化
                        if (!editableCode[uniqueKey]) {
                          setEditableCode(prev => ({ ...prev, [uniqueKey]: diagramCode || '' }));
                        }
                      }}
                      className="px-2 py-1 bg-yellow-500 text-white rounded text-xs"
                      type="button"
                    >
                      編集
                    </button>
                  </div>
                </div>
                
                <div className="p-4">
                  <div className="mb-2 text-sm font-medium text-[var(--color-text-primary)] flex justify-between items-center">
                    {diagramTypeDisplay} Diagram Preview
                  </div>
                  <div className="border rounded p-4 bg-white overflow-auto" style={{ maxHeight: '500px' }}>
                    {svg ? (
                      <div dangerouslySetInnerHTML={{ __html: svg }} />
                    ) : (
                      <div className="p-4 bg-yellow-100 text-yellow-800 rounded">SVGが見つかりませんでした</div>
                    )}
                  </div>
                  
                  {diagramCode && (
                    <div className="mt-4">
                      <div className="mb-2 text-sm font-medium text-[var(--color-text-primary)] flex justify-between items-center">
                        <span>{diagramTypeDisplay} Source Code</span>
                        <button
                          onClick={() => setShowCode(prev => ({ ...prev, [uniqueKey]: !prev[uniqueKey] }))}
                          className="px-2 py-1 bg-gray-500 text-white rounded text-xs"
                          type="button"
                        >
                          {showCode[uniqueKey] ? '閉じる' : '表示'}
                        </button>
                      </div>
                      {showCode[uniqueKey] && (
                        <SyntaxHighlighter
                          language={promptType === 'excalidraw' ? 'json' : promptType}
                          style={vscDarkPlus}
                          customStyle={{
                            margin: 0,
                            borderRadius: '4px',
                            fontSize: '0.875rem'
                          }}
                        >
                          {diagramCode}
                        </SyntaxHighlighter>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          }
          
          // テキストモードとウェブアプリモード用
          return (
            <div key={uniqueKey} className="card overflow-hidden">
              <div className="bg-[var(--color-bg-secondary)] px-4 py-2 border-b border-[var(--color-border)]">
                <div className="flex justify-between items-center">
                  <h3 className="text-sm font-medium text-[var(--color-text-primary)]">
                    {result.model}
                  </h3>
                  <span className="text-xs text-[var(--color-text-secondary)]">
                    {result.startTime && formatTimestamp(result.startTime)}
                    {result.endTime && ` - ${formatTimestamp(result.endTime)} ${calculateSeconds(result.startTime, result.endTime)}`}
                  </span>
                </div>
              </div>
              <div className="p-4">
                {result.error ? (
                  <div className="text-red-400">{result.error}</div>
                ) : (
                  <div className="space-y-4">
                    {promptType === 'text' ? (
                      <div className="p-4 bg-[var(--color-bg-secondary)] rounded">
                        <div className="prose prose-invert max-w-none">
                          <ReactMarkdown>
                            {result.output}
                          </ReactMarkdown>
                        </div>
                      </div>
                    ) : promptType === 'webapp' ? (
                      <div className="space-y-4">
                        <div className="w-full flex justify-between items-center mb-2">
                          <button
                            type="button"
                            onClick={() => {
                              // WebアプリのPreviewをトグル表示
                              const previewKey = `preview-${uniqueKey}`;
                              const previewElement = document.getElementById(previewKey);
                              const previewContainer = document.getElementById(`preview-container-${uniqueKey}`);
                              
                              if (previewContainer) {
                                const currentDisplay = previewContainer.style.display;
                                const newDisplay = currentDisplay === 'none' ? 'block' : 'none';
                                previewContainer.style.display = newDisplay;
                                
                                // 「開く」操作の場合は、プレビューを再生成
                                if (newDisplay === 'block' && previewElement) {
                                  previewContainer.innerHTML = '';
                                  const previewDiv = document.createElement('div');
                                  previewDiv.id = previewKey;
                                  previewDiv.innerHTML = result.output;
                                  previewDiv.className = 'webapp-preview';
                                  previewDiv.style.color = 'black';
                                  previewContainer.appendChild(previewDiv);
                                }
                              }
                            }}
                            className="flex items-center text-sm font-medium text-[var(--color-text-primary)]"
                          >
                            <span>Preview</span>
                            <span className="ml-2" id={`preview-toggle-${uniqueKey}`}>▼</span>
                          </button>
                          
                          <button
                            onClick={() => copyToClipboard(result.output, uniqueKey)}
                            className="px-2 py-1 bg-blue-500 text-white rounded text-xs"
                            type="button"
                          >
                            {copyStatus[uniqueKey] || 'コピー'}
                          </button>
                        </div>

                        <div 
                          id={`preview-container-${uniqueKey}`}
                          className="relative border rounded p-4 bg-white overflow-auto mb-4"
                        >
                          <div
                            id={`preview-${uniqueKey}`}
                            dangerouslySetInnerHTML={{ __html: result.output }}
                            className="webapp-preview"
                            style={{ color: 'black' }}  // テキスト色を強制的に黒に設定
                          />
                        </div>
                        
                        <div className="space-y-2">
                          <button
                            type="button"
                            onClick={() => setShowCode(prev => ({ ...prev, [uniqueKey]: !prev[uniqueKey] }))}
                            className="flex items-center text-sm font-medium text-[var(--color-text-primary)]"
                          >
                            <span>Source Code</span>
                            <span className="ml-2">{showCode[uniqueKey] ? '▼' : '▶'}</span>
                          </button>
                          
                          {showCode[uniqueKey] && (
                            <SyntaxHighlighter
                              language="html"
                              style={vscDarkPlus}
                              customStyle={{
                                margin: 0,
                                borderRadius: '4px',
                                fontSize: '0.875rem'
                              }}
                            >
                              {result.output}
                            </SyntaxHighlighter>
                          )}
                        </div>
                      </div>
                    ) : (
                      <div className="w-full flex justify-end">
                        <button
                          onClick={() => copyToClipboard(result.output, uniqueKey)}
                          className="px-2 py-1 bg-blue-500 text-white rounded text-xs"
                          type="button"
                        >
                          {copyStatus[uniqueKey] || 'コピー'}
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

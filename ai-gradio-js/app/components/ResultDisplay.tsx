import { useState, useEffect, useRef, useCallback } from 'react';
import type { GenerationResponse, LLMResponse } from "../types";
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/cjs/styles/prism';

interface ResultDisplayProps {
  responses: LLMResponse[];
  plan?: string;
}

export function ResultDisplay({ responses, plan }: ResultDisplayProps) {
  const [showCode, setShowCode] = useState<{[key: string]: boolean}>({});
  const [showPreview, setShowPreview] = useState<{[key: string]: boolean}>({});
  const [iframeHeights, setIframeHeights] = useState<{[key: string]: number}>({});
  const iframeRefs = useRef<{[key: string]: HTMLIFrameElement}>({});
  const [renderedResponses, setRenderedResponses] = useState<{[key: string]: boolean}>({});
  const [editableHtml, setEditableHtml] = useState<{[key: string]: string}>({});
  const [isEditing, setIsEditing] = useState<{[key: string]: boolean}>({});
  const textareaRefs = useRef<{[key: string]: HTMLTextAreaElement}>({});
  
  // テキストエリアの変更ハンドラを作成
  const handleTextareaChange = useCallback((uniqueKey: string, e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    setEditableHtml(prev => ({ ...prev, [uniqueKey]: newValue }));
    // フォーカスを維持
    setTimeout(() => {
      if (textareaRefs.current[uniqueKey]) {
        textareaRefs.current[uniqueKey].focus();
        // カーソル位置を保持
        const cursorPosition = e.target.selectionStart;
        textareaRefs.current[uniqueKey].setSelectionRange(cursorPosition, cursorPosition);
      }
    }, 0);
  }, []);

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const { height, key } = event.data;
      if (height && typeof key === 'string') {
        setIframeHeights(prev => ({ ...prev, [key]: height }));
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  // 新しいレスポンスが追加されたときに処理
  useEffect(() => {
    // 新しいレスポンスを検出
    const newResponses = responses.filter(response => {
      const uniqueKey = `${response.model}-${response.startTime}`;
      return !renderedResponses[uniqueKey];
    });

    if (newResponses.length > 0) {
      // 新しいレスポンスのプレビューを表示
      const newShowPreview = { ...showPreview };
      const newRenderedResponses = { ...renderedResponses };

      for (const response of newResponses) {
        const uniqueKey = `${response.model}-${response.startTime}`;
        newShowPreview[uniqueKey] = true; // デフォルトでプレビューを表示
        newRenderedResponses[uniqueKey] = true; // レンダリング済みとしてマーク
      }

      setShowPreview(newShowPreview);
      setRenderedResponses(newRenderedResponses);
    }
  }, [responses, renderedResponses, showPreview]);

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  // バッククオートを削除する関数
  const removeBackticks = (str: string): string => {
    // 先頭と末尾のマークダウンコードブロック記法を削除
    return str.replace(/^```[\w]*\n/, '').replace(/\n```$/, '');
  };

  // 文字数をカウントする関数
  const countCharacters = (str: string): number => {
    return str.length;
  };

  // 秒数を計算する関数
  const calculateSeconds = (start?: number, end?: number): string => {
    if (!start || !end) return '';
    const seconds = ((end - start) / 1000).toFixed(2);
    return `(${seconds}秒)`;
  };

  // HTMLをコピーする関数
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
      .then(() => {
        alert('コピーしました！');
      })
      .catch(err => {
        console.error('コピーに失敗しました:', err);
      });
  };

  // 最新の結果が上に表示されるように並び替え
  const sortedResponses = [...responses].sort((a, b) => {
    return (b.startTime || 0) - (a.startTime || 0);
  });

  // 新しいレスポンスが追加されたときに編集用のHTMLを初期化
  useEffect(() => {
    const newResponses = responses.filter(response => {
      const uniqueKey = `${response.model}-${response.startTime}`;
      return !editableHtml[uniqueKey];
    });

    if (newResponses.length > 0) {
      const newEditableHtml = { ...editableHtml };
      
      for (const response of newResponses) {
        const uniqueKey = `${response.model}-${response.startTime}`;
        newEditableHtml[uniqueKey] = removeBackticks(response.output);
      }
      
      setEditableHtml(newEditableHtml);
    }
  }, [responses, editableHtml]);

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
          // outputからバッククオートを削除
          const cleanOutput = removeBackticks(result.output);
          // 一意のキーを作成
          const uniqueKey = `${result.model}-${result.startTime}`;
          
          return (
            <div
              key={uniqueKey}
              className="card overflow-hidden"
            >
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
                    {/* 文字数表示 */}
                    <div className="mb-2 text-sm text-[var(--color-text-secondary)]">
                      文字数: {countCharacters(cleanOutput)}
                    </div>
                    
                    {/* Preview of the generated HTML */}
                    <div className="border rounded overflow-hidden">
                      <div className="w-full bg-[var(--color-bg-secondary)] px-3 py-2 text-sm font-medium border-b text-[var(--color-text-primary)] flex justify-between items-center">
                        <div className="flex-1 text-left flex items-center">
                          <button
                            type="button"
                            onClick={() => setShowPreview(prev => ({ ...prev, [uniqueKey]: !prev[uniqueKey] }))}
                            className="flex items-center"
                          >
                            <span>Preview</span>
                            <span className="ml-2">{showPreview[uniqueKey] ? '▼' : '▶'}</span>
                          </button>
                        </div>
                      </div>
                      {showPreview[uniqueKey] && (
                        <iframe
                          title={`Preview ${result.model}`}
                          ref={(el) => {
                            if (el) iframeRefs.current[uniqueKey] = el;
                          }}
                          srcDoc={`
                            ${editableHtml[uniqueKey] || cleanOutput}
                            <script>
                              window.addEventListener('load', function() {
                                const height = document.documentElement.scrollHeight;
                                window.parent.postMessage({ height, key: "${uniqueKey}" }, '*');
                              });
                            </script>
                          `}
                          className="w-full bg-white transition-height duration-200 ease-in-out"
                          style={{ height: `${iframeHeights[uniqueKey] || 500}px` }}
                          sandbox="allow-scripts allow-forms"
                        />
                      )}
                    </div>
                    {/* HTML Code with edit functionality */}
                    <div className="border rounded mt-4">
                      <div className="w-full bg-[var(--color-bg-secondary)] px-3 py-2 text-sm font-medium border-b text-[var(--color-text-primary)] flex justify-between items-center">
                        <div className="flex-1 text-left flex items-center">
                          <button
                            type="button"
                            onClick={() => setShowCode(prev => ({ ...prev, [uniqueKey]: !prev[uniqueKey] }))}
                            className="flex items-center"
                          >
                            <span>HTML Code</span>
                            <span className="ml-2">{showCode[uniqueKey] ? '▼' : '▶'}</span>
                          </button>
                        </div>
                        <div className="flex space-x-2">
                          <button
                            type="button"
                            onClick={() => {
                              setIsEditing(prev => ({ ...prev, [uniqueKey]: !prev[uniqueKey] }));
                              // 編集モードをオンにするときはプレビューも表示
                              if (!isEditing[uniqueKey]) {
                                setShowPreview(prev => ({ ...prev, [uniqueKey]: true }));
                                setShowCode(prev => ({ ...prev, [uniqueKey]: true }));
                              }
                            }}
                            className="px-2 py-1 bg-blue-500 text-white rounded text-xs"
                          >
                            {isEditing[uniqueKey] ? '編集終了' : '編集する'}
                          </button>
                          <button
                            type="button"
                            onClick={() => copyToClipboard(editableHtml[uniqueKey] || cleanOutput)}
                            className="px-2 py-1 bg-green-500 text-white rounded text-xs"
                          >
                            コピー
                          </button>
                        </div>
                      </div>
                      {showCode[uniqueKey] && (
                        <div className="overflow-hidden">
                          {isEditing[uniqueKey] ? (
                            <textarea
                              ref={(el) => {
                                if (el) textareaRefs.current[uniqueKey] = el;
                              }}
                              value={editableHtml[uniqueKey]}
                              onChange={(e) => handleTextareaChange(uniqueKey, e)}
                              className="w-full p-2 font-mono text-sm h-64 bg-[var(--color-bg-primary)] text-[var(--color-text-primary)] border-none"
                            />
                          ) : (
                            <SyntaxHighlighter
                              language="html"
                              style={vscDarkPlus}
                              customStyle={{
                                margin: 0,
                                borderRadius: 0,
                                fontSize: '0.875rem',
                              }}
                            >
                              {editableHtml[uniqueKey] || cleanOutput}
                            </SyntaxHighlighter>
                          )}
                        </div>
                      )}
                    </div>
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

import { useState, useEffect, useRef, useCallback } from 'react';
import type { GenerationResponse, LLMResponse, PromptType } from "../types";
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/cjs/styles/prism';
import ReactMarkdown from 'react-markdown';

interface ResultDisplayProps {
  responses: LLMResponse[];
  plan?: string;
  promptType: PromptType;
}

export function ResultDisplay({ responses, plan, promptType }: ResultDisplayProps) {
  const [showCode, setShowCode] = useState<{[key: string]: boolean}>({});
  const [showPreview, setShowPreview] = useState<{[key: string]: boolean}>({});
  const [iframeHeights, setIframeHeights] = useState<{[key: string]: number}>({});
  const iframeRefs = useRef<{[key: string]: HTMLIFrameElement}>({});
  const [renderedResponses, setRenderedResponses] = useState<{[key: string]: boolean}>({});
  const [copyStatus, setCopyStatus] = useState<{[key: string]: string}>({});
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
      // iframeからの高さメッセージを処理
      if (event.data && typeof event.data === 'object' && 'height' in event.data && 'key' in event.data) {
        const { height, key } = event.data;
        if (height && typeof key === 'string') {
          setIframeHeights(prev => ({ ...prev, [key]: height }));
        }
      }
      
      // iframeからのAPIリクエストを処理
      if (event.data && typeof event.data === 'object' && 'type' in event.data && event.data.type === 'apiRequest') {
        const { url, options, requestId } = event.data;
        
        // 親ウィンドウでAPIリクエストを実行
        fetch(url, options)
          .then(response => {
            // レスポンスのContent-Typeを確認
            const contentType = response.headers.get('Content-Type') || '';
            
            // JSONの場合はJSON形式で解析、それ以外はテキスト形式で解析
            if (contentType.includes('application/json')) {
              return response.json().then(data => ({
                data,
                contentType,
                status: response.status,
                ok: response.ok
              }));
            }
            
            return response.text().then(text => ({
              data: text,
              contentType,
              status: response.status,
              ok: response.ok
            }));
          })
          .then(responseData => {
            // 結果をiframeに返す
            (event.source as Window)?.postMessage({
              type: 'apiResponse',
              requestId,
              data: responseData.data,
              contentType: responseData.contentType,
              status: responseData.status,
              ok: responseData.ok,
              error: null
            }, '*');
          })
          .catch(error => {
            // エラーをiframeに返す
            (event.source as Window)?.postMessage({
              type: 'apiResponse',
              requestId,
              data: null,
              contentType: null,
              status: 500,
              ok: false,
              error: error.message
            }, '*');
          });
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

  // マークダウンからHTMLコードブロックを抽出する関数
  const extractHtmlFromMarkdown = useCallback((text: string): { htmlCode: string, isMarkdown: boolean } => {
    // テキストモードの場合は単純にテキストを返す
    if (promptType === 'text') {
      return { 
        htmlCode: '', 
        isMarkdown: true 
      };
    }
    
    // HTMLコードブロックを検索（複数の言語指定に対応する正規表現）
    const htmlCodeBlockRegex = /```(?:html|HTML|javascript|js|jsx|ts|tsx)?\s*([\s\S]*?)(?:```|$)/g;
    const matches = [...text.matchAll(htmlCodeBlockRegex)];
    
    if (matches.length > 0) {
      // 最初のコードブロックを使用
      const code = matches[0][1].trim();
      
      // コードがHTMLらしいかどうかをチェック
      const containsHtml = /<\/?[a-z][\s\S]*>/i.test(code);
      
      if (containsHtml) {
        // コードブロックが途中で切れている場合の処理
        // 開始タグと終了タグの数を比較
        const openTags = (code.match(/<[^\/][^>]*>/g) || []).length;
        const closeTags = (code.match(/<\/[^>]*>/g) || []).length;
        
        // 開始タグの方が多い場合、コードが途中で切れている可能性がある
        if (openTags > closeTags) {
          console.log(`コードブロックが不完全な可能性があります: 開始タグ=${openTags}, 終了タグ=${closeTags}`);
        }
        
        return { 
          htmlCode: code,
          isMarkdown: true
        };
      }
    }
    
    // マークダウン形式かどうかを判断（簡易的な判定）
    const hasMarkdownSyntax = /(?:^|\n)(?:#{1,6}\s|[*-]\s|\d+\.\s|>\s|`{1,3}|---|===)/.test(text);
    
    if (hasMarkdownSyntax) {
      // マークダウンだがHTMLコードブロックがない場合は空文字を返す
      return { htmlCode: '', isMarkdown: true };
    }
    
    // マークダウンでない場合はそのまま返す
    return { htmlCode: text, isMarkdown: false };
  }, [promptType]);

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
        // extractHtmlFromMarkdownを使用して初期値を設定
        const { htmlCode } = extractHtmlFromMarkdown(response.output);
        newEditableHtml[uniqueKey] = htmlCode;
      }
      
      setEditableHtml(newEditableHtml);
    }
  }, [responses, editableHtml, extractHtmlFromMarkdown]);

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
          // マークダウンからHTMLコードを抽出
          const { htmlCode, isMarkdown } = extractHtmlFromMarkdown(result.output);
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
                    {/* テキストモードとウェブアプリモードで表示を分ける */}
                    {promptType === 'text' ? (
                      <div className="p-4 bg-[var(--color-bg-secondary)] rounded">
                        <div className="prose prose-invert max-w-none">
                          <ReactMarkdown>
                            {result.output}
                          </ReactMarkdown>
                        </div>
                      </div>
                    ) : (
                      <>
                        {/* マークダウンの場合は警告を表示 */}
                        {isMarkdown && htmlCode === '' && (
                          <div className="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 mb-4">
                            <p className="font-bold">マークダウン形式のレスポンス</p>
                            <p>HTMLコードブロックが見つかりませんでした。プレビューは表示できません。</p>
                          </div>
                        )}
                        
                        {/* 文字数表示 */}
                        <div className="mb-2 text-sm text-[var(--color-text-secondary)]">
                          文字数: {countCharacters(editableHtml[uniqueKey] || htmlCode)}
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
                            <div className="flex items-center space-x-3">
                              <span className="text-xs text-[var(--color-text-secondary)]">
                                {(editableHtml[uniqueKey] || htmlCode).length} 文字
                              </span>
                              <button
                                type="button"
                                onClick={() => copyToClipboard(editableHtml[uniqueKey] || htmlCode, uniqueKey)}
                                className="text-xs bg-[var(--color-accent)] text-white px-2 py-1 rounded hover:bg-opacity-80 transition-colors"
                              >
                                {copyStatus[uniqueKey] || 'コピー'}
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
                                <base href="${window.location.origin}/">
                                ${editableHtml[uniqueKey] || htmlCode}
                                <script>
                                  // プロキシAPIリクエスト用のヘルパー関数
                                  window.proxyFetch = function(url, options = {}) {
                                    return new Promise((resolve, reject) => {
                                      const requestId = Date.now().toString() + Math.random().toString(36).substr(2, 9);
                                      
                                      // レスポンスハンドラを設定
                                      const handleResponse = function(event) {
                                        if (event.data && event.data.type === 'apiResponse' && event.data.requestId === requestId) {
                                          window.removeEventListener('message', handleResponse);
                                          
                                          if (event.data.error) {
                                            reject(new Error(event.data.error));
                                          } else {
                                            resolve({
                                              data: event.data.data,
                                              contentType: event.data.contentType,
                                              status: event.data.status,
                                              ok: event.data.ok
                                            });
                                          }
                                        }
                                      };
                                      
                                      window.addEventListener('message', handleResponse);
                                      
                                      // 親ウィンドウにリクエストを送信
                                      window.parent.postMessage({
                                        type: 'apiRequest',
                                        url,
                                        options,
                                        requestId
                                      }, '*');
                                    });
                                  };
                                  
                                  // 元のfetchをオーバーライド
                                  const originalFetch = window.fetch;
                                  window.fetch = function(url, options) {
                                    // APIリクエストの場合はプロキシを使用
                                    if (url.toString().includes('/api/')) {
                                      return new Promise((resolve, reject) => {
                                        proxyFetch(url, options)
                                          .then(responseData => {
                                            // Response風のオブジェクトを作成
                                            const response = {
                                              ok: responseData.ok,
                                              status: responseData.status,
                                              headers: new Headers({
                                                'Content-Type': responseData.contentType || 'application/json'
                                              }),
                                              json: function() {
                                                // JSONの場合はそのまま返す
                                                if (typeof responseData.data === 'object') {
                                                  return Promise.resolve(responseData.data);
                                                }
                                                
                                                // テキストの場合はJSONとしてパースを試みる
                                                try {
                                                  return Promise.resolve(JSON.parse(responseData.data));
                                                } catch (e) {
                                                  // JSONパースエラーの場合、エラーオブジェクトがあればそれを返す
                                                  if (responseData.data && typeof responseData.data === 'string') {
                                                    try {
                                                      // レスポンスがJSONエラーオブジェクトかどうかを確認
                                                      const errorObj = JSON.parse(responseData.data);
                                                      if (errorObj && errorObj.error && errorObj.text) {
                                                        // エラーメッセージとテキストを含むオブジェクトを返す
                                                        return Promise.resolve(errorObj);
                                                      }
                                                    } catch (innerError) {
                                                      // 二重のJSONパースエラー、無視
                                                    }
                                                  }
                                                  
                                                  // それ以外の場合はエラーを投げる
                                                  return Promise.reject(new Error('Unexpected token, response is not valid JSON: ' + responseData.data.substring(0, 50) + '...'));
                                                }
                                              },
                                              text: function() {
                                                return Promise.resolve(
                                                  typeof responseData.data === 'string' 
                                                    ? responseData.data 
                                                    : JSON.stringify(responseData.data)
                                                );
                                              }
                                            };
                                            resolve(response);
                                          })
                                          .catch(error => {
                                            reject(error);
                                          });
                                      });
                                    }
                                    
                                    // それ以外は元のfetchを使用
                                    return originalFetch(url, options);
                                  };
                                  
                                  // 高さ調整用のスクリプト
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
                          {showPreview[uniqueKey] && !htmlCode && isMarkdown && (
                            <div className="p-4 bg-white">
                              <p className="text-gray-500 italic">プレビューできるHTMLコードがありません</p>
                            </div>
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
                                <span>{isMarkdown ? "Full Response" : "HTML Code"}</span>
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
                                onClick={() => copyToClipboard(isMarkdown ? result.output : (editableHtml[uniqueKey] || htmlCode), `code-${uniqueKey}`)}
                                className="px-2 py-1 bg-green-500 text-white rounded text-xs"
                              >
                                {copyStatus[`code-${uniqueKey}`] || 'コピー'}
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
                                  value={editableHtml[uniqueKey] || htmlCode}
                                  onChange={(e) => handleTextareaChange(uniqueKey, e)}
                                  className="w-full p-2 font-mono text-sm h-64 bg-[var(--color-bg-primary)] text-[var(--color-text-primary)] border-none"
                                />
                              ) : (
                                <SyntaxHighlighter
                                  language={isMarkdown ? "markdown" : "html"}
                                  style={vscDarkPlus}
                                  customStyle={{
                                    margin: 0,
                                    borderRadius: 0,
                                    fontSize: '0.875rem',
                                  }}
                                >
                                  {isMarkdown ? result.output : (editableHtml[uniqueKey] || htmlCode)}
                                </SyntaxHighlighter>
                              )}
                            </div>
                          )}
                        </div>
                      </>
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

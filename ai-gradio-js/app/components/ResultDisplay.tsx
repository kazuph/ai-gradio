import { useState, useEffect, useRef } from 'react';
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

  // バッククオートを削除する関数
  const removeBackticks = (str: string): string => {
    // 先頭と末尾のマークダウンコードブロック記法を削除
    return str.replace(/^```[\w]*\n/, '').replace(/\n```$/, '');
  };

  // 最新の結果が上に表示されるように並び替え
  const sortedResponses = [...responses].sort((a, b) => {
    return (b.startTime || 0) - (a.startTime || 0);
  });

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
                    {result.endTime && ` - ${formatTimestamp(result.endTime)}`}
                  </span>
                </div>
              </div>
              <div className="p-4">
                {result.error ? (
                  <div className="text-red-400">{result.error}</div>
                ) : (
                  <div className="space-y-4">
                    {/* Preview of the generated HTML */}
                    <div className="border rounded overflow-hidden">
                      <button
                        type="button"
                        onClick={() => setShowPreview(prev => ({ ...prev, [uniqueKey]: !prev[uniqueKey] }))}
                        className="w-full bg-[var(--color-bg-secondary)] px-3 py-2 text-sm font-medium border-b text-[var(--color-text-primary)] flex justify-between items-center hover:bg-opacity-80 transition-colors"
                      >
                        <span>Preview</span>
                        <span>{showPreview[uniqueKey] ? '▼' : '▶'}</span>
                      </button>
                      {showPreview[uniqueKey] && (
                        <iframe
                          title={`Preview ${result.model}`}
                          ref={(el) => {
                            if (el) iframeRefs.current[uniqueKey] = el;
                          }}
                          srcDoc={`
                            <base href="${window.location.origin}/">
                            ${cleanOutput}
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
                    </div>
                    {/* Raw HTML code */}
                    <div className="border rounded">
                      <button
                        type="button"
                        onClick={() => setShowCode(prev => ({ ...prev, [uniqueKey]: !prev[uniqueKey] }))}
                        className="w-full bg-[var(--color-bg-secondary)] px-3 py-2 text-sm font-medium border-b text-[var(--color-text-primary)] flex justify-between items-center hover:bg-opacity-80 transition-colors"
                      >
                        <span>HTML Code</span>
                        <span>{showCode[uniqueKey] ? '▼' : '▶'}</span>
                      </button>
                      {showCode[uniqueKey] && (
                        <div className="overflow-hidden">
                          <SyntaxHighlighter
                            language="html"
                            style={vscDarkPlus}
                            customStyle={{
                              margin: 0,
                              borderRadius: 0,
                              fontSize: '0.875rem',
                            }}
                          >
                            {cleanOutput}
                          </SyntaxHighlighter>
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

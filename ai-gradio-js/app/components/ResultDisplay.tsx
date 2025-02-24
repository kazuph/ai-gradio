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

  // 初期状態ではすべてのプレビューを表示
  useEffect(() => {
    const initialShowPreview: {[key: string]: boolean} = {};
    responses.forEach((result) => {
      const uniqueKey = `${result.model}-${result.startTime}`;
      initialShowPreview[uniqueKey] = true;
    });
    setShowPreview(initialShowPreview);
  }, [responses]);

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
                            ${cleanOutput}
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

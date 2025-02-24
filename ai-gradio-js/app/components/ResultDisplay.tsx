import { useState, useEffect, useRef } from 'react';
import type { GenerationResponse } from "../types";
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/cjs/styles/prism';

interface ResultDisplayProps {
  response: GenerationResponse | null;
}

export function ResultDisplay({ response }: ResultDisplayProps) {
  const [showCode, setShowCode] = useState<{[key: number]: boolean}>({});
  const [iframeHeights, setIframeHeights] = useState<{[key: number]: number}>({});
  const iframeRefs = useRef<{[key: number]: HTMLIFrameElement}>({});

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const { height, index } = event.data;
      if (height && typeof index === 'number') {
        setIframeHeights(prev => ({ ...prev, [index]: height }));
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  // バッククオートを削除する関数
  const removeBackticks = (str: string): string => {
    // 先頭と末尾のマークダウンコードブロック記法を削除
    return str.replace(/^```[\w]*\n/, '').replace(/\n```$/, '');
  };

  console.log('🚀 Response:', response);
  if (!response) return null;

  console.log('🚀 Response:', response.results[0].output);

  return (
    <div className="space-y-6">
      {response.plan && (
        <div className="card p-4">
          <h3 className="text-lg font-medium text-[var(--color-text-primary)] mb-2">
            Implementation Plan
          </h3>
          <pre className="whitespace-pre-wrap text-sm text-[var(--color-text-secondary)]">
            {response.plan}
          </pre>
        </div>
      )}

      <div className="space-y-4">
        {response.results.map((result, index) => {
          // outputからバッククオートを削除
          const cleanOutput = removeBackticks(result.output);
          // 一意のキーを作成
          const uniqueKey = `${result.model}-${index}`;
          
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
                      <div className="bg-[var(--color-bg-secondary)] px-3 py-2 text-sm font-medium border-b text-[var(--color-text-primary)]">
                        Preview
                      </div>
                      <iframe
                        title={`Preview ${result.model}`}
                        ref={(el) => {
                          if (el) iframeRefs.current[index] = el;
                        }}
                        srcDoc={`
                          ${cleanOutput}
                          <script>
                            window.addEventListener('load', function() {
                              const height = document.documentElement.scrollHeight;
                              window.parent.postMessage({ height, index: ${index} }, '*');
                            });
                          </script>
                        `}
                        className="w-full bg-white transition-height duration-200 ease-in-out"
                        style={{ height: `${iframeHeights[index] || 500}px` }}
                        sandbox="allow-scripts allow-forms"
                      />
                    </div>
                    {/* Raw HTML code */}
                    <div className="border rounded">
                      <button
                        type="button"
                        onClick={() => setShowCode(prev => ({ ...prev, [index]: !prev[index] }))}
                        className="w-full bg-[var(--color-bg-secondary)] px-3 py-2 text-sm font-medium border-b text-[var(--color-text-primary)] flex justify-between items-center hover:bg-opacity-80 transition-colors"
                      >
                        <span>HTML Code</span>
                        <span>{showCode[index] ? '▼' : '▶'}</span>
                      </button>
                      {showCode[index] && (
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

import type { GenerationResponse } from "../types";

interface ResultDisplayProps {
  response: GenerationResponse | null;
}

export function ResultDisplay({ response }: ResultDisplayProps) {
  console.log('🚀 Response:', response);
  if (!response) return null;

  console.log('🚀 Response:', response.results[0].output);

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString();
  };


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
        {response.results.map((result, index) => (
          <div
            key={index}
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
                    <div className="bg-gray-100 px-3 py-2 text-sm font-medium border-b">Preview</div>
                    <iframe
                      srcDoc={result.output}
                      className="w-full h-[500px] bg-white"
                      sandbox="allow-scripts allow-forms"
                    />
                  </div>
                  {/* Raw HTML code */}
                  <div className="border rounded">
                    <div className="bg-gray-100 px-3 py-2 text-sm font-medium border-b">HTML Code</div>
                    <pre className="whitespace-pre-wrap text-sm p-4 overflow-x-auto">
                      {result.output}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

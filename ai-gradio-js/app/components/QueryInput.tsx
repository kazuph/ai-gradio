interface QueryInputProps {
  query: string;
  onChange: (query: string) => void;
  isLoading: boolean;
  completedRequests?: number;
  totalRequests?: number;
}

export function QueryInput({
  query,
  onChange,
  isLoading,
  completedRequests = 0,
  totalRequests = 0,
}: QueryInputProps) {
  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-[var(--color-text-primary)]">
        Enter your query
      </label>
      <div className="space-y-2">
        <textarea
          name="query"
          value={query}
          onChange={(e) => onChange(e.target.value)}
          className="input-field flex-1 min-h-[150px] w-full"
          placeholder="Enter your query here..."
        />
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="btn-primary w-40"
          >
            {isLoading 
              ? `Generating... ${completedRequests}/${totalRequests}`
              : "Generate"}
          </button>
        </div>
      </div>
    </div>
  );
}

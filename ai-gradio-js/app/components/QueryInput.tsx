interface QueryInputProps {
  query: string;
  onChange: (query: string) => void;
  isLoading: boolean;
}

export function QueryInput({
  query,
  onChange,
  isLoading,
}: QueryInputProps) {
  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-[var(--color-text-primary)]">
        Enter your query
      </label>
      <div className="flex space-x-2">
        <textarea
          name="query"
          value={query}
          onChange={(e) => onChange(e.target.value)}
          className="input-field flex-1 min-h-[100px]"
          placeholder="Enter your query here..."
        />
        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="btn-primary"
        >
          {isLoading ? "Generating..." : "Generate"}
        </button>
      </div>
    </div>
  );
}

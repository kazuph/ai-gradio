import { MODEL_CATEGORIES } from "../constants/models";
import type { ModelType } from "../types";

interface ModelSelectorProps {
  selectedModels: ModelType[];
  onChange: (models: ModelType[]) => void;
}

export function ModelSelector({ selectedModels, onChange }: ModelSelectorProps) {
  const handleModelChange = (model: ModelType) => {
    const newSelectedModels = selectedModels.includes(model)
      ? selectedModels.filter((m) => m !== model)
      : [...selectedModels, model];
    onChange(newSelectedModels);
  };

  return (
    <div className="space-y-4">
      <label className="block text-sm font-medium text-[var(--color-text-primary)]">
        Select Models
      </label>
      <div className="space-y-6">
        {Object.entries(MODEL_CATEGORIES).map(([category, models]) => (
          <div key={category} className="space-y-2">
            <h3 className="text-sm font-medium text-[var(--color-text-primary)] border-b border-[var(--color-border)] pb-1">
              {category}
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
              {models.map((model) => (
                <label
                  key={model}
                  className="flex items-center space-x-2 cursor-pointer hover:bg-[var(--color-bg-secondary)] p-2 rounded-md transition-colors duration-200"
                >
                  <input
                    type="checkbox"
                    checked={selectedModels.includes(model)}
                    onChange={() => handleModelChange(model)}
                    className="rounded border-[var(--color-border)] bg-[var(--color-bg-secondary)] text-[var(--color-accent)] focus:ring-[var(--color-accent)]"
                  />
                  <span className="text-sm text-[var(--color-text-secondary)]">
                    {model.split(':')[1]}
                  </span>
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

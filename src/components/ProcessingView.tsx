interface ProcessingViewProps {
  current: number;
  total: number;
  fileName: string;
  phase?: string;
}

export function ProcessingView({
  current,
  total,
  fileName,
  phase = "Analisando",
}: ProcessingViewProps) {
  const progress = total > 0 ? (current / total) * 100 : 0;
  const isDone = current === total && total > 0;

  return (
    <div className="flex h-full items-center justify-center">
      <div className="w-full max-w-md animate-fade-in px-8 text-center">
        {/* Circular progress */}
        <div className="relative mx-auto mb-8 h-24 w-24">
          <svg className="h-24 w-24 -rotate-90" viewBox="0 0 96 96">
            <circle
              cx="48" cy="48" r="40"
              fill="none"
              stroke="var(--color-border)"
              strokeWidth="5"
            />
            <circle
              cx="48" cy="48" r="40"
              fill="none"
              stroke="var(--color-accent)"
              strokeWidth="5"
              strokeLinecap="round"
              strokeDasharray={`${progress * 2.51} 251`}
              className="transition-all duration-700 ease-out"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-bold text-accent tabular-nums">
              {Math.round(progress)}%
            </span>
          </div>
        </div>

        {/* Status */}
        <h2 className="text-lg font-semibold text-text">
          {isDone ? "Finalizando..." : `${phase}`}
        </h2>

        <div className="mt-4 rounded-lg bg-surface-raised/70 px-4 py-3">
          <div className="flex items-center justify-between text-[12px]">
            <span className="text-text-tertiary">Arquivo</span>
            <span className="font-medium text-text tabular-nums">
              {current} de {total}
            </span>
          </div>
          <p className="mt-1.5 truncate text-left text-[13px] font-medium text-accent">
            {fileName}
          </p>
        </div>

        {/* Step indicators */}
        <div className="mt-6 flex items-center justify-center gap-3">
          {Array.from({ length: total }, (_, i) => (
            <div
              key={i}
              className={`h-1.5 rounded-full transition-all duration-500 ${
                i < current
                  ? "w-6 bg-accent"
                  : i === current - 1
                    ? "w-6 bg-accent animate-pulse-soft"
                    : "w-1.5 bg-border"
              }`}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

import { useState } from "react";
import type { ProcessedFile } from "../types";
import { ALL_ENTITIES } from "../types";

interface PreviewViewProps {
  files: ProcessedFile[];
  onSaveAll: () => void;
  onDownloadFile: (file: ProcessedFile) => void;
  onBack: () => void;
}

export function PreviewView({
  files,
  onSaveAll,
  onDownloadFile,
  onBack,
}: PreviewViewProps) {
  const [activeIndex, setActiveIndex] = useState(0);

  if (files.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-text-tertiary">
        Nenhum arquivo processado.
      </div>
    );
  }

  const safeIndex = Math.min(activeIndex, files.length - 1);
  const activeFile = files[safeIndex];

  // Conta entidades por tipo
  const entityCounts: Record<string, number> = {};
  for (const entity of activeFile.entitiesFound) {
    entityCounts[entity.type] = (entityCounts[entity.type] || 0) + 1;
  }

  const totalEntities = activeFile.entitiesFound.length;

  // Nome do arquivo de saída
  const getOutputName = (name: string) => {
    const ext = name.lastIndexOf(".");
    const base = ext > 0 ? name.slice(0, ext) : name;
    const extension = ext > 0 ? name.slice(ext) : ".txt";
    return `${base}_anonimizado${extension}`;
  };

  return (
    <div className="flex h-full flex-col animate-fade-in">
      {/* Sticky toolbar */}
      <div className="shrink-0 border-b border-border-subtle bg-surface px-6 py-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <button
              onClick={onBack}
              aria-label="Voltar para seleção de arquivos"
              className="flex shrink-0 items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-[13px] text-text-secondary transition hover:bg-surface-hover hover:text-text"
            >
              <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M15 19l-7-7 7-7" />
              </svg>
              Voltar
            </button>

            {/* File tabs */}
            {files.length > 1 && (
              <div className="flex min-w-0 gap-1 overflow-x-auto rounded-lg bg-surface-raised p-0.5">
                {files.map((file, i) => (
                  <button
                    key={file.originalName}
                    onClick={() => setActiveIndex(i)}
                    className={`shrink-0 rounded-md px-2.5 py-1 text-[11px] font-medium whitespace-nowrap transition ${
                      i === safeIndex
                        ? "bg-accent text-white shadow-sm"
                        : "text-text-tertiary hover:text-text-secondary"
                    }`}
                  >
                    {file.originalName}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex shrink-0 items-center gap-2">
            {/* Download individual */}
            <button
              onClick={() => onDownloadFile(activeFile)}
              className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-[12px] font-medium text-text-secondary transition hover:bg-surface-hover hover:text-text"
              title={`Download: ${getOutputName(activeFile.originalName)}`}
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              Download
            </button>

            {/* Salvar (na mesma pasta do original) */}
            <button
              onClick={onSaveAll}
              className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-[13px] font-semibold whitespace-nowrap text-white shadow-sm transition hover:bg-accent-hover"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z" />
                <polyline points="17 21 17 13 7 13 7 21" />
                <polyline points="7 3 7 8 15 8" />
              </svg>
              Salvar {files.length > 1 ? `todos (${files.length})` : ""}
            </button>
          </div>
        </div>

        {/* Entity summary + output info */}
        <div className="mt-3 flex items-center justify-between">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="mr-1 text-[11px] font-medium text-text-tertiary">
              {totalEntities} entidade{totalEntities !== 1 ? "s" : ""}:
            </span>
            {Object.entries(entityCounts)
              .sort(([, a], [, b]) => b - a)
              .map(([type, count]) => {
                const info = ALL_ENTITIES.find((e) => e.id === type);
                return (
                  <span
                    key={type}
                    className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium"
                    style={{
                      backgroundColor: `${info?.color || "#666"}12`,
                      color: info?.color || "#94a3b8",
                      border: `1px solid ${info?.color || "#334155"}25`,
                    }}
                  >
                    <span
                      className="h-1.5 w-1.5 rounded-full"
                      style={{
                        backgroundColor: info?.color || "#94a3b8",
                      }}
                    />
                    {info?.label || type} {count}
                  </span>
                );
              })}
            {totalEntities === 0 && (
              <span className="text-[11px] text-text-tertiary">
                Nenhuma entidade encontrada
              </span>
            )}
          </div>

          {/* Output file name */}
          <span className="shrink-0 text-[11px] text-text-tertiary">
            {getOutputName(activeFile.originalName)}
          </span>
        </div>
      </div>

      {/* Scrollable preview */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-4xl p-6">
          {files.length === 1 && (
            <div className="mb-4 flex items-center gap-2">
              <svg className="h-4 w-4 text-text-tertiary" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span className="text-[13px] font-medium text-text-secondary">
                {activeFile.originalName}
              </span>
              <svg className="h-3 w-3 text-text-tertiary" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 5l7 7-7 7" />
              </svg>
              <span className="text-[13px] font-medium text-accent">
                {getOutputName(activeFile.originalName)}
              </span>
            </div>
          )}

          <div className="rounded-xl border border-border-subtle bg-surface p-6 shadow-sm">
            <pre className="whitespace-pre-wrap font-mono text-[13px] leading-[1.7] text-text-secondary">
              {activeFile.anonymizedContent}
            </pre>
          </div>

          {/* Bottom action bar — sempre visível após scroll */}
          <div className="mt-6 flex items-center justify-between rounded-xl border border-border-subtle bg-surface-raised p-4">
            <div>
              <p className="text-[13px] font-medium text-text">
                Pronto para salvar?
              </p>
              <p className="mt-0.5 text-[11px] text-text-tertiary">
                O arquivo será salvo na mesma pasta do original
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => onDownloadFile(activeFile)}
                className="flex items-center gap-1.5 rounded-lg border border-border px-4 py-2 text-[12px] font-medium text-text-secondary transition hover:bg-surface-hover hover:text-text"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                Download
              </button>
              <button
                onClick={onSaveAll}
                className="flex items-center gap-2 rounded-lg bg-accent px-5 py-2 text-[13px] font-semibold text-white shadow-sm transition hover:bg-accent-hover"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z" />
                  <polyline points="17 21 17 13 7 13 7 21" />
                  <polyline points="7 3 7 8 15 8" />
                </svg>
                Salvar
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

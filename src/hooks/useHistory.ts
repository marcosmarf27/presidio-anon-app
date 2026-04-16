import { useState, useCallback, useEffect } from "react";
import type { HistoryItem, ProcessedFile } from "../types";

const STORAGE_KEY = "presidio-anon-history";
const MAX_HISTORY = 50;

export function useHistory() {
  const [items, setItems] = useState<HistoryItem[]>([]);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        setItems(JSON.parse(stored));
      }
    } catch {
      // localStorage vazio ou corrompido
    }
  }, []);

  const save = useCallback((newItems: HistoryItem[]) => {
    const trimmed = newItems.slice(0, MAX_HISTORY);
    setItems(trimmed);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
    } catch {
      // localStorage cheio — remove itens antigos
      const reduced = trimmed.slice(0, 10);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(reduced));
      setItems(reduced);
    }
  }, []);

  const addEntry = useCallback(
    (files: ProcessedFile[]) => {
      const entityBreakdown: Record<string, number> = {};
      let totalEntities = 0;
      for (const file of files) {
        for (const e of file.entitiesFound) {
          entityBreakdown[e.type] = (entityBreakdown[e.type] || 0) + 1;
          totalEntities++;
        }
      }

      const entry: HistoryItem = {
        id: crypto.randomUUID(),
        date: new Date().toISOString(),
        fileNames: files.map((f) => f.originalName),
        totalEntities,
        entityBreakdown,
        results: files,
      };

      save([entry, ...items]);
      return entry;
    },
    [items, save]
  );

  const removeEntry = useCallback(
    (id: string) => {
      save(items.filter((item) => item.id !== id));
    },
    [items, save]
  );

  const clearHistory = useCallback(() => {
    save([]);
  }, [save]);

  return { items, addEntry, removeEntry, clearHistory };
}

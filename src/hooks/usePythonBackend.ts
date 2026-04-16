import { useState, useEffect, useCallback } from "react";
import type { AnonymizeResponse, EntityType } from "../types";

type BackendStatus = "loading" | "ready" | "error";
type NlpMode = "transformer" | "spacy" | "unknown";

const API_BASE = "http://127.0.0.1:8123";

export function usePythonBackend() {
  const [status, setStatus] = useState<BackendStatus>("loading");
  const [nlpMode, setNlpMode] = useState<NlpMode>("unknown");

  useEffect(() => {
    let cancelled = false;
    let attempts = 0;
    // Até 180s: o modelo BERT pode levar ~60-120s para baixar na 1ª execução.
    const maxAttempts = 180;

    const checkHealth = async () => {
      try {
        const res = await fetch(`${API_BASE}/health`);
        const data = await res.json();
        if (!cancelled) {
          if (data.nlp_mode) setNlpMode(data.nlp_mode);
          if (data.status === "ready") {
            setStatus("ready");
            return;
          }
        }
      } catch {
        // Servidor ainda não iniciou
      }

      attempts++;
      if (!cancelled && attempts < maxAttempts) {
        setTimeout(checkHealth, 1000);
      } else if (!cancelled) {
        setStatus("error");
      }
    };

    checkHealth();
    return () => {
      cancelled = true;
    };
  }, []);

  const extractText = useCallback(
    async (content: string, format: string): Promise<string> => {
      const res = await fetch(`${API_BASE}/extract-text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, format }),
      });

      if (!res.ok) {
        throw new Error(`Erro ao extrair texto: ${res.status}`);
      }

      const data = await res.json();
      return data.text;
    },
    []
  );

  const anonymize = useCallback(
    async (
      text: string,
      entities: EntityType[]
    ): Promise<AnonymizeResponse> => {
      const res = await fetch(`${API_BASE}/anonymize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, entities, language: "pt" }),
      });

      if (!res.ok) {
        throw new Error(`Erro no backend: ${res.status}`);
      }

      return res.json();
    },
    []
  );

  return { status, nlpMode, anonymize, extractText };
}

"use client";

import { useState, useCallback } from "react";

// Подставь свой базовый URL API / способ получения access token —
// здесь предполагается, что fetch к бэкенду уже настроен с credentials
// (cookie-based auth) или ты добавишь Authorization header сам.
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

type UploadStage =
  | "idle"
  | "creating" // POST /kits/upload-url
  | "uploading" // PUT напрямую в S3
  | "confirming" // POST /kits/{id}/confirm-upload
  | "done"
  | "error";

interface KitMetadata {
  title: string;
  genre: string;
  tags: string; // comma-separated, как ожидает бэкенд
  description?: string;
}

interface UseKitUploadResult {
  stage: UploadStage;
  progress: number; // 0-100, реальный прогресс PUT-запроса в S3
  error: string | null;
  kitSlug: string | null;
  upload: (file: File, metadata: KitMetadata) => Promise<void>;
  reset: () => void;
}

export function useKitUpload(): UseKitUploadResult {
  const [stage, setStage] = useState<UploadStage>("idle");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [kitSlug, setKitSlug] = useState<string | null>(null);

  const reset = useCallback(() => {
    setStage("idle");
    setProgress(0);
    setError(null);
    setKitSlug(null);
  }, []);

  const upload = useCallback(async (file: File, metadata: KitMetadata) => {
    setError(null);
    setProgress(0);

    try {
      // Шаг 1 — создаём кит в БД (status=pending) и получаем presigned URL.
      // Файл ещё не грузится.
      setStage("creating");
      const initRes = await fetch(`${API_BASE}/api/v1/kits/upload-url`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: metadata.title,
          genre: metadata.genre,
          tags: metadata.tags,
          description: metadata.description ?? null,
          content_type: file.type || "application/zip",
        }),
      });

      if (!initRes.ok) {
        const body = await initRes.json().catch(() => null);
        throw new Error(body?.detail ?? `Не удалось создать кит (${initRes.status})`);
      }

      const { kit_id, slug, upload_url } = await initRes.json();
      setKitSlug(slug);

      // Шаг 2 — грузим файл НАПРЯМУЮ в S3, минуя наш сервер.
      // Используем XMLHttpRequest вместо fetch, т.к. fetch не даёт
      // прогресс отправки (upload progress), а для большого zip это важно.
      setStage("uploading");
      await putWithProgress(upload_url, file, setProgress);

      // Шаг 3 — сообщаем бэкенду, что файл долетел. Сервер сам проверит
      // это через head_object и поставит job в очередь на распаковку.
      setStage("confirming");
      const confirmRes = await fetch(
        `${API_BASE}/api/v1/kits/${kit_id}/confirm-upload`,
        { method: "POST", credentials: "include" }
      );

      if (!confirmRes.ok) {
        const body = await confirmRes.json().catch(() => null);
        throw new Error(
          body?.detail ?? `Не удалось подтвердить загрузку (${confirmRes.status})`
        );
      }

      setStage("done");
    } catch (e) {
      setStage("error");
      setError(e instanceof Error ? e.message : "Неизвестная ошибка загрузки");
    }
  }, []);

  return { stage, progress, error, kitSlug, upload, reset };
}

/**
 * PUT файла с реальным прогрессом через XMLHttpRequest.
 * fetch() не умеет отдавать upload progress до сих пор, поэтому для
 * прогресс-бара при заливке большого zip нужен именно XHR.
 */
function putWithProgress(
  url: string,
  file: File,
  onProgress: (percent: number) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url, true);
    xhr.setRequestHeader("Content-Type", file.type || "application/zip");

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        onProgress(100);
        resolve();
      } else {
        reject(new Error(`S3 вернул ошибку при загрузке: ${xhr.status}`));
      }
    };

    xhr.onerror = () => reject(new Error("Сетевая ошибка при загрузке файла в хранилище"));
    xhr.onabort = () => reject(new Error("Загрузка отменена"));

    xhr.send(file);
  });
}
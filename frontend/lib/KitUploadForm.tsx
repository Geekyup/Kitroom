"use client";

import { useState } from "react";
import { useKitUpload } from "@/lib/useKitUpload";

export function KitUploadForm() {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [genre, setGenre] = useState("");
  const [tags, setTags] = useState("");
  const [description, setDescription] = useState("");

  const { stage, progress, error, kitSlug, upload, reset } = useKitUpload();

  const isBusy = stage === "creating" || stage === "uploading" || stage === "confirming";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !title || !genre) return;
    await upload(file, { title, genre, tags, description });
  };

  const stageLabel: Record<string, string> = {
    idle: "",
    creating: "Создаём кит…",
    uploading: `Загружаем файл в хранилище… ${progress}%`,
    confirming: "Проверяем загрузку и ставим в очередь…",
    done: "Готово! Кит поставлен в очередь на обработку.",
    error: "Ошибка загрузки",
  };

  if (stage === "done") {
    return (
      <div>
        <p>{stageLabel.done}</p>
        {kitSlug && <p>Слаг кита: {kitSlug}</p>}
        <button onClick={reset}>Загрузить ещё один</button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Название кита"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        disabled={isBusy}
        required
      />
      <input
        type="text"
        placeholder="Жанр"
        value={genre}
        onChange={(e) => setGenre(e.target.value)}
        disabled={isBusy}
        required
      />
      <input
        type="text"
        placeholder="Теги через запятую"
        value={tags}
        onChange={(e) => setTags(e.target.value)}
        disabled={isBusy}
      />
      <textarea
        placeholder="Описание"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        disabled={isBusy}
      />
      <input
        type="file"
        accept=".zip"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        disabled={isBusy}
        required
      />

      <button type="submit" disabled={isBusy || !file}>
        Загрузить
      </button>

      {isBusy && (
        <div>
          <progress value={stage === "uploading" ? progress : undefined} max={100} />
          <p>{stageLabel[stage]}</p>
        </div>
      )}

      {stage === "error" && (
        <div>
          <p style={{ color: "red" }}>{error}</p>
          <button onClick={reset}>Попробовать снова</button>
        </div>
      )}
    </form>
  );
}
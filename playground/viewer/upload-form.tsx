/** The upload form: sends a DOCX or PDF to the playground's server, which renders and stores it. */
"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

/** Upload the chosen file to /api/documents, then refresh the list, or show why it failed. */
export function UploadForm() {
  const router = useRouter();
  const [uploadStatus, setUploadStatus] = useState<string>("");
  const [uploading, setUploading] = useState(false);

  /** Send the form's file and react to the answer. */
  async function submitUpload(submitEvent: FormEvent<HTMLFormElement>) {
    submitEvent.preventDefault();
    setUploading(true);
    setUploadStatus("Rendering…");
    const answer = await fetch("/api/documents", { method: "POST", body: new FormData(submitEvent.currentTarget) });
    const answerBody = (await answer.json()) as { id?: string; code?: string; message?: string };
    setUploading(false);
    if (answer.ok && answerBody.id) {
      setUploadStatus("Stored.");
      router.refresh(); // the home page lists it
    } else {
      setUploadStatus(`Not stored: ${answerBody.message ?? "unknown error"} (${answerBody.code ?? answer.status})`);
    }
  }

  return (
    <form onSubmit={submitUpload} style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
      <input type="file" name="document" accept=".docx,.pdf,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" required />
      <button type="submit" disabled={uploading}>
        {uploading ? "Uploading…" : "Upload"}
      </button>
      <span role="status">{uploadStatus}</span>
    </form>
  );
}

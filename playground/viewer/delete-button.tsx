/** The delete button: asks first, deletes the document through the playground's server, then goes back to the list. */
"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

/** Delete this document after the user confirms, then return to the home page. */
export function DeleteButton({ documentId, fileName }: { documentId: string; fileName: string }) {
  const router = useRouter();
  const [deleting, setDeleting] = useState(false);

  /** Confirm, send the DELETE, and leave the page once it's gone. */
  async function confirmAndDelete() {
    if (!window.confirm(`Delete "${fileName}" and all its pages?`)) {
      return;
    }
    setDeleting(true);
    const answer = await fetch(`/api/documents/${documentId}`, { method: "DELETE" });
    if (answer.ok) {
      router.push("/");
      router.refresh();
    } else {
      setDeleting(false);
      window.alert("The document could not be deleted.");
    }
  }

  return (
    <button type="button" onClick={confirmAndDelete} disabled={deleting}>
      {deleting ? "Deleting…" : "Delete"}
    </button>
  );
}

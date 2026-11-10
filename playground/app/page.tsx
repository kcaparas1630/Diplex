/** The playground's home page: upload a DOCX or PDF, and the current browser's documents, newest first. */
import { cookies } from "next/headers";

import { getPlaygroundServices, listDocuments, readPlaygroundUser } from "../server";
import { UploadForm } from "../viewer";

export const dynamic = "force-dynamic"; // the list belongs to whoever is asking

/** Show the upload form and the list of this browser's documents. */
export default async function HomePage() {
  const ownerId = readPlaygroundUser(await cookies());
  const listedDocuments = ownerId ? await listDocuments(getPlaygroundServices().database, ownerId) : [];
  return (
    <>
      <h1>Diplex playground</h1>
      <p>Upload a DOCX or PDF: the playground&apos;s server sends it to the engine, keeps the results in its own bucket and database, and shows it page by page.</p>
      <UploadForm />
      <h2>Your documents</h2>
      {listedDocuments.length === 0 ? (
        <p>None yet.</p>
      ) : (
        <ul>
          {listedDocuments.map((listedDocument) => (
            <li key={listedDocument.id}>
              <a href={`/documents/${listedDocument.id}`}>{listedDocument.fileName}</a> · {listedDocument.sourceType.toUpperCase()} ·{" "}
              {listedDocument.pageCount} {listedDocument.pageCount === 1 ? "page" : "pages"}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

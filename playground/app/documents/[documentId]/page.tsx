/** A document's page: its name and type, download links, and the viewer laid out from its page sizes; only its owner sees it. */
import { cookies } from "next/headers";
import { notFound } from "next/navigation";

import { getOwnedDocument, getPlaygroundServices, readPlaygroundUser } from "../../../server";
import { DocumentViewer } from "../../../viewer";

export const dynamic = "force-dynamic";

/** Show the owner's document, or a 404 for anyone else. */
export default async function DocumentPage({ params }: { params: Promise<{ documentId: string }> }) {
  const { documentId } = await params;
  const ownedDocument = await getOwnedDocument(getPlaygroundServices().database, readPlaygroundUser(await cookies()), documentId);
  if (!ownedDocument) {
    notFound();
  }
  return (
    <>
      <p>
        <a href="/">← All documents</a>
      </p>
      <h1 style={{ wordBreak: "break-word" }}>{ownedDocument.fileName}</h1>
      <p>
        {ownedDocument.sourceType.toUpperCase()} · {ownedDocument.pageSizes.length} {ownedDocument.pageSizes.length === 1 ? "page" : "pages"} ·{" "}
        <a href={`/api/documents/${ownedDocument.id}/download?file=pdf`}>Download PDF</a>
        {ownedDocument.sourceType === "docx" ? (
          <>
            {" "}
            · <a href={`/api/documents/${ownedDocument.id}/download?file=original`}>Download original DOCX</a>
          </>
        ) : null}
      </p>
      <DocumentViewer documentId={ownedDocument.id} pageSizes={ownedDocument.pageSizes} />
    </>
  );
}

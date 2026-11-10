/** Signs a download URL for a document's PDF or original, named after the user's file, on demand and never stored. */
import type { S3Client } from "@aws-sdk/client-s3";

import { findOwnedDocumentRow, type SqlQueries } from "../database";
import { documentKeys, signGetUrl } from "../storage";

/** What signing a download needs: the database and the client that signs URLs browsers can reach. */
export interface DownloadSource {
  database: SqlQueries;
  signingClient: S3Client;
  bucketName: string;
}

/** Which file to download: the PDF (converted, or the uploaded PDF itself), or the original upload. */
export type DownloadKind = "pdf" | "original";

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

/** The name a download is saved under: the user's file name, with .pdf for the PDF of a DOCX. */
export function downloadFileName(fileName: string, downloadKind: DownloadKind): string {
  return downloadKind === "pdf" ? `${fileName.replace(/\.(docx|pdf)$/i, "")}.pdf` : fileName;
}

/** A Content-Disposition that saves the file under its name: a plain ASCII fallback, and the exact name in RFC 5987 form. */
export function attachmentDisposition(fileName: string): string {
  const asciiFallback = fileName.replace(/[^\x20-\x7e]/g, "_").replace(/["\\]/g, "_");
  const encodedName = encodeURIComponent(fileName).replace(/['()*]/g, (character) => `%${character.charCodeAt(0).toString(16).toUpperCase()}`);
  return `attachment; filename="${asciiFallback}"; filename*=UTF-8''${encodedName}`;
}

/** Sign a download URL for the owner's document, or return null for anyone else or an unknown ID. */
export async function getDownloadUrl(
  source: DownloadSource,
  ownerId: string | undefined,
  documentId: string,
  downloadKind: DownloadKind,
): Promise<string | null> {
  if (!ownerId || !UUID_PATTERN.test(documentId)) {
    return null;
  }
  const documentRow = await findOwnedDocumentRow(source.database, documentId, ownerId);
  if (!documentRow) {
    return null;
  }
  const objectKey = downloadKind === "pdf" ? documentKeys.pdf(documentRow.folder) : documentKeys.original(documentRow.folder, documentRow.sourceType);
  return signGetUrl(source.signingClient, source.bucketName, objectKey, attachmentDisposition(downloadFileName(documentRow.fileName, downloadKind)));
}

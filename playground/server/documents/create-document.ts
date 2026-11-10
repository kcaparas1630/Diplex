/** Stores one upload the way ADR 001 §5 says: render it, upload the files, write the row, and remove the files if that fails. */
import type { S3Client } from "@aws-sdk/client-s3";

import { insertDocumentRow, type DocumentRow, type SqlQueries } from "../database";
import { renderDocument, type EngineConnection, type RenderResult } from "../engine-client";
import { documentFolder, removeDocumentFolder, uploadDocumentFiles } from "../storage";

/** What storing a document needs: the engine, the bucket and the database. */
export interface DocumentStore {
  engine: EngineConnection;
  serverClient: S3Client;
  bucketName: string;
  folderPrefix: string;
  database: SqlQueries;
  render?: (engine: EngineConnection, documentBytes: Uint8Array, fileName: string) => Promise<RenderResult>;
}

/** One upload from a user. */
export interface Upload {
  ownerId: string;
  fileName: string;
  documentBytes: Uint8Array;
}

/** Render the upload, store its files and its row, and return the row; on any failure after rendering, leave no files. */
export async function createDocument(store: DocumentStore, upload: Upload): Promise<DocumentRow> {
  const renderResult = await (store.render ?? renderDocument)(store.engine, upload.documentBytes, upload.fileName);
  const documentId = crypto.randomUUID();
  const folder = documentFolder(store.folderPrefix, upload.ownerId, documentId);
  const sourceType = renderResult.convertedPdf ? "docx" : "pdf"; // only a DOCX comes back with a PDF (ADR 010)
  try {
    await uploadDocumentFiles(store.serverClient, store.bucketName, folder, {
      originalBytes: upload.documentBytes,
      sourceType,
      convertedPdf: renderResult.convertedPdf,
      pageImages: renderResult.pageImages,
    });
    return await insertDocumentRow(store.database, {
      id: documentId,
      ownerId: upload.ownerId,
      fileName: upload.fileName,
      folder,
      sourceType,
      pageSizes: renderResult.pageSizes,
    });
  } catch (storeError) {
    // A row that failed, or files that half uploaded, must not leave orphaned files behind (#87).
    await removeDocumentFolder(store.serverClient, store.bucketName, folder).catch(() => undefined);
    throw storeError;
  }
}

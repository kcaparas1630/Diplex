/** Writes a document's files to the bucket in ADR 001 §5's layout, named by document ID, never by the user's file name. */
import { CopyObjectCommand, PutObjectCommand, type S3Client } from "@aws-sdk/client-s3";

/** The kinds of document the playground keeps. */
export type SourceType = "docx" | "pdf";

/** What one upload leaves in the bucket: the original, the PDF to download, and one WebP per page. */
export interface DocumentFiles {
  originalBytes: Uint8Array;
  sourceType: SourceType;
  convertedPdf: Uint8Array | undefined;
  pageImages: Uint8Array[];
}

const PAGE_IMAGE_CACHE_CONTROL = "public, max-age=31536000, immutable"; // a page image never changes
const PAGE_UPLOADS_AT_ONCE = 8;
const CONTENT_TYPES: Record<SourceType, string> = {
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  pdf: "application/pdf",
};

/** The document's folder: {prefix}/{userId}/{documentId}. */
export function documentFolder(folderPrefix: string, ownerId: string, documentId: string): string {
  return `${folderPrefix}/${ownerId}/${documentId}`;
}

/** The key of the original upload, of the PDF to download, and of page N (1-based). */
export const documentKeys = {
  original: (folder: string, sourceType: SourceType) => `${folder}/original.${sourceType}`,
  pdf: (folder: string) => `${folder}/document.pdf`,
  page: (folder: string, pageNumber: number) => `${folder}/pages/page-${String(pageNumber).padStart(4, "0")}.webp`,
};

/** Upload the original, the PDF (the converted one, or a copy of an uploaded PDF) and every page image. */
export async function uploadDocumentFiles(client: S3Client, bucketName: string, folder: string, files: DocumentFiles): Promise<void> {
  const originalKey = documentKeys.original(folder, files.sourceType);
  await client.send(
    new PutObjectCommand({ Bucket: bucketName, Key: originalKey, Body: files.originalBytes, ContentType: CONTENT_TYPES[files.sourceType] }),
  );
  if (files.convertedPdf) {
    await client.send(
      new PutObjectCommand({ Bucket: bucketName, Key: documentKeys.pdf(folder), Body: files.convertedPdf, ContentType: CONTENT_TYPES.pdf }),
    );
  } else {
    // A PDF upload is its own PDF: copy it inside the bucket rather than upload it twice.
    await client.send(new CopyObjectCommand({ Bucket: bucketName, Key: documentKeys.pdf(folder), CopySource: `${bucketName}/${originalKey}` }));
  }
  for (let firstPage = 0; firstPage < files.pageImages.length; firstPage += PAGE_UPLOADS_AT_ONCE) {
    const pageBatch = files.pageImages.slice(firstPage, firstPage + PAGE_UPLOADS_AT_ONCE);
    await Promise.all(
      pageBatch.map((pageImage, offset) =>
        client.send(
          new PutObjectCommand({
            Bucket: bucketName,
            Key: documentKeys.page(folder, firstPage + offset + 1),
            Body: pageImage,
            ContentType: "image/webp",
            CacheControl: PAGE_IMAGE_CACHE_CONTROL,
          }),
        ),
      ),
    );
  }
}

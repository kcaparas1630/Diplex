/** The playground's documents: storing an upload (render, files, row), reading the browser's form, listing them, and
 * signing a range of their pages for the viewer and their files for download, and deleting them. */
export { createDocument } from "./create-document";
export type { DocumentStore, Upload } from "./create-document";
export { listDocuments } from "./list-documents";
export type { ListedDocument } from "./list-documents";
export { InvalidUploadError, describeUploadFailure, readUploadedFile } from "./upload-handling";
export type { UploadFailure, UploadedFile } from "./upload-handling";
export { DEFAULT_PAGES_PER_REQUEST, getDocumentPages } from "./document-pages";
export type { PageRange, PageSource, ViewerPage } from "./document-pages";
export { getOwnedDocument } from "./owned-document";
export type { OwnedDocument } from "./owned-document";
export { attachmentDisposition, downloadFileName, getDownloadUrl } from "./download-url";
export type { DownloadKind, DownloadSource } from "./download-url";
export { deleteDocument } from "./delete-document";
export type { DeletionTarget } from "./delete-document";

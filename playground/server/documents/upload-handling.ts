/** Reads an upload from the browser's form, and turns a failed upload into an answer the browser can show. */
import { EngineRenderError } from "../engine-client";

/** The file the browser sent. */
export interface UploadedFile {
  fileName: string;
  documentBytes: Uint8Array;
}

/** What the playground answers when an upload fails: a status, the engine's code when it had one, and a message. */
export interface UploadFailure {
  httpStatus: number;
  body: { code: string; message: string };
}

const MAX_UPLOAD_BYTES = 50 * 1024 * 1024; // the engine's default limit; the engine still checks its own
const MAX_FILE_NAME_LENGTH = 255;

/** A form that can't be stored, with the reason to show. */
export class InvalidUploadError extends Error {
  /** Name the error so callers can tell it apart. */
  constructor(message: string) {
    super(message);
    this.name = "InvalidUploadError";
  }
}

/** Read the `document` file from the form, refusing a missing, empty or oversized one. */
export async function readUploadedFile(uploadForm: FormData): Promise<UploadedFile> {
  const documentPart = uploadForm.get("document");
  if (!(documentPart instanceof Blob) || documentPart.size === 0) {
    throw new InvalidUploadError("choose a DOCX or PDF to upload");
  }
  if (documentPart.size > MAX_UPLOAD_BYTES) {
    throw new InvalidUploadError("the file is over 50 MB");
  }
  const fileName = ("name" in documentPart && typeof documentPart.name === "string" ? documentPart.name : "") || "document";
  return { fileName: fileName.slice(0, MAX_FILE_NAME_LENGTH), documentBytes: new Uint8Array(await documentPart.arrayBuffer()) };
}

/** Turn an upload's error into the answer for the browser: the engine's own status and code, or a plain 500. */
export function describeUploadFailure(uploadError: unknown): UploadFailure {
  if (uploadError instanceof InvalidUploadError) {
    return { httpStatus: 400, body: { code: "invalid_upload", message: uploadError.message } };
  }
  if (uploadError instanceof EngineRenderError) {
    return { httpStatus: uploadError.httpStatus, body: { code: uploadError.errorCode, message: uploadError.message } };
  }
  return { httpStatus: 500, body: { code: "playground_error", message: "the playground could not store the document" } };
}

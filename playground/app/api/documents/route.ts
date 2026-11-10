/** POST /api/documents stores an upload for the current browser's user; GET lists their documents. */
import { cookies } from "next/headers";

import {
  createDocument,
  describeUploadFailure,
  ensurePlaygroundUser,
  getDocumentStore,
  getPlaygroundServices,
  listDocuments,
  readPlaygroundUser,
  readUploadedFile,
} from "../../../server";

export const runtime = "nodejs";

/** Render the uploaded file, store its files and its row, and answer with its ID, or with why it failed. */
export async function POST(request: Request): Promise<Response> {
  const ownerId = ensurePlaygroundUser(await cookies());
  try {
    const uploadedFile = await readUploadedFile(await request.formData());
    const documentRow = await createDocument(getDocumentStore(), { ownerId, ...uploadedFile });
    return Response.json({ id: documentRow.id }, { status: 201 });
  } catch (uploadError) {
    const failure = describeUploadFailure(uploadError);
    if (failure.httpStatus >= 500) {
      console.error("upload failed:", (uploadError as Error).name, failure.body.code); // never the document's contents
    }
    return Response.json(failure.body, { status: failure.httpStatus });
  }
}

/** List the current user's documents, newest first; a browser without a user has none. */
export async function GET(): Promise<Response> {
  const ownerId = readPlaygroundUser(await cookies());
  const listedDocuments = ownerId ? await listDocuments(getPlaygroundServices().database, ownerId) : [];
  return Response.json({ documents: listedDocuments });
}

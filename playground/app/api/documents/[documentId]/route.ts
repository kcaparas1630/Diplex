/** DELETE /api/documents/[documentId]: deletes the owner's document, its row marked and its files removed. */
import { cookies } from "next/headers";

import { deleteDocument, getDocumentStore, readPlaygroundUser } from "../../../../server";

export const runtime = "nodejs";

/** Delete the document and answer 204; anyone but the owner, and an unknown ID, gets 404. */
export async function DELETE(_request: Request, context: { params: Promise<{ documentId: string }> }): Promise<Response> {
  const { documentId } = await context.params;
  const deleted = await deleteDocument(getDocumentStore(), readPlaygroundUser(await cookies()), documentId);
  return deleted ? new Response(null, { status: 204 }) : Response.json({ code: "not_found", message: "no such document" }, { status: 404 });
}

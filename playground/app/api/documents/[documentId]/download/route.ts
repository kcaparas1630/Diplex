/** GET /api/documents/[documentId]/download?file=pdf|original: redirects the owner to a signed URL named after their file. */
import { cookies } from "next/headers";

import { getDocumentStore, getDownloadUrl, readPlaygroundUser } from "../../../../../server";

export const runtime = "nodejs";

/** Redirect to a URL signed just now, never stored; anyone but the owner, and an unknown ID, gets 404. */
export async function GET(request: Request, context: { params: Promise<{ documentId: string }> }): Promise<Response> {
  const { documentId } = await context.params;
  const downloadKind = new URL(request.url).searchParams.get("file") === "original" ? "original" : "pdf";
  const downloadUrl = await getDownloadUrl(getDocumentStore(), readPlaygroundUser(await cookies()), documentId, downloadKind);
  if (!downloadUrl) {
    return Response.json({ code: "not_found", message: "no such document" }, { status: 404 });
  }
  return new Response(null, { status: 302, headers: { Location: downloadUrl, "Cache-Control": "private, no-store" } });
}

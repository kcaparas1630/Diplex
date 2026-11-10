/** GET /api/documents/[documentId]/pages?from=1&count=10: the page count, and sizes and signed URLs for that range. */
import { cookies } from "next/headers";

import { DEFAULT_PAGES_PER_REQUEST, getDocumentPages, getDocumentStore, readPlaygroundUser } from "../../../../../server";

export const runtime = "nodejs";

/** Answer the owner with the pages asked for; anyone else, and any unknown ID, gets the same 404. */
export async function GET(request: Request, context: { params: Promise<{ documentId: string }> }): Promise<Response> {
  const { documentId } = await context.params;
  const searchParams = new URL(request.url).searchParams;
  const pageRange = await getDocumentPages(
    getDocumentStore(),
    readPlaygroundUser(await cookies()),
    documentId,
    Number(searchParams.get("from") ?? 1),
    Number(searchParams.get("count") ?? DEFAULT_PAGES_PER_REQUEST),
  );
  if (!pageRange) {
    return Response.json({ code: "not_found", message: "no such document" }, { status: 404 });
  }
  return Response.json(pageRange, { headers: { "Cache-Control": "private, no-store" } }); // signed URLs are never cached or stored
}

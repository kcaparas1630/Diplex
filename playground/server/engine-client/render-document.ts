/** Sends one document to the engine's POST /render and reads the multipart/form-data answer with fetch alone (ADR 010). */

/** A page's size in points, as the engine's manifest gives it. */
export interface PageSize {
  index: number;
  width: number;
  height: number;
}

/** What the engine returns for one document: page sizes, one WebP per page in order, and the PDF a DOCX became. */
export interface RenderResult {
  pageSizes: PageSize[];
  pageImages: Uint8Array[];
  convertedPdf: Uint8Array | undefined;
}

/** How to reach the engine. */
export interface EngineConnection {
  engineUrl: string;
  engineApiKey: string | undefined;
}

/** The engine's refusal, with its error code to branch on and its plain message. */
export class EngineRenderError extends Error {
  /** Keep the HTTP status and the engine's code alongside the message. */
  constructor(
    readonly httpStatus: number,
    readonly errorCode: string,
    message: string,
  ) {
    super(message);
    this.name = "EngineRenderError";
  }
}

const API_VERSION = "1"; // the engine API version the playground codes against (ADR 012)

/** POST the document to /render and return its pages, or throw EngineRenderError with the engine's code. */
export async function renderDocument(
  engine: EngineConnection,
  documentBytes: Uint8Array,
  fileName: string,
  fetchFunction: typeof fetch = fetch,
): Promise<RenderResult> {
  const uploadForm = new FormData();
  uploadForm.append("document", new Blob([new Uint8Array(documentBytes)]), fileName);
  const requestHeaders: Record<string, string> = { "Diplex-Api-Version": API_VERSION };
  if (engine.engineApiKey) {
    requestHeaders.Authorization = `Bearer ${engine.engineApiKey}`;
  }
  const response = await fetchFunction(`${engine.engineUrl}/render`, { method: "POST", body: uploadForm, headers: requestHeaders });
  if (!response.ok) {
    throw await readEngineError(response);
  }
  return readRenderResult(await response.formData());
}

/** Turn the engine's JSON error into an EngineRenderError, or a generic one when the body isn't the contract's. */
async function readEngineError(response: Response): Promise<EngineRenderError> {
  try {
    const errorBody = (await response.json()) as { code?: string; message?: string };
    return new EngineRenderError(response.status, errorBody.code ?? "unknown", errorBody.message ?? response.statusText);
  } catch {
    return new EngineRenderError(response.status, "unknown", `the engine answered ${response.status}`);
  }
}

/** Read the manifest, the page images in order and the optional PDF from the response's parts. */
async function readRenderResult(responseParts: FormData): Promise<RenderResult> {
  const manifestPart = responseParts.get("manifest");
  const manifestText = typeof manifestPart === "string" ? manifestPart : await manifestPart?.text();
  if (!manifestText) {
    throw new EngineRenderError(502, "invalid_response", "the engine's answer has no manifest part");
  }
  const pageSizes = (JSON.parse(manifestText) as { pages: PageSize[] }).pages;
  const pageImages = await Promise.all(
    responseParts.getAll("page").map(async (pagePart) => new Uint8Array(await (pagePart as Blob).arrayBuffer())),
  );
  if (pageImages.length !== pageSizes.length) {
    throw new EngineRenderError(502, "invalid_response", `the manifest lists ${pageSizes.length} pages but ${pageImages.length} came`);
  }
  const pdfPart = responseParts.get("pdf");
  const convertedPdf = pdfPart instanceof Blob ? new Uint8Array(await pdfPart.arrayBuffer()) : undefined;
  return { pageSizes, pageImages, convertedPdf };
}

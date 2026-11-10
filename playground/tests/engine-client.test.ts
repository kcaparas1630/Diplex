/** Tests sending a document to /render and reading the engine's multipart/form-data answer, with a stand-in fetch. */
import { describe, expect, it } from "vitest";

import { EngineRenderError, renderDocument } from "../server/engine-client";

const ENGINE = { engineUrl: "http://engine:8000", engineApiKey: "local-playground-engine-key" };
const MANIFEST = { pages: [{ index: 1, width: 612, height: 792 }, { index: 2, width: 612, height: 792 }] };

/** A multipart/form-data body laid out as the engine's form_data module writes it: manifest, pages, then the PDF. */
function engineStyleResponse(withPdf: boolean): Response {
  const boundary = "engine-boundary";
  const parts = [
    `--${boundary}\r\nContent-Disposition: form-data; name="manifest"\r\nContent-Type: application/json\r\n\r\n${JSON.stringify(MANIFEST)}\r\n`,
    `--${boundary}\r\nContent-Disposition: form-data; name="page"; filename="page-0001.webp"\r\nContent-Type: image/webp\r\n\r\nWEBP-ONE\r\n`,
    `--${boundary}\r\nContent-Disposition: form-data; name="page"; filename="page-0002.webp"\r\nContent-Type: image/webp\r\n\r\nWEBP-TWO\r\n`,
  ];
  if (withPdf) {
    parts.push(`--${boundary}\r\nContent-Disposition: form-data; name="pdf"; filename="document.pdf"\r\nContent-Type: application/pdf\r\n\r\n%PDF-1.7 converted\r\n`);
  }
  return new Response(parts.join("") + `--${boundary}--\r\n`, { headers: { "Content-Type": `multipart/form-data; boundary=${boundary}` } });
}

/** A stand-in fetch that records the request and answers with the given response. */
function standInFetch(answer: Response) {
  const requests: { url: string; init: RequestInit }[] = [];
  /** Record the request and return the canned answer. */
  const fetchFunction = (async (url: string, init: RequestInit) => {
    requests.push({ url, init });
    return answer;
  }) as unknown as typeof fetch;
  return { fetchFunction, requests };
}

describe("renderDocument", () => {
  it("posts the file as the document part with the API version and the engine's key", async () => {
    const { fetchFunction, requests } = standInFetch(engineStyleResponse(false));

    await renderDocument(ENGINE, new TextEncoder().encode("%PDF-1.7 upload"), "report.pdf", fetchFunction);

    expect(requests[0].url).toBe("http://engine:8000/render");
    expect(requests[0].init.headers).toEqual({ "Diplex-Api-Version": "1", Authorization: "Bearer local-playground-engine-key" });
    const sentDocument = (requests[0].init.body as FormData).get("document") as File;
    expect(sentDocument.name).toBe("report.pdf");
    expect(await sentDocument.text()).toBe("%PDF-1.7 upload");
  });

  it("sends no Authorization header when the engine has no key", async () => {
    const { fetchFunction, requests } = standInFetch(engineStyleResponse(false));

    await renderDocument({ ...ENGINE, engineApiKey: undefined }, new Uint8Array([1]), "a.pdf", fetchFunction);

    expect(requests[0].init.headers).toEqual({ "Diplex-Api-Version": "1" });
  });

  it("reads the page sizes, the page images in order and the converted PDF", async () => {
    const { fetchFunction } = standInFetch(engineStyleResponse(true));

    const renderResult = await renderDocument(ENGINE, new Uint8Array([1]), "thesis.docx", fetchFunction);

    expect(renderResult.pageSizes).toEqual(MANIFEST.pages);
    expect(renderResult.pageImages.map((pageImage) => new TextDecoder().decode(pageImage))).toEqual(["WEBP-ONE", "WEBP-TWO"]);
    expect(new TextDecoder().decode(renderResult.convertedPdf)).toBe("%PDF-1.7 converted");
  });

  it("has no converted PDF for a PDF upload", async () => {
    const { fetchFunction } = standInFetch(engineStyleResponse(false));

    expect((await renderDocument(ENGINE, new Uint8Array([1]), "a.pdf", fetchFunction)).convertedPdf).toBeUndefined();
  });

  it("turns the engine's JSON error into an EngineRenderError with its status and code", async () => {
    const refusal = new Response(JSON.stringify({ code: "macros_not_allowed", message: "the DOCX carries macros" }), {
      status: 422,
      headers: { "Content-Type": "application/json" },
    });
    const { fetchFunction } = standInFetch(refusal);

    const renderError = await renderDocument(ENGINE, new Uint8Array([1]), "a.docx", fetchFunction).catch((thrown) => thrown);

    expect(renderError).toBeInstanceOf(EngineRenderError);
    expect([renderError.httpStatus, renderError.errorCode, renderError.message]).toEqual([422, "macros_not_allowed", "the DOCX carries macros"]);
  });

  it("refuses an answer whose page count doesn't match its manifest", async () => {
    const shortAnswer = new FormData();
    shortAnswer.append("manifest", JSON.stringify(MANIFEST));
    shortAnswer.append("page", new Blob(["only one"]), "page-0001.webp");
    const { fetchFunction } = standInFetch(new Response(shortAnswer));

    await expect(renderDocument(ENGINE, new Uint8Array([1]), "a.pdf", fetchFunction)).rejects.toThrow("lists 2 pages but 1 came");
  });
});

/** Tests download names and signed download URLs: the user's file name, the PDF or original key, owner only. */
import { S3Client } from "@aws-sdk/client-s3";
import { describe, expect, it } from "vitest";

import { attachmentDisposition, downloadFileName, getDownloadUrl, type DownloadSource } from "../server/documents";

const OWNER = "0b5c2f7e-8a1d-4c3e-9f20-6d1a2b3c4d5e";
const DOCUMENT_ID = "9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d";

/** A download source whose database holds one DOCX for OWNER. */
function standInDownloadSource(fileName: string): DownloadSource {
  return {
    database: {
      query: async (_queryText: string, queryValues?: unknown[]) => ({
        rows: queryValues?.[1] === OWNER ? [{ id: DOCUMENT_ID, owner_id: OWNER, file_name: fileName, folder: `playground/${OWNER}/${DOCUMENT_ID}`, source_type: "docx", page_sizes: [], created_at: new Date(), deleted_at: null }] : [],
      }),
    },
    signingClient: new S3Client({ endpoint: "http://localhost:9000", region: "us-east-1", forcePathStyle: true, credentials: { accessKeyId: "a", secretAccessKey: "b" } }),
    bucketName: "playground-documents",
  };
}

describe("download names", () => {
  it("names the PDF after the user's file, and keeps the original's name", () => {
    expect(downloadFileName("Thesis final.docx", "pdf")).toBe("Thesis final.pdf");
    expect(downloadFileName("scan.PDF", "pdf")).toBe("scan.pdf");
    expect(downloadFileName("Thesis final.docx", "original")).toBe("Thesis final.docx");
  });

  it("gives an ASCII fallback and the exact UTF-8 name (RFC 6266, RFC 5987)", () => {
    expect(attachmentDisposition('Résumé "final".pdf')).toBe(
      `attachment; filename="R_sum_ _final_.pdf"; filename*=UTF-8''R%C3%A9sum%C3%A9%20%22final%22.pdf`,
    );
  });
});

describe("getDownloadUrl", () => {
  it("signs the PDF's key with the download name in response-content-disposition", async () => {
    const downloadUrl = new URL(String(await getDownloadUrl(standInDownloadSource("Thesis.docx"), OWNER, DOCUMENT_ID, "pdf")));

    expect(downloadUrl.pathname).toBe(`/playground-documents/playground/${OWNER}/${DOCUMENT_ID}/document.pdf`);
    expect(downloadUrl.searchParams.get("response-content-disposition")).toBe(`attachment; filename="Thesis.pdf"; filename*=UTF-8''Thesis.pdf`);
    expect(downloadUrl.searchParams.get("X-Amz-Expires")).toBe("1800");
  });

  it("signs the original's key under its own extension", async () => {
    const downloadUrl = new URL(String(await getDownloadUrl(standInDownloadSource("Thesis.docx"), OWNER, DOCUMENT_ID, "original")));

    expect(downloadUrl.pathname.endsWith("/original.docx")).toBe(true);
  });

  it("gives anyone but the owner nothing", async () => {
    expect(await getDownloadUrl(standInDownloadSource("Thesis.docx"), "11111111-2222-4333-8444-555555555555", DOCUMENT_ID, "pdf")).toBeNull();
    expect(await getDownloadUrl(standInDownloadSource("Thesis.docx"), undefined, DOCUMENT_ID, "pdf")).toBeNull();
  });
});

/** Tests writing a document's files in ADR 001 §5's layout, with a stand-in S3 client. */
import type { S3Client } from "@aws-sdk/client-s3";
import { describe, expect, it } from "vitest";

import { documentFolder, documentKeys, uploadDocumentFiles } from "../server/storage";

/** A stand-in S3 client that records each command's name and input. */
function recordingS3Client() {
  const sentCommands: { name: string; input: Record<string, unknown> }[] = [];
  const client = {
    send: async (command: { constructor: { name: string }; input: Record<string, unknown> }) => {
      sentCommands.push({ name: command.constructor.name, input: command.input });
      return {};
    },
  } as unknown as S3Client;
  return { client, sentCommands };
}

const pageImages = Array.from({ length: 10 }, (_, pageOffset) => new Uint8Array([pageOffset]));

describe("document layout", () => {
  it("names the folder by owner and document ID under the prefix, never by file name", () => {
    expect(documentFolder("playground", "user-1", "doc-9")).toBe("playground/user-1/doc-9");
    expect(documentKeys.original("p/u/d", "docx")).toBe("p/u/d/original.docx");
    expect(documentKeys.pdf("p/u/d")).toBe("p/u/d/document.pdf");
    expect(documentKeys.page("p/u/d", 12)).toBe("p/u/d/pages/page-0012.webp");
  });
});

describe("uploadDocumentFiles", () => {
  it("uploads a DOCX's original, its converted PDF and every page, pages with a year-long immutable cache", async () => {
    const { client, sentCommands } = recordingS3Client();

    await uploadDocumentFiles(client, "bucket", "p/u/d", {
      originalBytes: new Uint8Array([1]),
      sourceType: "docx",
      convertedPdf: new Uint8Array([2]),
      pageImages,
    });

    expect(sentCommands.map((command) => [command.name, command.input.Key])).toEqual([
      ["PutObjectCommand", "p/u/d/original.docx"],
      ["PutObjectCommand", "p/u/d/document.pdf"],
      ...pageImages.map((_, pageOffset) => ["PutObjectCommand", documentKeys.page("p/u/d", pageOffset + 1)]),
    ]);
    const pageUpload = sentCommands[2].input;
    expect([pageUpload.ContentType, pageUpload.CacheControl]).toEqual(["image/webp", "public, max-age=31536000, immutable"]);
    expect(sentCommands[0].input.ContentType).toBe("application/vnd.openxmlformats-officedocument.wordprocessingml.document");
  });

  it("copies an uploaded PDF to document.pdf inside the bucket instead of uploading it twice", async () => {
    const { client, sentCommands } = recordingS3Client();

    await uploadDocumentFiles(client, "bucket", "p/u/d", { originalBytes: new Uint8Array([1]), sourceType: "pdf", convertedPdf: undefined, pageImages: [] });

    expect(sentCommands.map((command) => command.name)).toEqual(["PutObjectCommand", "CopyObjectCommand"]);
    expect(sentCommands[1].input).toMatchObject({ Key: "p/u/d/document.pdf", CopySource: "bucket/p/u/d/original.pdf" });
  });
});

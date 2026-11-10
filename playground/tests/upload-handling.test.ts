/** Tests reading the browser's upload form and describing a failed upload for the browser. */
import { describe, expect, it } from "vitest";

import { InvalidUploadError, describeUploadFailure, readUploadedFile } from "../server/documents";
import { EngineRenderError } from "../server/engine-client";

describe("readUploadedFile", () => {
  it("reads the document part's name and bytes", async () => {
    const uploadForm = new FormData();
    uploadForm.append("document", new File(["%PDF-1.7"], "Quarterly report.pdf"));

    const uploadedFile = await readUploadedFile(uploadForm);

    expect(uploadedFile.fileName).toBe("Quarterly report.pdf");
    expect(new TextDecoder().decode(uploadedFile.documentBytes)).toBe("%PDF-1.7");
  });

  it.each([
    ["no document part", new FormData()],
    ["an empty file", (() => { const emptyForm = new FormData(); emptyForm.append("document", new File([], "empty.pdf")); return emptyForm; })()],
    ["a text field", (() => { const textForm = new FormData(); textForm.append("document", "not a file"); return textForm; })()],
  ])("refuses %s", async (_, uploadForm) => {
    await expect(readUploadedFile(uploadForm)).rejects.toBeInstanceOf(InvalidUploadError);
  });
});

describe("describeUploadFailure", () => {
  it("passes on the engine's status and code, so the browser sees why", () => {
    expect(describeUploadFailure(new EngineRenderError(422, "macros_not_allowed", "the DOCX carries macros"))).toEqual({
      httpStatus: 422,
      body: { code: "macros_not_allowed", message: "the DOCX carries macros" },
    });
  });

  it("answers a bad form with 400 invalid_upload", () => {
    expect(describeUploadFailure(new InvalidUploadError("choose a DOCX or PDF to upload")).httpStatus).toBe(400);
  });

  it("answers anything else with a plain 500 that says nothing about the error", () => {
    expect(describeUploadFailure(new Error("connection string with a password"))).toEqual({
      httpStatus: 500,
      body: { code: "playground_error", message: "the playground could not store the document" },
    });
  });
});

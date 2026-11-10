/** The viewer: lays out every page from its size at once, then loads page images in batches of 10 as the user scrolls. */
"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { PAGES_PER_BATCH, batchesToRequest, type SignedPageUrl } from "./page-batches";

/** A page's number and size in points, from the document's row. */
export interface ViewerPageSize {
  index: number;
  width: number;
  height: number;
}

/** The pages route's answer for one batch. */
interface PageBatchAnswer {
  pages: { index: number; url: string }[];
  expiresAt: string;
}

const PREFETCH_MARGIN = "1200px 0px"; // start loading a little before a page scrolls into view

/** Show every page as a box of its own shape, and fill in each image once its batch's signed URLs arrive. */
export function DocumentViewer({ documentId, pageSizes }: { documentId: string; pageSizes: ViewerPageSize[] }) {
  const [signedUrls, setSignedUrls] = useState<Map<number, SignedPageUrl>>(new Map());
  const signedUrlsRef = useRef(signedUrls);
  const batchesInFlight = useRef(new Set<number>());
  const visiblePages = useRef(new Set<number>());
  signedUrlsRef.current = signedUrls;

  /** Ask for every batch the visible pages still need, and store the URLs that come back. */
  const requestMissingBatches = useCallback(async () => {
    const neededBatches = batchesToRequest([...visiblePages.current], signedUrlsRef.current, batchesInFlight.current, Date.now());
    await Promise.all(
      neededBatches.map(async (batchStart) => {
        batchesInFlight.current.add(batchStart);
        try {
          const answer = await fetch(`/api/documents/${documentId}/pages?from=${batchStart}&count=${PAGES_PER_BATCH}`);
          if (!answer.ok) {
            return;
          }
          const pageBatch = (await answer.json()) as PageBatchAnswer;
          const expiresAtMilliseconds = Date.parse(pageBatch.expiresAt);
          setSignedUrls((current) => {
            const updated = new Map(current);
            for (const page of pageBatch.pages) {
              updated.set(page.index, { url: page.url, expiresAtMilliseconds });
            }
            return updated;
          });
        } finally {
          batchesInFlight.current.delete(batchStart);
        }
      }),
    );
  }, [documentId]);

  useEffect(() => {
    /** Track which pages are near the viewport, and fetch what they need. */
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const pageIndex = Number((entry.target as HTMLElement).dataset.pageIndex);
          if (entry.isIntersecting) {
            visiblePages.current.add(pageIndex);
          } else {
            visiblePages.current.delete(pageIndex);
          }
        }
        void requestMissingBatches();
      },
      { rootMargin: PREFETCH_MARGIN },
    );
    document.querySelectorAll<HTMLElement>("[data-page-index]").forEach((pageBox) => observer.observe(pageBox));
    const renewal = window.setInterval(() => void requestMissingBatches(), 30_000); // renew URLs that are about to expire
    return () => {
      observer.disconnect();
      window.clearInterval(renewal);
    };
  }, [requestMissingBatches]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, alignItems: "center" }}>
      {pageSizes.map((pageSize) => {
        const signedUrl = signedUrls.get(pageSize.index);
        return (
          <div
            key={pageSize.index}
            data-page-index={pageSize.index}
            style={{ width: "100%", maxWidth: Math.round(pageSize.width * 1.5), aspectRatio: `${pageSize.width} / ${pageSize.height}`, background: "#fff", boxShadow: "0 1px 4px rgba(0,0,0,.15)" }}
          >
            {signedUrl ? (
              // A signed URL, not a static file, so next/image's optimiser doesn't apply.
              // eslint-disable-next-line @next/next/no-img-element
              <img src={signedUrl.url} alt={`Page ${pageSize.index}`} width={pageSize.width} height={pageSize.height} decoding="async" style={{ width: "100%", height: "100%", display: "block" }} />
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

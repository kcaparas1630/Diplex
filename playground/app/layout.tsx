/** The playground's root layout: the HTML shell and the styles every page shares. */
import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Diplex playground",
  description: "Upload a DOCX or PDF, render it with the Diplex engine, and read it page by page.",
};

/** Wrap every page in the document shell. */
export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "system-ui, sans-serif", background: "#f4f4f5", color: "#18181b" }}>
        <main style={{ maxWidth: 960, margin: "0 auto", padding: "24px 16px" }}>{children}</main>
      </body>
    </html>
  );
}

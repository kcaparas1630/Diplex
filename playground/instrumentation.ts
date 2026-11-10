/** Runs once when the playground's server starts (Next.js instrumentation): creates its bucket and documents table. */

/** Prepare storage before the first request, on the Node.js server only. */
export async function register(): Promise<void> {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const { prepareStorage } = await import("./server");
    await prepareStorage();
  }
}

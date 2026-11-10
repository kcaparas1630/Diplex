/** Tests the per-browser user: read from the httpOnly cookie, or a new random one set on first upload. */
import { describe, expect, it } from "vitest";

import { ensurePlaygroundUser, readPlaygroundUser } from "../server/session";

/** A cookie jar holding the given value, recording what is set. */
function cookieJarWith(cookieValue: string | undefined) {
  const setCookies: { name: string; value: string; options: Record<string, unknown> }[] = [];
  return {
    setCookies,
    get: () => (cookieValue === undefined ? undefined : { value: cookieValue }),
    /** Record a cookie the code sets. */
    set: (name: string, value: string, options: Record<string, unknown>) => setCookies.push({ name, value, options }),
  };
}

const KNOWN_USER = "0b5c2f7e-8a1d-4c3e-9f20-6d1a2b3c4d5e";

describe("the playground user", () => {
  it("reads a user ID the playground gave earlier", () => {
    expect(readPlaygroundUser(cookieJarWith(KNOWN_USER))).toBe(KNOWN_USER);
  });

  it("ignores a cookie that isn't one of its IDs", () => {
    expect(readPlaygroundUser(cookieJarWith("../other-user"))).toBeUndefined();
  });

  it("keeps an existing user without setting the cookie again", () => {
    const cookieJar = cookieJarWith(KNOWN_USER);

    expect(ensurePlaygroundUser(cookieJar)).toBe(KNOWN_USER);
    expect(cookieJar.setCookies).toEqual([]);
  });

  it("gives a new browser a random ID in an httpOnly, same-site cookie for a year", () => {
    const cookieJar = cookieJarWith(undefined);

    const newUser = ensurePlaygroundUser(cookieJar);

    expect(newUser).toMatch(/^[0-9a-f-]{36}$/);
    expect(cookieJar.setCookies).toEqual([
      { name: "playground_user", value: newUser, options: { httpOnly: true, sameSite: "lax", path: "/", maxAge: 31536000 } },
    ]);
  });
});

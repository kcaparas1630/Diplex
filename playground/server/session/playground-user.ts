/** Who the current browser is: the playground has no sign-in, so each browser gets a random user ID in an httpOnly cookie. */

const USER_COOKIE_NAME = "playground_user";
const USER_COOKIE_MAX_AGE_SECONDS = 365 * 24 * 60 * 60;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

/** The cookie calls the playground makes, as Next.js's cookies() store provides them. */
export interface CookieJar {
  get(cookieName: string): { value: string } | undefined;
  set?(cookieName: string, cookieValue: string, cookieOptions: Record<string, unknown>): unknown;
}

/** The browser's user ID, or undefined when it has none yet (or a cookie that isn't one of ours). */
export function readPlaygroundUser(cookieJar: CookieJar): string | undefined {
  const cookieValue = cookieJar.get(USER_COOKIE_NAME)?.value;
  return cookieValue && UUID_PATTERN.test(cookieValue) ? cookieValue : undefined;
}

/** The browser's user ID, giving it a new one in an httpOnly, same-site cookie when it has none. */
export function ensurePlaygroundUser(cookieJar: CookieJar): string {
  const knownUser = readPlaygroundUser(cookieJar);
  if (knownUser) {
    return knownUser;
  }
  const newUser = crypto.randomUUID();
  cookieJar.set?.(USER_COOKIE_NAME, newUser, { httpOnly: true, sameSite: "lax", path: "/", maxAge: USER_COOKIE_MAX_AGE_SECONDS });
  return newUser;
}

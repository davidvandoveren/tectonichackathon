/**
 * An insight's `cta_target` must only be followed when it is an internal, root-relative path
 * (starts with "/" but not "//", which browsers treat as a protocol-relative external URL).
 */
export function isSafeInternalPath(target: string): boolean {
  return target.startsWith("/") && !target.startsWith("//");
}

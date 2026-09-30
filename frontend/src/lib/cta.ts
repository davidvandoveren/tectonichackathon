/**
 * An insight's `cta_target` must only be followed when it is an internal, root-relative path
 * (starts with "/" but not "//", which browsers treat as a protocol-relative external URL).
 * Backslashes and control characters are refused too: browsers read "/\evil.example" as
 * "//evil.example", and they strip tabs/newlines, so "/\t/evil.example" would work the same way.
 */
export function isSafeInternalPath(target: string): boolean {
  return (
    target.startsWith("/") &&
    !target.startsWith("//") &&
    !target.includes("\\") &&
    // eslint-disable-next-line no-control-regex
    !/[\u0000-\u001f\u007f]/.test(target)
  );
}

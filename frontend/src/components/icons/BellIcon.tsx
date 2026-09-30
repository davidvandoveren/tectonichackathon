import type { SVGProps } from "react";

export function BellIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="22"
      height="22"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M6 10.5a6 6 0 0 1 12 0v3.3l1.4 2.4a1 1 0 0 1-.9 1.5H5.5a1 1 0 0 1-.9-1.5L6 13.8Z" />
      <path d="M9.7 20a2.3 2.3 0 0 0 4.6 0" />
    </svg>
  );
}

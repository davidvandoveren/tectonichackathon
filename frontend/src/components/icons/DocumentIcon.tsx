import type { SVGProps } from "react";

export function DocumentIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M6.5 3.5h7L18 8v12a1 1 0 0 1-1 1h-10a1 1 0 0 1-1-1v-15a1 1 0 0 1 1-1Z" />
      <path d="M13 3.5V8h4.5" />
      <path d="M9 13h6" />
      <path d="M9 16.5h6" />
    </svg>
  );
}

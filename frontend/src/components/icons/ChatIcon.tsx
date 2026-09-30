import type { SVGProps } from "react";

export function ChatIcon(props: SVGProps<SVGSVGElement>) {
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
      <path d="M4 5.5h16v10H9.5L5.5 19v-3.5H4Z" />
    </svg>
  );
}

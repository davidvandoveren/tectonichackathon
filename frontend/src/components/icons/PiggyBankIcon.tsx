import type { SVGProps } from "react";

export function PiggyBankIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="24"
      height="24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M4.5 12.5a5.5 5.5 0 0 1 5.5-5.5h4a5 5 0 0 1 4.6 3h1.4a1 1 0 0 1 1 1.3l-.5 1.5a1 1 0 0 1-1 .7H19v1a3 3 0 0 1-2 2.8V19h-2.5v-1.5h-4V19H8v-2.2a5.5 5.5 0 0 1-3.5-5.1Z" />
      <path d="M9.5 11h.01" />
      <path d="M8 7.2 7 5" />
      <path d="M13.5 7 14.5 5" />
    </svg>
  );
}

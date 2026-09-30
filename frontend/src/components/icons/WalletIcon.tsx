import type { SVGProps } from "react";

export function WalletIcon(props: SVGProps<SVGSVGElement>) {
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
      <rect x="3" y="6.5" width="18" height="13" rx="2" />
      <path d="M3 10.5h18" />
      <path d="M16 14.5h2.5" />
      <path d="M7 6.5V5a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v1.5" />
    </svg>
  );
}

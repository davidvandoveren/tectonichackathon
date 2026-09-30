import type { SVGProps } from "react";

export function TransferIcon(props: SVGProps<SVGSVGElement>) {
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
      <path d="M7 7h12l-3.5-3.5" />
      <path d="M17 17H5l3.5 3.5" />
    </svg>
  );
}

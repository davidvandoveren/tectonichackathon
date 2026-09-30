import type { SVGProps } from "react";

export function CarIcon(props: SVGProps<SVGSVGElement>) {
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
      <path d="M4.5 16V11.5l2-4.5a2 2 0 0 1 1.8-1.2h7.4a2 2 0 0 1 1.8 1.2l2 4.5V16" />
      <path d="M4.5 16a2 2 0 1 0 4 0" />
      <path d="M15.5 16a2 2 0 1 0 4 0" />
      <path d="M4.5 16h15" />
      <path d="M4.8 11.5h14.4" />
    </svg>
  );
}

import type { SVGProps } from "react";

export function PeopleIcon(props: SVGProps<SVGSVGElement>) {
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
      <circle cx="9" cy="8.5" r="2.75" />
      <path d="M3.5 19a5.5 5.5 0 0 1 11 0" />
      <path d="M15.5 7.5a2.5 2.5 0 1 1 0 5" />
      <path d="M16 13.2a4.7 4.7 0 0 1 4.5 4.8" />
    </svg>
  );
}

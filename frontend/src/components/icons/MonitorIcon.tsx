import type { SVGProps } from "react";

export function MonitorIcon(props: SVGProps<SVGSVGElement>) {
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
      <rect x="3" y="4.5" width="18" height="12" rx="2" />
      <path d="M8.5 20.5h7" />
      <path d="M12 16.5v4" />
    </svg>
  );
}

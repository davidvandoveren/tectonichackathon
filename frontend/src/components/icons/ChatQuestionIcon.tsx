import type { SVGProps } from "react";

export function ChatQuestionIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="20"
      height="20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M4 5.5h16v10H9.5L5.5 19v-3.5H4Z" />
      <path d="M10 9.8c0-1.1.9-1.8 2-1.8s2 .6 2 1.6c0 .9-.6 1.2-1.4 1.7-.5.3-.6.5-.6 1" />
      <path d="M12 13.9h.01" />
    </svg>
  );
}

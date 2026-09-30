import type { SVGProps } from "react";
import type { TransactionCategory } from "../../api/types";

interface CategoryIconProps extends SVGProps<SVGSVGElement> {
  category: TransactionCategory;
}

const PATHS: Record<TransactionCategory, string> = {
  income: "M12 19V5M5 12l7-7 7 7",
  groceries: "M6 8h12l-1.3 10.5a2 2 0 0 1-2 1.8H9.3a2 2 0 0 1-2-1.8L6 8Zm2-3a4 4 0 0 1 8 0",
  housing: "M4 11.5 12 4l8 7.5M6 10v9a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-9",
  transport: "M4.5 16V10a2 2 0 0 1 2-2h11a2 2 0 0 1 2 2v6M4.5 16a2 2 0 1 0 4 0M15.5 16a2 2 0 1 0 4 0M4.5 16h15",
  leisure: "m12 3 2.5 5.5 6 0.8-4.3 4.2 1 6-5.2-3-5.2 3 1-6-4.3-4.2 6-0.8Z",
  shopping: "M6.5 7h11l1 13a2 2 0 0 1-2 2h-9a2 2 0 0 1-2-2l1-13Zm2.5-1a3 3 0 0 1 6 0",
  utilities: "M13 2 4.5 14h5.5l-1 8 9-12H12.5l0.5-8Z",
  savings: "M4.5 13a5 5 0 0 1 5-5H14a4.5 4.5 0 0 1 4.5 4.5V13c0 1-1 2-2 2h-1l-1 3h-5l-1-3h-2a2 2 0 0 1-2-2Z",
  transfer: "M6 7h12l-3-3m3 3-3 3M18 17H6l3-3m-3 3 3 3",
  other: "M12 12h.01M12 6.5h.01M12 17.5h.01",
};

const COLORS: Record<TransactionCategory, string> = {
  income: "var(--kbc-green)",
  groceries: "#e08a1e",
  housing: "#6a4fc4",
  transport: "#1f8fd6",
  leisure: "#d6336c",
  shopping: "#c77700",
  utilities: "#b8960f",
  savings: "#12886b",
  transfer: "#0074a8",
  other: "#5b6b7a",
};

export function CategoryIcon({ category, ...rest }: CategoryIconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="20"
      height="20"
      fill="none"
      stroke={COLORS[category]}
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...rest}
    >
      <path d={PATHS[category]} />
    </svg>
  );
}

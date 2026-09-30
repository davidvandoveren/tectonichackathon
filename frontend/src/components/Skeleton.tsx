import styles from "./Skeleton.module.css";

interface SkeletonProps {
  height?: number | string;
  width?: number | string;
  radius?: number | string;
}

export function Skeleton({ height = 16, width = "100%", radius = 8 }: SkeletonProps) {
  return (
    <div
      className={styles.skeleton}
      style={{ height, width, borderRadius: radius }}
      aria-hidden="true"
    />
  );
}

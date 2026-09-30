import { Outlet } from "react-router";
import { TabBar } from "./TabBar";
import styles from "./AppLayout.module.css";

export function AppLayout() {
  return (
    <div className={styles.shell}>
      <main className={styles.content}>
        <Outlet />
      </main>
      <TabBar />
    </div>
  );
}

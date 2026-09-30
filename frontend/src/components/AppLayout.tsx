import { Outlet } from "react-router";
import { TabBar } from "./TabBar";
import { KateChat } from "../kate/KateChat";
import styles from "./AppLayout.module.css";

export function AppLayout() {
  return (
    <div className={styles.shell}>
      <main className={styles.content}>
        <Outlet />
      </main>
      <TabBar />
      <KateChat />
    </div>
  );
}

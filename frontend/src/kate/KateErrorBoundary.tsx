import { Component, type ErrorInfo, type ReactNode } from "react";
import styles from "./KateChat.module.css";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
  resetKey: number;
}

/**
 * Keeps a problem inside Kate from taking the whole app down: without this, one render error in
 * the chat unmounts every screen. Shows a small notice with a restart button and logs the error.
 */
export class KateErrorBoundary extends Component<Props, State> {
  state: State = { error: null, resetKey: 0 };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("Kate crashte (de rest van de app blijft werken):", error, info.componentStack);
  }

  private restart = () => {
    this.setState((state) => ({ error: null, resetKey: state.resetKey + 1 }));
  };

  render() {
    if (this.state.error) {
      return (
        <div className={styles.crashNotice} role="alert">
          <p>Er ging iets mis met Kate. De rest van de app werkt gewoon verder.</p>
          <button type="button" className={styles.crashButton} onClick={this.restart}>
            Kate herstarten
          </button>
        </div>
      );
    }
    // A new key after a restart gives Kate a completely fresh state.
    return <div key={this.state.resetKey}>{this.props.children}</div>;
  }
}

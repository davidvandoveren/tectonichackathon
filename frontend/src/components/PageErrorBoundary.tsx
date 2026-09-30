import { Component, type ErrorInfo, type ReactNode } from "react";
import { ErrorState } from "./ErrorState";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
  attempt: number;
}

/**
 * Catches a render error in one screen so the rest of the app (top bar, tab bar, Kate) keeps
 * working, instead of React unmounting everything into a blank page. Give it a `key` per route so
 * navigating away also clears the error.
 */
export class PageErrorBoundary extends Component<Props, State> {
  state: State = { error: null, attempt: 0 };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("Scherm crashte (de rest van de app blijft werken):", error, info.componentStack);
  }

  private retry = () => {
    this.setState((state) => ({ error: null, attempt: state.attempt + 1 }));
  };

  render() {
    if (this.state.error) {
      return (
        <ErrorState message="Dit scherm liep vast. De rest van de app werkt gewoon verder." onRetry={this.retry} />
      );
    }
    return <div key={this.state.attempt}>{this.props.children}</div>;
  }
}

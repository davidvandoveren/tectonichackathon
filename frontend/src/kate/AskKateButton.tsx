import { ChatQuestionIcon } from "../components/icons/ChatQuestionIcon";
import styles from "./AskKateButton.module.css";

interface AskKateButtonProps {
  /**
   * Opens the Kate assistant. Left undefined until the Kate chat surface
   * exists, in which case the button renders as an inert "Binnenkort"
   * placeholder; once a handler is wired in, it becomes a real button.
   */
  onClick?: () => void;
  className?: string;
}

/** The "Vraag het Kate" entry point, used in the desktop header. */
export function AskKateButton({ onClick, className }: AskKateButtonProps) {
  const isEnabled = typeof onClick === "function";
  const classNames = [styles.button, className ?? ""].filter(Boolean).join(" ");

  return (
    <button
      type="button"
      className={classNames}
      onClick={onClick}
      aria-disabled={!isEnabled}
      title={isEnabled ? undefined : "Binnenkort"}
    >
      <ChatQuestionIcon aria-hidden="true" />
      <span>Vraag het Kate</span>
    </button>
  );
}

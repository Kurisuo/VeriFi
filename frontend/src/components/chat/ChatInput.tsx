import { useState, type FormEvent } from "react";

interface ChatInputProps {
  onSubmit: (message: string) => void;
  disabled?: boolean;
  value?: string;
  onValueChange?: (value: string) => void;
}

export function ChatInput({
  onSubmit,
  disabled,
  value: controlledValue,
  onValueChange,
}: ChatInputProps) {
  const [internalValue, setInternalValue] = useState("");
  const value = controlledValue ?? internalValue;

  function setValue(next: string) {
    if (onValueChange) {
      onValueChange(next);
    } else {
      setInternalValue(next);
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue("");
  }

  return (
    <form className="chat-input-bar" onSubmit={handleSubmit}>
      <input
        type="text"
        className="chat-input-bar__field"
        placeholder="Ask about IRA withdrawals, RMDs, fees, transfers, or beneficiaries…"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={disabled}
        aria-label="Your question"
      />
      <button
        type="submit"
        className="chat-input-bar__submit"
        disabled={disabled || !value.trim()}
      >
        Send
      </button>
    </form>
  );
}

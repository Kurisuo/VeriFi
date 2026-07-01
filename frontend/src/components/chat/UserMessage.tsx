interface UserMessageProps {
  content: string;
}

export function UserMessage({ content }: UserMessageProps) {
  return (
    <div className="message message--user">
      <span className="message__avatar message__avatar--you">You</span>
      <div className="message__bubble message__bubble--user">{content}</div>
    </div>
  );
}

import { useEffect, useRef } from "react";
import type { ChatMessage } from "../../hooks/useChat";
import { AssistantMessage } from "./AssistantMessage";
import { UserMessage } from "./UserMessage";

interface MessageListProps {
  messages: ChatMessage[];
}

export function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="message-list">
      {messages.map((message, index) =>
        message.role === "user" ? (
          <UserMessage key={index} content={message.content} />
        ) : (
          <AssistantMessage
            key={index}
            content={message.content}
            sources={message.sources}
          />
        ),
      )}
      <div ref={bottomRef} />
    </div>
  );
}

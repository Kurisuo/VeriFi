import { useMutation } from "@tanstack/react-query";
import { postChat } from "../api/chat";
import type { SourceCitation } from "../api/types";

export type ChatMessage =
  | { role: "user"; content: string }
  | { role: "assistant"; content: string; sources: SourceCitation[] };

export function useChat() {
  const mutation = useMutation({
    mutationFn: postChat,
  });

  function sendMessage(
    message: string,
    onSuccess: (messages: ChatMessage[]) => void,
    currentMessages: ChatMessage[],
  ) {
    const trimmed = message.trim();
    if (!trimmed || mutation.isPending) return;

    const userMessage: ChatMessage = { role: "user", content: trimmed };
    const withUser = [...currentMessages, userMessage];

    mutation.mutate(
      { message: trimmed },
      {
        onSuccess: (response) => {
          const assistantMessage: ChatMessage = {
            role: "assistant",
            content: response.answer,
            sources: response.sources,
          };
          onSuccess([...withUser, assistantMessage]);
        },
      },
    );
  }

  return {
    sendMessage,
    isLoading: mutation.isPending,
    error: mutation.error,
    resetError: mutation.reset,
  };
}

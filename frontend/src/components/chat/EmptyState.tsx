const EXAMPLE_QUESTIONS = [
  "What happens if a margin call is issued?",
  "How long do withdrawals take to process?",
  "What are the account terms and conditions?",
];

interface EmptyStateProps {
  onSelectQuestion: (question: string) => void;
  disabled?: boolean;
}

export function EmptyState({ onSelectQuestion, disabled }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <p className="empty-state__heading">Ask a policy question</p>
      <p className="empty-state__description">
        VeriFi retrieves relevant passages from verified documents and grounds
        its answer in those sources.
      </p>
      <div className="example-questions">
        {EXAMPLE_QUESTIONS.map((question) => (
          <button
            key={question}
            type="button"
            className="example-question"
            disabled={disabled}
            onClick={() => onSelectQuestion(question)}
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}

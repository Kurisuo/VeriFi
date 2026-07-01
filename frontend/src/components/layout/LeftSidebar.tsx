const DEMO_QUESTIONS = [
  "Can I take money out of my traditional IRA before age 59½?",
  "What account fees might apply to a brokerage account?",
  "When do required minimum distributions begin?",
  "How long do fund transfers usually take?",
  "How can I change the beneficiary on my retirement account?",
];

const PIPELINE_STEPS = [
  "Embedding query...",
  "Searching custom C++ vector database...",
  "Retrieving top policy chunks...",
  "Generating grounded response...",
];

interface LeftSidebarProps {
  onSelectQuestion: (question: string) => void;
  activeQuestion: string | null;
  isLoading: boolean;
}

export function LeftSidebar({
  onSelectQuestion,
  activeQuestion,
  isLoading,
}: LeftSidebarProps) {
  return (
    <aside className="left-sidebar">
      <div className="left-sidebar__top">
        <div className="sidebar-logo">
          <div className="sidebar-logo__icon">F</div>
          <div>
            <p className="sidebar-logo__eyebrow">Internal Prototype</p>
            <p className="sidebar-logo__name">Policy Assist</p>
          </div>
        </div>

        <div className="sidebar-tabs">
          <button type="button" className="sidebar-tab sidebar-tab--active">
            Chat Demo
          </button>
          <button type="button" className="sidebar-tab">
            RAG Pipeline
          </button>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-section__header">
            <span className="sidebar-section__title">Demo Questions</span>
            <span className="sidebar-badge">Hardcoded</span>
          </div>
          <ul className="demo-questions">
            {DEMO_QUESTIONS.map((question) => (
              <li key={question}>
                <button
                  type="button"
                  className={`demo-question${activeQuestion === question ? " demo-question--active" : ""}`}
                  onClick={() => onSelectQuestion(question)}
                  disabled={isLoading}
                >
                  {question}
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-section__header">
            <span className="sidebar-section__title">RAG Pipeline</span>
            <span className="sidebar-badge sidebar-badge--green">
              {isLoading ? "Running" : "Ready"}
            </span>
          </div>
          <ul className="pipeline-steps">
            {PIPELINE_STEPS.map((step, i) => (
              <li key={step} className="pipeline-step">
                <span
                  className={`pipeline-step__dot${isLoading ? " pipeline-step__dot--pulse" : ""}`}
                  style={{ animationDelay: `${i * 0.2}s` }}
                />
                <span className="pipeline-step__label">{step}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="sidebar-footer">
        <p className="sidebar-footer__eyebrow">Runtime · Static</p>
        <p className="sidebar-footer__title">React + static JSON</p>
        <p className="sidebar-footer__body">
          Embeddings and C++ vector search are mocked for presentation purposes.
        </p>
      </div>
    </aside>
  );
}

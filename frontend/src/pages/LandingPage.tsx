import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

const HOW_IT_WORKS = [
  {
    step: "01",
    title: "Ask",
    body: "Type any policy question in natural language. VeriFi embeds your query using the same model that indexed the documents.",
  },
  {
    step: "02",
    title: "Retrieve",
    body: "Our custom C++ vector database runs cosine similarity across every document chunk and returns the top-K most semantically relevant passages.",
  },
  {
    step: "03",
    title: "Verify",
    body: "The LLM generates a grounded answer using only the retrieved passages — then surfaces every source with its document, page, and relevance score.",
  },
];

const TECH_PILLS = [
  "C++ Vector Database",
  "Cosine Similarity",
  "RAG Pipeline",
  "React",
  "Embedding API",
  "LLM Grounding",
  "Source Citations",
];

const TEAM = [
  { name: "Christopher Zarraga Jimenez", initials: "CZ" },
  { name: "Sai Gonuguntla", initials: "SG" },
  { name: "Divya Machiraju", initials: "DM" },
  { name: "Srushti Chaudhari", initials: "SC" },
  { name: "Ethan Williams", initials: "EW" },
];

export default function LandingPage() {
  const [question, setQuestion] = useState("");
  const navigate = useNavigate();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q) return;
    navigate(`/chat?q=${encodeURIComponent(q)}`);
  }

  return (
    <div className="lp">
      {/* ── Navbar ─────────────────────────────────────── */}
      <nav className="lp-nav">
        <Link to="/" className="lp-nav__logo">
          <span className="lp-nav__logo-icon">F</span>
          <span className="lp-nav__logo-name">VeriFi</span>
        </Link>

        <ul className="lp-nav__links">
          <li><a href="#how-it-works">How It Works</a></li>
          <li><a href="#technology">Technology</a></li>
          <li><a href="#team">Team</a></li>
        </ul>

        <div className="lp-nav__actions">
          <Link to="/chat" className="lp-btn lp-btn--ghost">Sign In</Link>
          <Link to="/chat" className="lp-btn lp-btn--primary">Try Demo</Link>
        </div>
      </nav>

      {/* ── Hero ───────────────────────────────────────── */}
      <section className="lp-hero">
        <div className="lp-hero__content">
          <p className="lp-hero__eyebrow">Fidelity Policy RAG · Internal Prototype</p>
          <h1 className="lp-hero__title">Verify Every Answer.</h1>
          <p className="lp-hero__subtitle">
            Policy-grounded AI that eliminates hallucinations for financial
            services — powered by a custom C++ vector database and verified
            source citations.
          </p>

          <form className="lp-input-box" onSubmit={handleSubmit}>
            <input
              className="lp-input-box__field"
              type="text"
              placeholder="Ask about Fidelity policy, fees, withdrawals, RMDs…"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              aria-label="Ask a policy question"
            />
            <div className="lp-input-box__footer">
              <span className="lp-input-box__hint">
                Powered by C++ vector search + LLM grounding
              </span>
              <button
                type="submit"
                className="lp-input-box__submit"
                disabled={!question.trim()}
                aria-label="Submit question"
              >
                ↑
              </button>
            </div>
          </form>

          <p className="lp-hero__note">
            Or{" "}
            <Link to="/chat" className="lp-hero__note-link">
              open the demo directly →
            </Link>
          </p>
        </div>
      </section>

      {/* ── How It Works ───────────────────────────────── */}
      <section className="lp-hiw" id="how-it-works">
        <p className="lp-section-eyebrow">Under the hood</p>
        <h2 className="lp-section-title">How VeriFi works</h2>
        <p className="lp-section-subtitle">
          Three steps from your question to a fully cited, hallucination-resistant answer.
        </p>

        <div className="lp-hiw__cards">
          {HOW_IT_WORKS.map(({ step, title, body }) => (
            <div key={step} className="lp-hiw__card">
              <span className="lp-hiw__step">{step}</span>
              <h3 className="lp-hiw__card-title">{title}</h3>
              <p className="lp-hiw__card-body">{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Technology ─────────────────────────────────── */}
      <section className="lp-tech" id="technology">
        <p className="lp-section-eyebrow">Built with</p>
        <h2 className="lp-section-title">Purpose-built for accuracy</h2>
        <p className="lp-section-subtitle">
          No off-the-shelf vector store. A hand-rolled C++ engine with
          exact cosine similarity math — lightweight, fast, and fully
          transparent.
        </p>
        <div className="lp-tech__pills">
          {TECH_PILLS.map((pill) => (
            <span key={pill} className="lp-tech__pill">{pill}</span>
          ))}
        </div>
      </section>

      {/* ── CTA ────────────────────────────────────────── */}
      <section className="lp-cta">
        <h2 className="lp-cta__title">Ready to see it live?</h2>
        <p className="lp-cta__body">
          Ask a real Fidelity policy question and watch the full RAG pipeline
          retrieve, ground, and cite its answer.
        </p>
        <Link to="/chat" className="lp-btn lp-btn--primary lp-btn--lg">
          Open the Demo →
        </Link>
      </section>

      {/* ── Team ───────────────────────────────────────── */}
      <section className="lp-team" id="team">
        <p className="lp-section-eyebrow">The people behind VeriFi</p>
        <h2 className="lp-section-title">Meet the team</h2>
        <p className="lp-section-subtitle">
          The five people building VeriFi end to end — from document ingestion
          to grounded answers in the UI.
        </p>

        <ul className="lp-team__grid">
          {TEAM.map(({ name, initials }) => (
            <li key={name} className="lp-team__card">
              <span className="lp-team__avatar" aria-hidden="true">
                {initials}
              </span>
              <p className="lp-team__name">{name}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* ── Footer ─────────────────────────────────────── */}
      <footer className="lp-footer">
        <div className="lp-footer__logo">
          <span className="lp-nav__logo-icon lp-nav__logo-icon--sm">F</span>
          <span className="lp-footer__name">VeriFi</span>
        </div>
        <p className="lp-footer__note">
          Internal prototype · Fidelity policy documents · Not for public use
        </p>
      </footer>
    </div>
  );
}

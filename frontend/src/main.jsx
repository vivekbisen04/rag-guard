import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import rehypeSanitize from "rehype-sanitize";
import "./styles.css";

async function api(path, token, options = {}) {
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(path, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok)
    throw new Error(data.detail || `Request failed (${response.status})`);
  return data;
}

function Panel({ title, subtitle, children }) {
  return (
    <section className="panel">
      <header>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </header>
      {children}
    </section>
  );
}

function AnswerMessage({ message }) {
  const [expanded, setExpanded] = useState(false);
  const longAnswer = message.text.length > 1100;
  return (
    <article className="message answer">
      <div className="answer-heading">
        <span className="assistant-avatar">✦</span>
        <span className="message-label">RAG Guard</span>
      </div>
      <div
        className={`answer-body ${longAnswer && !expanded ? "collapsed" : ""}`}
      >
        <Markdown
          className="answer-content"
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[rehypeRaw, rehypeSanitize]}
          components={{
            a: ({ children, ...props }) => (
              <a {...props} target="_blank" rel="noopener noreferrer">
                {children}
              </a>
            ),
          }}
        >
          {message.text}
        </Markdown>
      </div>
      {longAnswer && (
        <div className="answer-actions">
          <button
            className="expand-toggle"
            onClick={() => setExpanded((value) => !value)}
            aria-expanded={expanded}
          >
            {expanded ? "Show less" : "Show full answer"}
          </button>
        </div>
      )}
      <details className="references">
        <summary>
          Sources <span>{message.sources.length}</span>
          <small>{message.ms} ms retrieval</small>
        </summary>
        <div className="source-list">
          {message.sources.length ? (
            message.sources.map((source) => (
              <span className="source" key={source.chunk_id}>
                {source.title} <em>chunk {source.chunk_id}</em>
              </span>
            ))
          ) : (
            <span>No matching sources</span>
          )}
        </div>
      </details>
    </article>
  );
}

function App() {
  const [email, setEmail] = useState("admin@alpha.example");
  const [password, setPassword] = useState("demo-password");
  const [token, setToken] = useState("");
  const [profile, setProfile] = useState(null);
  const [view, setView] = useState("chat");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [title, setTitle] = useState("");
  const [roles, setRoles] = useState(["admin", "manager", "employee"]);
  const [file, setFile] = useState(null);
  const [auditRows, setAuditRows] = useState(null);
  const [auditUser, setAuditUser] = useState("");
  const conversationRef = useRef(null);

  useEffect(() => {
    const container = conversationRef.current;
    if (!container) return;

    container.scrollTop = container.scrollHeight;
  }, [messages, busy]);

  async function signIn(event) {
    event.preventDefault();
    setBusy(true);
    setNotice("");
    try {
      const session = await api("/login", "", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const me = await api("/me", session.access_token);
      setToken(session.access_token);
      setProfile(me);
      setMessages([]);
      setAuditRows(null);
      setView("chat");
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function send(event) {
    event.preventDefault();
    const text = query.trim();
    if (!text || busy) return;
    setQuery("");
    setMessages((previous) => [...previous, { type: "question", text }]);
    setBusy(true);
    setNotice("");
    try {
      const result = await api("/chat", token, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: text }),
      });
      setMessages((previous) => [
        ...previous,
        {
          type: "answer",
          text: result.answer,
          sources: result.sources,
          ms: result.retrieval_ms,
        },
      ]);
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function upload(event) {
    event.preventDefault();
    if (!file || !title.trim()) return;
    const formElement = event.currentTarget;
    setBusy(true);
    setNotice("");
    try {
      const form = new FormData();
      form.append("title", title.trim());
      form.append("allowed_roles", roles.join(","));
      form.append("file", file);
      const result = await api("/ingest", token, {
        method: "POST",
        body: form,
      });
      setNotice(`Document ${result.document_id} was uploaded.`);
      setTitle("");
      setFile(null);
      formElement.reset();
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function loadAudit(event) {
    event.preventDefault();
    setBusy(true);
    setNotice("");
    try {
      const params = new URLSearchParams();
      if (auditUser.trim()) params.set("user_id", auditUser.trim());
      setAuditRows(
        await api(`/admin/audit${params.size ? `?${params}` : ""}`, token),
      );
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  function toggleRole(role) {
    if (role === "admin") return;
    setRoles((previous) =>
      previous.includes(role)
        ? previous.filter((item) => item !== role)
        : [...previous, role],
    );
  }

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">◆</span> RAG Guard
        </div>
        <span>Permission-aware document search</span>
      </header>
      {!profile ? (
        <main className="login-wrap">
          <Panel
            title="Sign in"
            subtitle="Explore tenant and role scoped answers with a demo account."
          >
            <form className="form-stack" onSubmit={signIn}>
              <label>
                Email
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </label>
              <label>
                Password
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </label>
              <button disabled={busy}>
                {busy ? "Signing in…" : "Sign in"}
              </button>
            </form>
            <p className="hint">Demo: admin@alpha.example / demo-password</p>
            {notice && (
              <p className="notice error" role="alert">
                {notice}
              </p>
            )}
          </Panel>
        </main>
      ) : (
        <div className="workspace">
          <aside className="sidebar">
            <div className="account">
              <div className="avatar">{profile.role[0].toUpperCase()}</div>
              <div>
                <strong>{email}</strong>
                <small>
                  {profile.role} · tenant {profile.tenant_id.slice(0, 8)}
                </small>
              </div>
            </div>
            <nav aria-label="Main navigation">
              <button
                className={view === "chat" ? "active" : ""}
                onClick={() => {
                  setView("chat");
                  setNotice("");
                }}
              >
                Chat
              </button>
              {profile.role === "admin" && (
                <>
                  <button
                    className={view === "ingest" ? "active" : ""}
                    onClick={() => {
                      setView("ingest");
                      setNotice("");
                    }}
                  >
                    Ingest
                  </button>
                  <button
                    className={view === "audit" ? "active" : ""}
                    onClick={() => {
                      setView("audit");
                      setNotice("");
                    }}
                  >
                    Audit log
                  </button>
                </>
              )}
            </nav>
            <button
              className="signout"
              onClick={() => {
                setToken("");
                setProfile(null);
                setMessages([]);
                setNotice("");
              }}
            >
              Sign out
            </button>
          </aside>
          <main className="content">
            {notice && (
              <p
                className={`notice ${notice.includes("uploaded") ? "success" : "error"}`}
                role="status"
              >
                {notice}
              </p>
            )}
            {view === "chat" && (
              <Panel
                title="Chat with your documents"
                subtitle="Answers use sources available to your tenant and role."
              >
                <div
                  className="conversation"
                  aria-live="polite"
                  ref={conversationRef}
                >
                  {!messages.length && (
                    <div className="empty">
                      <div className="empty-icon">✦</div>
                      <strong>Ask a question to get started</strong>
                      <p>
                        Try asking about a policy or document you can access.
                      </p>
                    </div>
                  )}
                  {messages.map((message, index) =>
                    message.type === "answer" ? (
                      <AnswerMessage key={index} message={message} />
                    ) : (
                      <article className="message question" key={index}>
                        <span className="message-label">You</span>
                        <div className="message-text">{message.text}</div>
                      </article>
                    ),
                  )}
                </div>
                <form className="composer" onSubmit={send}>
                  <textarea
                    rows="3"
                    maxLength="4000"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Ask a question…"
                  />
                  <button disabled={busy || !query.trim()}>
                    {busy ? "Thinking…" : "Send"}
                  </button>
                </form>
              </Panel>
            )}
            {view === "ingest" && (
              <Panel
                title="Ingest a document"
                subtitle="The selected roles determine who can retrieve this document."
              >
                <form className="form-stack" onSubmit={upload}>
                  <label>
                    Document title
                    <input
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      required
                      maxLength="200"
                    />
                  </label>
                  <fieldset>
                    <legend>Allowed roles</legend>
                    {["admin", "manager", "employee"].map((role) => (
                      <label className="check" key={role}>
                        <input
                          type="checkbox"
                          checked={roles.includes(role)}
                          disabled={role === "admin"}
                          onChange={() => toggleRole(role)}
                        />
                        {role}
                      </label>
                    ))}
                  </fieldset>
                  <label>
                    File
                    <input
                      type="file"
                      accept=".txt,.md,.markdown,.pdf"
                      required
                      onChange={(e) => setFile(e.target.files?.[0] || null)}
                    />
                  </label>
                  <p className="hint">Text, Markdown, or PDF · maximum 10 MB</p>
                  <button disabled={busy || !file || !title.trim()}>
                    {busy ? "Uploading…" : "Upload document"}
                  </button>
                </form>
              </Panel>
            )}
            {view === "audit" && (
              <Panel
                title="Audit log"
                subtitle="Recent chat requests from your tenant."
              >
                <form className="audit-controls" onSubmit={loadAudit}>
                  <label>
                    User ID (optional)
                    <input
                      value={auditUser}
                      onChange={(e) => setAuditUser(e.target.value)}
                      placeholder="Filter by user UUID"
                    />
                  </label>
                  <button disabled={busy}>
                    {busy ? "Loading…" : "Refresh"}
                  </button>
                </form>
                {auditRows &&
                  (auditRows.length ? (
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>Time</th>
                            <th>User</th>
                            <th>Role</th>
                            <th>Query</th>
                            <th>Chunks</th>
                            <th>Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {auditRows.map((row) => (
                            <tr key={row.id}>
                              <td>
                                {new Date(row.created_at).toLocaleString()}
                              </td>
                              <td className="mono">
                                {row.user_id.slice(0, 8)}…
                              </td>
                              <td>{row.role}</td>
                              <td>{row.query}</td>
                              <td>
                                {row.retrieved_chunk_ids.join(", ") || "—"}
                              </td>
                              <td>
                                <span className={`status ${row.status}`}>
                                  {row.status}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="hint">No matching requests.</p>
                  ))}
              </Panel>
            )}
          </main>
        </div>
      )}
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);

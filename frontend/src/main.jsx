import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {Upload, Send, FileText, ChevronDown, Bot, User, Loader2, Lock, LogOut} from 'lucide-react';
import './style.css';

const API = 'http://localhost:8000/api';
const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt', '.md'];
const MAX_QUESTION_LENGTH = 2000;

const getSavedSession = () => {
  try {
    return JSON.parse(localStorage.getItem('eka_session'));
  } catch (err) {
    localStorage.removeItem('eka_session');
    return null;
  }
};

function App() {
  const [session, setSession] = useState(getSavedSession);
  const [loginForm, setLoginForm] = useState({username: '', password: ''});
  const [loginError, setLoginError] = useState('');
  const [loggingIn, setLoggingIn] = useState(false);
  const [docs, setDocs] = useState([]);
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [questionError, setQuestionError] = useState('');

  const load = () => fetch(API + '/documents')
    .then(r => r.json())
    .then(setDocs)
    .catch(() => {});

  useEffect(() => {
    if (session) {
      load();
    }
  }, [session]);

  const login = async e => {
    e.preventDefault();
    const username = loginForm.username.trim();
    const password = loginForm.password;

    if (!username || !password) {
      setLoginError('Enter both username and password.');
      return;
    }

    setLoginError('');
    setLoggingIn(true);

    try {
      const r = await fetch(API + '/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username, password})
      });
      const d = await r.json();

      if (!r.ok) {
        setLoginError(d.detail || 'Login failed.');
        return;
      }

      const nextSession = {token: d.token, username: d.username};
      localStorage.setItem('eka_session', JSON.stringify(nextSession));
      setSession(nextSession);
    } catch (err) {
      setLoginError('Backend is unavailable. Start the FastAPI server and try again.');
    } finally {
      setLoggingIn(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('eka_session');
    setSession(null);
    setDocs([]);
    setMessages([]);
    setQuestion('');
    setUploadError('');
    setQuestionError('');
  };

  const validateFile = file => {
    if (!file) {
      return 'Choose a document to upload.';
    }

    const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();

    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      return 'Unsupported file type. Supported: PDF, DOCX, TXT, MD.';
    }

    if (file.size === 0) {
      return 'Uploaded file is empty.';
    }

    return '';
  };

  const upload = async e => {
    const f = e.target.files?.[0];
    const error = validateFile(f);
    e.target.value = '';

    if (error) {
      setUploadError(error);
      return;
    }

    setUploadError('');
    setUploading(true);
    const fd = new FormData();
    fd.append('file', f);

    try {
      const r = await fetch(API + '/documents/upload', {method: 'POST', body: fd});
      const d = await r.json();
      alert(d.message || d.detail);
      load();
    } finally {
      setUploading(false);
    }
  };

  const validateQuestion = value => {
    const q = value.trim();

    if (!q) {
      return 'Enter a question before sending.';
    }

    if (q.length > MAX_QUESTION_LENGTH) {
      return `Question must be ${MAX_QUESTION_LENGTH} characters or fewer.`;
    }

    return '';
  };

  const ask = async () => {
    const error = validateQuestion(question);

    if (error || loading) {
      setQuestionError(error);
      return;
    }

    const q = question.trim();
    setQuestionError('');
    setMessages(m => [...m, {role: 'user', text: q}]);
    setQuestion('');
    setLoading(true);

    try {
      const r = await fetch(API + '/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({question: q})
      });
      const d = await r.json();

      if (!r.ok) {
        setMessages(m => [...m, {role: 'assistant', text: d.detail || 'Unable to answer this question.'}]);
        return;
      }

      setMessages(m => [...m, {role: 'assistant', text: d.answer, clarification: d.clarification, sources: d.sources || []}]);
    } catch (err) {
      setMessages(m => [...m, {role: 'assistant', text: 'Backend is unavailable. Start the FastAPI server and try again.'}]);
    } finally {
      setLoading(false);
    }
  };

  if (!session) {
    return (
      <div className="login-page">
        <form className="login-panel" onSubmit={login}>
          <div className="login-mark"><Lock size={24}/></div>
          <h1>Enterprise Knowledge Assistant</h1>
          <p>Sign in to access document search and grounded answers.</p>
          <label>
            <span>Username</span>
            <input
              value={loginForm.username}
              onChange={e => setLoginForm({...loginForm, username: e.target.value})}
              autoComplete="username"
            />
          </label>
          <label>
            <span>Password</span>
            <input
              type="password"
              value={loginForm.password}
              onChange={e => setLoginForm({...loginForm, password: e.target.value})}
              autoComplete="current-password"
            />
          </label>
          {loginError && <div className="form-error">{loginError}</div>}
          <button type="submit" disabled={loggingIn}>
            {loggingIn ? <Loader2 size={18} className="spin"/> : <Lock size={18}/>}
            Sign In
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="app">
      <header>
        <div>
          <h1>Enterprise Knowledge Assistant</h1>
          <p>Grounded document Q&A • RAG</p>
        </div>
        <div className="header-actions">
          <div className="status"><span/>Knowledge Base</div>
          <button className="logout" onClick={logout} title="Sign out"><LogOut size={17}/></button>
        </div>
      </header>
      <main>
        <aside>
          <div className="panel-title">
            <span>Documents</span>
            <label className="upload">
              {uploading ? <Loader2 size={18} className="spin"/> : <Upload size={18}/>}
              <input type="file" accept=".pdf,.docx,.txt,.md" onChange={upload}/>
            </label>
          </div>
          <p className="muted">Upload policies, FAQs, manuals or wikis.</p>
          {uploadError && <div className="form-error">{uploadError}</div>}
          {docs.map(d => <div className="doc" key={d.name}><FileText size={18}/><span>{d.name}</span></div>)}
          {!docs.length && <div className="empty">No documents indexed yet.</div>}
        </aside>
        <section className="chat">
          <div className="welcome">
            <Bot size={28}/>
            <div>
              <h2>Ask your knowledge base</h2>
              <p>I answer only from uploaded documents and show the evidence used.</p>
            </div>
          </div>
          <div className="messages">
            {messages.map((m, i) => (
              <div className={'msg ' + m.role} key={i}>
                <div className="avatar">{m.role === 'user' ? <User size={17}/> : <Bot size={17}/>}</div>
                <div className="bubble">
                  <div>{m.text}</div>
                  {m.clarification && <div className="clarify">{m.clarification}</div>}
                  {m.sources?.length > 0 && (
                    <details>
                      <summary>
                        <FileText size={15}/>
                        View Source ({m.sources.length})
                        <span className="summary-score">
                          Best Similarity: {Math.max(...m.sources.map(s => s.score || 0)).toFixed(3)}
                        </span>
                        <ChevronDown size={15}/>
                      </summary>
                      {m.sources.map((s, j) => (
                        <div className="source" key={j}>
                          <b>[{j + 1}] {s.document}{s.page ? ` • Page ${s.page}` : ''}</b>
                          <p>{s.snippet}</p>
                          <small>Similarity: {s.score.toFixed(3)}</small>
                        </div>
                      ))}
                    </details>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="msg assistant">
                <div className="avatar"><Bot size={17}/></div>
                <div className="bubble"><Loader2 className="spin"/></div>
              </div>
            )}
          </div>
          <div className="composer">
            <textarea
              value={question}
              onChange={e => {
                setQuestion(e.target.value);
                if (questionError) {
                  setQuestionError('');
                }
              }}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  ask();
                }
              }}
              maxLength={MAX_QUESTION_LENGTH}
              placeholder="Ask a question about your documents..."
            />
            <button onClick={ask} disabled={!question.trim() || loading}><Send size={19}/></button>
          </div>
          {questionError && <div className="composer-error">{questionError}</div>}
        </section>
      </main>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App/>);

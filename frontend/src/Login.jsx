import { useState } from 'react';
import { signIn } from './api';

export default function Login({ onSignedIn }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      onSignedIn(await signIn(username.trim(), password));
    } catch (signInError) {
      setError(signInError.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="auth-shell">
      <section className="auth-card" aria-labelledby="sign-in-title">
        <div className="auth-mark" aria-hidden="true">A</div>
        <p className="auth-eyebrow">Archive / Research desk</p>
        <h1 id="sign-in-title">Sign in</h1>
        <p className="auth-description">Your documents are private to your account.</p>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="username">Username</label>
          <input
            autoComplete="username"
            autoFocus
            id="username"
            name="username"
            onChange={(event) => setUsername(event.target.value)}
            required
            value={username}
          />
          <label htmlFor="password">Password</label>
          <input
            autoComplete="current-password"
            id="password"
            name="password"
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button className="auth-submit" disabled={submitting} type="submit">
            {submitting ? 'Signing in…' : 'Continue'}
          </button>
        </form>
      </section>
    </main>
  );
}

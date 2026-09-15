/**
 * Authentication UI bridge for the existing HAVCAN single-page experience.
 *
 * The app screens remain unchanged underneath this gate. This file only
 * handles the real session lifecycle and hydrates existing profile elements.
 */
(function (global) {
  'use strict';

  let currentUser = null;
  let authMode = 'login';
  let pendingAction = null;

  function get(id) {
    return document.getElementById(id);
  }

  function setStatus(message, isError) {
    const status = get('auth-status');
    if (!status) return;
    status.textContent = message || '';
    status.className = `text-[11px] min-h-[16px] mt-3 ${isError ? 'text-red-600' : 'text-emerald-600'}`;
  }

  function setBusy(button, busy, label) {
    if (!button) return;
    button.disabled = busy;
    button.classList.toggle('opacity-60', busy);
    button.querySelector('[data-submit-label]').textContent = busy ? 'Please wait…' : label;
  }

  function initials(name) {
    return String(name || 'H')
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0])
      .join('')
      .toUpperCase() || 'H';
  }

  function avatarFor(user) {
    if (user.profile_image) return user.profile_image;
    return `data:image/svg+xml,${encodeURIComponent(
      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128"><rect width="128" height="128" rx="64" fill="#6D28D9"/><text x="64" y="76" text-anchor="middle" fill="white" font-family="Arial" font-size="44" font-weight="700">${initials(user.name)}</text></svg>`,
    )}`;
  }

  function hydrateUser(user) {
    currentUser = user;
    const avatar = avatarFor(user);
    document.querySelectorAll('[data-user-name]').forEach((element) => {
      element.textContent = user.name;
    });
    document.querySelectorAll('[data-user-email]').forEach((element) => {
      element.textContent = user.email;
    });
    document.querySelectorAll('[data-user-role]').forEach((element) => {
      element.textContent = user.role;
    });
    document.querySelectorAll('[data-user-avatar]').forEach((element) => {
      element.src = avatar;
      element.alt = `${user.name} avatar`;
    });
  }

  function showApp() {
    const gate = get('auth-gate');
    if (gate) {
      gate.classList.add('hidden');
      gate.setAttribute('aria-hidden', 'true');
    }
    const main = get('app-viewport');
    if (main) main.removeAttribute('aria-hidden');
  }

  function showGate() {
    const gate = get('auth-gate');
    if (gate) {
      gate.classList.remove('hidden');
      gate.removeAttribute('aria-hidden');
    }
    const main = get('app-viewport');
    if (main) main.setAttribute('aria-hidden', 'true');
  }

  function resumePendingAction() {
    const action = pendingAction;
    pendingAction = null;
    if (typeof action === 'function') {
      global.setTimeout(action, 0);
    }
  }

  function showLogin(action) {
    if (typeof action === 'function') pendingAction = action;
    showGate();
    updateAuthMode('login');
    const email = get('auth-login-form')?.querySelector('[name="email"]');
    if (email) global.setTimeout(() => email.focus(), 0);
  }

  function requireAuth(action) {
    if (currentUser) return true;
    showLogin(action);
    return false;
  }

  function updateAuthMode(mode) {
    authMode = mode;
    const login = get('auth-login-panel') || get('auth-login-form');
    const signup = get('auth-signup-panel') || get('auth-signup-form');
    const forgot = get('auth-forgot-panel');
    if (login) login.classList.toggle('hidden', mode !== 'login');
    if (signup) signup.classList.toggle('hidden', mode !== 'signup');
    if (forgot) forgot.classList.toggle('hidden', mode !== 'forgot');
    const title = get('auth-title');
    const subtitle = get('auth-subtitle');
    const submit = get('auth-submit');
    if (title) title.textContent = mode === 'signup' ? 'Create your HAVCAN account' : mode === 'forgot' ? 'Reset your password' : 'Welcome back';
    if (subtitle) subtitle.textContent = mode === 'signup' ? 'Start turning your ideas into finished work.' : mode === 'forgot' ? 'We’ll help you get back into your account.' : 'Creative work, handled from idea to delivery.';
    if (submit) {
      submit.classList.toggle('hidden', mode === 'forgot');
      submit.querySelector('[data-submit-label]').textContent = mode === 'signup' ? 'Create account' : 'Log in';
    }
    setStatus('');
  }

  function showAuthError(error) {
    const detail = error && error.body && error.body.detail;
    if (Array.isArray(detail)) {
      setStatus(detail.map((item) => item.msg).join(' '), true);
    } else {
      setStatus(detail || (error && error.message) || 'Something went wrong. Please try again.', true);
    }
  }

  async function submitLoginOrSignup(event) {
    event.preventDefault();
    const isSignup = authMode === 'signup';
    const form = event.currentTarget;
    const button = event.submitter || form.querySelector('button[type="submit"]');
    const values = Object.fromEntries(new FormData(form).entries());
    setBusy(button, true, isSignup ? 'Create account' : 'Log in');
    setStatus('');
    try {
      const result = isSignup
        ? await global.HavcanAPI.register(values)
        : await global.HavcanAPI.login(values);
      hydrateUser(result.user);
      showApp();
      form.reset();
      resumePendingAction();
    } catch (error) {
      showAuthError(error);
    } finally {
      setBusy(button, false, isSignup ? 'Create account' : 'Log in');
    }
  }

  async function submitForgot(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector('button[type="submit"]');
    setBusy(button, true, 'Send reset link');
    try {
      const result = await global.HavcanAPI.forgotPassword(
        Object.fromEntries(new FormData(form).entries()),
      );
      setStatus(result.message, false);
      form.reset();
    } catch (error) {
      showAuthError(error);
    } finally {
      setBusy(button, false, 'Send reset link');
    }
  }

  async function submitReset(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector('button[type="submit"]');
    setBusy(button, true, 'Set new password');
    try {
      const result = await global.HavcanAPI.resetPassword(
        Object.fromEntries(new FormData(form).entries()),
      );
      setStatus(result.message, false);
      form.reset();
      updateAuthMode('login');
    } catch (error) {
      showAuthError(error);
    } finally {
      setBusy(button, false, 'Set new password');
    }
  }

  async function logout() {
    try {
      await global.HavcanAPI.logout();
    } catch (error) {
      // Even if the network is unavailable, clear the local view of the session.
      setStatus(error.message, true);
    }
    currentUser = null;
    pendingAction = null;
    showApp();
    updateAuthMode('login');
    if (typeof global.switchNav === 'function') {
      global.switchNav('home', get('nav-btn-home'));
    }
  }

  async function initialize() {
    try {
      const result = await global.HavcanAPI.me();
      hydrateUser(result.user);
      showApp();
    } catch (error) {
      currentUser = null;
      showApp();
      updateAuthMode('login');
      if (error.status && error.status !== 401) {
        setStatus('Authentication service is unavailable. Please try again shortly.', true);
      }
    }
  }

  function bind() {
    const loginForm = get('auth-login-form');
    const signupForm = get('auth-signup-form');
    const forgotForm = get('auth-forgot-form');
    if (loginForm) loginForm.addEventListener('submit', submitLoginOrSignup);
    if (signupForm) signupForm.addEventListener('submit', submitLoginOrSignup);
    if (forgotForm) forgotForm.addEventListener('submit', submitForgot);
    const resetForm = get('auth-reset-form');
    if (resetForm) resetForm.addEventListener('submit', submitReset);
    document.querySelectorAll('[data-auth-mode]').forEach((button) => {
      button.addEventListener('click', () => updateAuthMode(button.dataset.authMode));
    });
    const logoutButton = get('logout-button');
    if (logoutButton) logoutButton.addEventListener('click', logout);
    const resetToken = new URLSearchParams(global.location.search).get('reset_token');
    if (resetToken && get('reset-token')) get('reset-token').value = resetToken;
    updateAuthMode('login');
    initialize();
  }

  global.HavcanAuth = Object.freeze({
    getUser: () => currentUser,
    logout,
    requireAuth,
    showLogin,
  });

  document.addEventListener('DOMContentLoaded', bind);
})(window);
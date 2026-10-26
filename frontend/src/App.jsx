
// =========================================================================
// AUTHENTICATION MODAL (Sign In / Register / Demo Login)
// =========================================================================
function AuthModal({ isOpen, onClose, onAuthSuccess, initialMode = 'login' }) {
  if (!isOpen) return null;

  const [mode, setMode] = useState(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const endpoint = mode === 'login' ? '/api/auth/login' : '/api/auth/register';
      const payload = mode === 'login' ? { email, password } : { name, email, password };
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        onAuthSuccess(data.token, data.user);
        onClose();
      } else {
        setError(data.error || 'Authentication failed. Please check credentials.');
      }
    } catch (err) {
      setError('Network error contacting authentication service.');
    } finally {
      setLoading(false);
    }
  };

  const handleDemo = async () => {
    setError('');
    setLoading(true);
    try {
      const res = await fetch('/api/auth/demo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      const data = await res.json();
      if (res.ok && data.success) {
        onAuthSuccess(data.token, data.user);
        onClose();
      } else {
        setError(data.error || 'Demo login failed.');
      }
    } catch (err) {
      setError('Network error contacting demo service.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="w-full max-w-md bg-slate-900 rounded-3xl border border-indigo-500/40 p-6 md:p-8 shadow-2xl relative glow-indigo">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-1.5 rounded-full text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <Icons.Close />
        </button>

        <div className="text-center space-y-2 mb-6">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-violet-500 flex items-center justify-center mx-auto shadow-lg shadow-indigo-600/30">
            <Icons.Sparkles />
          </div>
          <h3 className="font-display font-extrabold text-2xl text-white tracking-tight">
            Manta<span className="text-indigo-400">Booking</span>
          </h3>
          <p className="text-xs text-slate-400 max-w-xs mx-auto">
            Sign in to unlock all booking studios, track official carrier PNRs, and access your LangGraph AI Co-Pilot.
          </p>
        </div>

        <div className="flex rounded-xl bg-slate-950 p-1 border border-slate-800 mb-5">
          <button
            type="button"
            onClick={() => { setMode('login'); setError(''); }}
            className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
              mode === 'login'
                ? 'bg-gradient-to-r from-indigo-600 to-violet-600 text-white shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setMode('register'); setError(''); }}
            className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
              mode === 'register'
                ? 'bg-gradient-to-r from-indigo-600 to-violet-600 text-white shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Create Account
          </button>
        </div>

        <div className="mb-5 p-3 rounded-2xl bg-gradient-to-r from-emerald-500/10 via-teal-500/10 to-indigo-500/10 border border-emerald-500/30 flex items-center justify-between">
          <div className="space-y-0.5">
            <span className="text-[11px] font-bold text-emerald-300">⚡ Instant Evaluation</span>
            <p className="text-[10px] text-slate-400">Jump right into the full studio with 1 click</p>
          </div>
          <button
            type="button"
            onClick={handleDemo}
            disabled={loading}
            className="px-3.5 py-1.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs shadow-md shadow-emerald-500/20 transition-all active:scale-95 disabled:opacity-50"
          >
            Demo Access ➔
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-red-500/15 border border-red-500/30 text-xs text-red-300">
            ⚠️ {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
          {mode === 'register' && (
            <div className="space-y-1">
              <label className="text-slate-300 font-semibold block">Full Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Satya Desai"
                required={mode === 'register'}
                className="w-full bg-slate-950 border border-slate-700/80 rounded-xl px-3.5 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
          )}

          <div className="space-y-1">
            <label className="text-slate-300 font-semibold block">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              className="w-full bg-slate-950 border border-slate-700/80 rounded-xl px-3.5 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono text-xs"
            />
          </div>

          <div className="space-y-1">
            <label className="text-slate-300 font-semibold block">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              className="w-full bg-slate-950 border border-slate-700/80 rounded-xl px-3.5 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-bold text-sm shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50 active:scale-95"
          >
            {loading ? 'Authenticating...' : mode === 'login' ? 'Sign In to Studio ➔' : 'Create Account & Sign In ➔'}
          </button>

          <div className="pt-2 text-center text-[11px] text-slate-500">
            <span>No account? Use Instant Demo Access for a private guest account.</span>
          </div>
        </form>
      </div>
    </div>
  );
}

// =========================================================================
// VISITOR LANDING PAGE
// =========================================================================
function VisitorLanding({ onOpenAuth, onDemoLogin }) {
  if (!user) {
    return (
      <>
        <VisitorLanding
          onOpenAuth={(m) => {
            setAuthMode(m || 'login');
            setAuthModalOpen(true);
          }}
          onDemoLogin={handleDemoLogin}
        />
        <AuthModal
          isOpen={authModalOpen}
          onClose={() => setAuthModalOpen(false)}
          onAuthSuccess={handleAuthSuccess}
          initialMode={authMode}
        />
      </>
    );
  }

  return (
    <div className="min-h-screen w-full flex flex-col bg-[#090D16] text-slate-100 overflow-y-auto selection:bg-indigo-500/30">
      <header className="sticky top-0 z-30 bg-slate-900/90 border-b border-slate-800/80 px-4 md:px-8 py-3.5 flex items-center justify-between backdrop-blur-md">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-600/30">
            <span className="text-xl">✈️</span>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="font-extrabold text-xl text-white tracking-tight">
                Manta<span className="text-indigo-400">Booking</span>
              </h1>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
                Multi-Mode Portal
              </span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block">
              Direct Verified Carriers • CRIS & IATA PNRs • LangGraph AI Co-Pilot
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2.5">
          <button
            onClick={onDemoLogin}
            className="hidden sm:flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs font-semibold transition-all"
          >
            <span>⚡ 1-Click Demo</span>
          </button>
          <button
            onClick={() => onOpenAuth('login')}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700/70 transition-all"
          >
            Sign In
          </button>
          <button
            onClick={() => onOpenAuth('register')}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-semibold text-xs shadow-lg shadow-indigo-600/30 transition-all active:scale-95"
          >
            Get Started ➔
          </button>
        </div>
      </header>

      {/* HERO SECTION */}
      <section className="relative overflow-hidden pt-12 md:pt-20 pb-16 px-4 md:px-8 border-b border-slate-800/80 text-center space-y-6">
        <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-xs text-indigo-300 font-semibold">
          <span>✦ The Next-Generation Multi-Mode Booking & AI Travel Platform</span>
        </div>

        <h2 className="font-extrabold text-3xl sm:text-5xl md:text-6xl text-white tracking-tight leading-[1.15]">
          Book Flights, Trains, Buses & Events Direct. <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-violet-300 to-emerald-400">
            Verified Carriers. Powered by AI.
          </span>
        </h2>

        <p className="text-slate-400 text-sm md:text-lg max-w-2xl mx-auto leading-relaxed">
          No fake booking IDs, no middleman price markups. MantaBooking links you straight to authorized platforms with prefilled itineraries, tracks live CRIS & IATA carrier PNRs, and provides an embedded LangGraph AI Co-Pilot.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
          <button
            onClick={() => onOpenAuth('login')}
            className="w-full sm:w-auto px-7 py-3.5 rounded-2xl bg-gradient-to-r from-indigo-600 via-indigo-500 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-bold text-sm shadow-xl shadow-indigo-600/30 transition-all hover:scale-105 active:scale-95"
          >
            Sign In to Launch Studio ➔
          </button>

          <button
            onClick={onDemoLogin}
            className="w-full sm:w-auto px-6 py-3.5 rounded-2xl bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 font-bold text-sm transition-all hover:scale-105 active:scale-95"
          >
            ⚡ Instant Demo Access
          </button>
        </div>

        <div className="pt-6 flex flex-wrap items-center justify-center gap-4 text-xs text-slate-400">
          <span>✓ 100% Direct Carrier Checkout</span>
          <span>•</span>
          <span>✓ Official CRIS 10-Digit & IATA PNRs</span>
          <span>•</span>
          <span>✓ LangGraph AI Assistant</span>
          <span>•</span>
          <span>✓ Gmail Dispatch</span>
        </div>
      </section>

      {/* 6 STUDIOS SECTION */}
      <section className="py-16 px-4 md:px-8 max-w-6xl mx-auto space-y-8 text-center">
        <div className="space-y-2">
          <span className="text-xs font-bold uppercase tracking-wider text-indigo-400">Complete Coverage</span>
          <h3 className="font-extrabold text-2xl sm:text-3xl text-white tracking-tight">
            Six Dedicated Booking Studios in One Unified Platform
          </h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-left">
          {[
            { icon: '✈️', title: 'Flights Studio', desc: 'Google Flights, Skyscanner, MakeMyTrip, and IndiGo with real-time seat search and zero hidden agency markups.' },
            { icon: '🚆', title: 'Trains Studio', desc: 'Official Indian Railways (IRCTC), ConfirmTkt, RailYatri, and Trainline (UK/Europe) with live seat charts.' },
            { icon: '🚌', title: 'Buses Studio', desc: 'RedBus, AbhiBus, and FlixBus across thousands of intercity express and AC sleeper bus routes.' },
            { icon: '🍿', title: 'Movies Studio', desc: 'BookMyShow and PVR INOX cinema bookings with IMAX 3D, Dolby Atmos, and 70mm showtimes.' },
            { icon: '🎟️', title: 'Events & Shows', desc: 'Live concert tours (Coldplay, Taylor Swift), sports tournaments (F1, IPL), and festivals via official portals.' },
            { icon: '🏨', title: 'Hotels & Stays', desc: 'Direct resort and hotel reservations through Booking.com, Agoda, and boutique villas.' },
          ].map((item, idx) => (
            <div key={idx} className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800 hover:border-indigo-500/40 transition-all space-y-2.5">
              <div className="text-2xl">{item.icon}</div>
              <h4 className="font-bold text-white text-base">{item.title}</h4>
              <p className="text-xs text-slate-400 leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* FOOTER */}
      <footer className="py-8 px-4 md:px-8 border-t border-slate-800/80 text-center text-xs text-slate-500">
        © 2026 MantaBooking. Carrier PNRs are verified through official railway and airline GDS portals. Zero middleman fees.
      </footer>
    </div>
  );
}

import React, { useState, useEffect, useRef } from 'react';
import MessageBubble from './components/MessageBubble';
import { Icons } from './components/Icons';

const CATEGORIES = [
  { id: 'flight', label: 'Flights', icon: '✈️', color: 'indigo' },
  { id: 'train', label: 'Trains', icon: '🚆', color: 'emerald' },
  { id: 'bus', label: 'Buses', icon: '🚌', color: 'amber' },
  { id: 'movie', label: 'Movies', icon: '🍿', color: 'rose' },
  { id: 'event', label: 'Events & Concerts', icon: '🎟️', color: 'purple' },
  { id: 'hotel', label: 'Hotels', icon: '🏨', color: 'sky' }
];

export default function App() {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('mantabooking_user');
      return stored ? JSON.parse(stored) : null;
    } catch (e) {
      return null;
    }
  });
  const [authToken, setAuthToken] = useState(() => {
    return localStorage.getItem('mantabooking_token') || '';
  });
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState('login');

  useEffect(() => {
    if (authToken) {
      fetch('/api/auth/me', {
        headers: { 'Authorization': `Bearer ${authToken}` }
      })
        .then(res => res.json())
        .then(data => {
          if (data.authenticated && data.user) {
            setUser(data.user);
            localStorage.setItem('mantabooking_user', JSON.stringify(data.user));
          } else {
            handleLogout();
          }
        })
        .catch(() => {});
    }
  }, []);

  const handleAuthSuccess = (token, userData) => {
    setAuthToken(token);
    setUser(userData);
    localStorage.setItem('mantabooking_token', token);
    localStorage.setItem('mantabooking_user', JSON.stringify(userData));
    setAuthModalOpen(false);
  };

  const handleLogout = async () => {
    if (authToken) {
      try {
        await fetch('/api/auth/logout', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${authToken}` }
        });
      } catch (e) {}
    }
    setAuthToken('');
    setUser(null);
    localStorage.removeItem('mantabooking_token');
    localStorage.removeItem('mantabooking_user');
    setBookings([]);
    setBookingCount(0);
  };

  const handleDemoLogin = async () => {
    try {
      const res = await fetch('/api/auth/demo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await res.json();
      if (res.ok && data.success) {
        handleAuthSuccess(data.token, data.user);
      }
    } catch (e) {
      console.warn('Demo login failed:', e);
    }
  };
  const [activeTab, setActiveTab] = useState('flight'); // flight, train, bus, movie, event, hotel, pnr, bookings
  const [platforms, setPlatforms] = useState({});
  const [loadingPlatforms, setLoadingPlatforms] = useState(false);

  // Search Form State
  const [searchParams, setSearchParams] = useState({
    origin: 'New York (JFK)',
    destination: 'London (LHR)',
    date: new Date(Date.now() + 86400000 * 7).toISOString().split('T')[0],
    passengers: 1,
    travelClass: 'Economy'
  });

  // PNR Tracker State

  const [pnrInput, setPnrInput] = useState('');
  const [pnrResult, setPnrResult] = useState(null);
  const [pnrLoading, setPnrLoading] = useState(false);

  // Bookings Store
  const [bookings, setBookings] = useState([]);
  const [bookingCount, setBookingCount] = useState(0);

  // AI Co-Pilot State
  const [coPilotOpen, setCoPilotOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      sender: 'agent',
      content: 'Hello! I am your MantaBooking AI Co-Pilot powered by LangGraph. I can compare travel platforms, check PNR formats, verify transit guidelines, and format itineraries. How can I help you today?',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [threadId, setThreadId] = useState(() => Math.random().toString(36).slice(2, 10)); // per-tab conversation id (server also scopes it to the user)
  const chatEndRef = useRef(null);

  // Modal State for Manual Ticket / Draft Itinerary Registration
  const [registerModalOpen, setRegisterModalOpen] = useState(false);
  const [selectedPlatformForModal, setSelectedPlatformForModal] = useState(null);
  const [modalOfficialPnr, setModalOfficialPnr] = useState('');
  const [modalPassengerName, setModalPassengerName] = useState('');

  useEffect(() => {
    fetchPlatforms();
    fetchBookings();
  }, []);

  useEffect(() => {
    if (coPilotOpen) {
      chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, chatLoading, coPilotOpen]);

  const fetchPlatforms = async () => {
    setLoadingPlatforms(true);
    try {
      const res = await fetch('/api/platforms');
      if (res.ok) {
        const data = await res.json();
        setPlatforms(data.catalog || {});
      }
    } catch (e) {
      console.warn('Failed to load platforms:', e);
    } finally {
      setLoadingPlatforms(false);
    }
  };

  const fetchBookings = async () => {
    try {
      const res = await fetch('/api/bookings');
      if (res.ok) {
        const data = await res.json();
        setBookings(data.bookings || []);
        setBookingCount(data.count || 0);
      }
    } catch (e) {
      console.warn('Failed to load bookings:', e);
    }
  };

  const handleTrackPnr = async () => {
    const val = pnrInput.trim();
    if (!val) return;
    setPnrLoading(true);
    try {
      const res = await fetch(`/api/pnr-status?pnr=${encodeURIComponent(val)}`, {
        headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {}
      });
      const data = await res.json();
      setPnrResult(data);
    } catch (e) {
      setPnrResult({
        error: true,
        message: 'Network error contacting PNR status service.'
      });
    } finally {
      setPnrLoading(false);
    }
  };

  const handleSendMessage = async (customPrompt) => {
    const text = (typeof customPrompt === 'string' ? customPrompt : chatInput).trim();
    if (!text || chatLoading) return;

    const userMsg = {
      sender: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setMessages((prev) => [...prev, userMsg]);
    setChatInput('');
    setChatLoading(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, thread_id: threadId })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setMessages((prev) => [
          ...prev,
          {
            sender: 'agent',
            content: data.reply,
            toolsCalled: data.tools_called || [],
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }
        ]);
        if (data.bookings_count !== undefined) {
          setBookingCount(data.bookings_count);
          fetchBookings();
        }
      } else {
        setMessages((prev) => [
          ...prev,
          {
            sender: 'agent',
            content: `⚠️ Error from LangGraph backend: ${data.error || 'Unable to process request.'}`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          sender: 'agent',
          content: '⚠️ Failed to connect to LangGraph backend server on /api/chat. Please ensure server.py is running.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleResetThread = async () => {
    try {
      const res = await fetch('/api/reset', { method: 'POST' });
      const data = await res.json();
      const newId = data.new_thread_id || String(Date.now()).slice(-4);
      setThreadId(newId);
      setMessages([
        {
          sender: 'agent',
          content: `Session reset (Thread ${newId}). MemorySaver checkpointer has been cleared. How can I help you?`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } catch (e) {
      setThreadId(String(Date.now()).slice(-4));
    }
  };

  const handleSaveDraftBooking = async () => {
    if (!selectedPlatformForModal) return;
    try {
      const payload = {
        category: activeTab,
        origin: searchParams.origin,
        destination: searchParams.destination,
        date: searchParams.date,
        passengers: Number(searchParams.passengers),
        platform: selectedPlatformForModal.name,
        passenger_name: modalPassengerName || 'Guest Traveler',
        official_pnr: modalOfficialPnr.trim()
      };
      const res = await fetch('/api/bookings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        setRegisterModalOpen(false);
        setModalOfficialPnr('');
        setModalPassengerName('');
        fetchBookings();
      }
    } catch (e) {
      console.warn('Failed to save booking:', e);
    }
  };

  const currentCategoryPlatforms = platforms[activeTab]?.platforms || [];

  if (!user) {
    return (
      <>
        <VisitorLanding
          onOpenAuth={(m) => {
            setAuthMode(m || 'login');
            setAuthModalOpen(true);
          }}
          onDemoLogin={handleDemoLogin}
        />
        <AuthModal
          isOpen={authModalOpen}
          onClose={() => setAuthModalOpen(false)}
          onAuthSuccess={handleAuthSuccess}
          initialMode={authMode}
        />
      </>
    );
  }

  return (
    <div className="min-h-screen w-full flex flex-col bg-[#090D16] text-slate-100 font-sans selection:bg-indigo-500/30 selection:text-white relative overflow-x-hidden">

      {/* Top Application Navigation */}
      <header className="sticky top-0 z-30 bg-slate-900/90 backdrop-blur-md border-b border-slate-800/80 px-4 md:px-8 py-3.5 flex items-center justify-between shadow-lg">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-600/30">
            <span className="text-xl">✈️</span>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="font-bold text-lg text-white tracking-tight">Manta<span className="text-indigo-400">Booking</span></h1>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
                Booking Portal
              </span>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hidden sm:inline-block">
                AI Co-Pilot Ready
              </span>
            </div>
            <p className="text-xs text-slate-400">Multi-Mode Travel & Event Reservations with AI Assistance</p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-2.5">
          <button
            onClick={() => setActiveTab('pnr')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center space-x-1.5 transition-all ${activeTab === 'pnr'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
              : 'bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border border-slate-700/60'
              }`}
          >
            <span>🔍</span>
            <span>PNR Tracker</span>
          </button>

          <button
            onClick={() => setActiveTab('bookings')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center space-x-1.5 transition-all ${activeTab === 'bookings'
              ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30'
              : 'bg-slate-800/80 hover:bg-slate-700/80 text-emerald-300 border border-emerald-500/30'
              }`}
          >
            <span>🎟️</span>
            <span>My Bookings</span>
            {bookingCount > 0 && (
              <span className="px-1.5 py-0.2 rounded-full bg-emerald-400 text-slate-950 font-bold text-[10px]">
                {bookingCount}
              </span>
            )}
          </button>

          <button
            onClick={() => setCoPilotOpen(true)}
            className="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-semibold flex items-center space-x-1.5 shadow-lg shadow-indigo-600/30 transition-all active:scale-95"
          >
            <Icons.Bot />
            <span>AI Co-Pilot</span>
          </button>

          {user && (
            <div className="flex items-center space-x-2 pl-2 border-l border-slate-800">
              <img
                src={user.avatar || `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(user.name)}`}
                alt={user.name}
                className="w-7 h-7 rounded-lg border border-indigo-500/40 shadow-sm shrink-0"
              />
              <div className="hidden sm:block text-left text-xs leading-tight">
                <div className="font-bold text-white truncate max-w-[110px]">{user.name}</div>
                <div className="text-[10px] text-emerald-400 font-mono">● Signed In</div>
              </div>
              <button
                onClick={handleLogout}
                title="Sign Out"
                className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-red-500/20 text-slate-400 hover:text-red-300 border border-slate-700/60 transition-all text-xs"
              >
                <Icons.Close />
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-8 space-y-8">

        {/* Navigation Category Switcher */}
        <div className="flex items-center space-x-2 overflow-x-auto pb-2 scrollbar-thin">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setActiveTab(cat.id)}
              className={`px-4 py-2.5 rounded-xl font-medium text-xs md:text-sm flex items-center space-x-2 shrink-0 transition-all ${activeTab === cat.id
                ? 'bg-indigo-600/30 border border-indigo-500 text-white shadow-md shadow-indigo-600/20'
                : 'bg-slate-900/60 hover:bg-slate-800/60 border border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
            >
              <span>{cat.icon}</span>
              <span>{cat.label}</span>
            </button>
          ))}
        </div>

        {/* View 1: Booking Search & Studio View */}
        {activeTab !== 'pnr' && activeTab !== 'bookings' && (
          <div className="space-y-6">

            {/* Search Studio Hero Card */}
            <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800/80 p-6 md:p-8 shadow-2xl">
              <div className="relative z-10 space-y-6">
                <div>
                  <h2 className="text-xl md:text-2xl font-bold text-white tracking-tight flex items-center space-x-2">
                    <span>{CATEGORIES.find((c) => c.id === activeTab)?.icon}</span>
                    <span>Book {CATEGORIES.find((c) => c.id === activeTab)?.label}</span>
                  </h2>
                  <p className="text-sm text-slate-400 mt-1">
                    Select your itinerary to generate direct verified platform search links, or ask the AI Co-Pilot to compare fares.
                  </p>
                </div>

                {/* Search Form Inputs */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">
                      {activeTab === 'movie' || activeTab === 'event' ? 'City / Location' : 'From / Origin'}
                    </label>
                    <input
                      type="text"
                      value={searchParams.origin}
                      onChange={(e) => setSearchParams({ ...searchParams, origin: e.target.value })}
                      className="w-full bg-slate-900/90 border border-slate-700/80 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 transition-all"
                      placeholder="e.g. Mumbai (BOM) or New York"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">
                      {activeTab === 'movie' || activeTab === 'event' ? 'Movie / Show Title' : 'To / Destination'}
                    </label>
                    <input
                      type="text"
                      value={searchParams.destination}
                      onChange={(e) => setSearchParams({ ...searchParams, destination: e.target.value })}
                      className="w-full bg-slate-900/90 border border-slate-700/80 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 transition-all"
                      placeholder="e.g. Delhi (DEL) or Coldplay Concert"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">Date</label>
                    <input
                      type="date"
                      value={searchParams.date}
                      onChange={(e) => setSearchParams({ ...searchParams, date: e.target.value })}
                      className="w-full bg-slate-900/90 border border-slate-700/80 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 transition-all"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">Passengers / Tickets</label>
                    <div className="flex space-x-2">
                      <input
                        type="number"
                        min="1"
                        max="9"
                        value={searchParams.passengers}
                        onChange={(e) => setSearchParams({ ...searchParams, passengers: e.target.value })}
                        className="w-20 bg-slate-900/90 border border-slate-700/80 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                      />
                      <button
                        onClick={() => {
                          setCoPilotOpen(true);
                          handleSendMessage(
                            `Please compare fares and platform recommendations for ${CATEGORIES.find((c) => c.id === activeTab)?.label} from ${searchParams.origin} to ${searchParams.destination} on ${searchParams.date} for ${searchParams.passengers} passenger(s).`
                          );
                        }}
                        className="flex-1 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white rounded-xl text-xs font-semibold flex items-center justify-center space-x-1.5 shadow-md shadow-indigo-600/30 transition-all"
                      >
                        <Icons.Sparkles />
                        <span>Compare via AI</span>
                      </button>
                    </div>
                  </div>
                </div>

                {/* Popular Route Presets */}
                <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-slate-400">
                  <span className="text-slate-500">Popular:</span>
                  {[
                    { from: 'BOM', to: 'DEL', label: 'Mumbai ➔ Delhi' },
                    { from: 'BLR', to: 'GOI', label: 'Bengaluru ➔ Goa' },
                    { from: 'JFK', to: 'LHR', label: 'NYC ➔ London' },
                    { from: 'SFO', to: 'HND', label: 'SF ➔ Tokyo' }
                  ].map((preset, idx) => (
                    <button
                      key={idx}
                      onClick={() => setSearchParams({ ...searchParams, origin: preset.from, destination: preset.to })}
                      className="px-2.5 py-1 rounded-lg bg-slate-800/60 hover:bg-slate-700 border border-slate-700/50 text-slate-300 hover:text-white transition-colors"
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Verified Platforms Grid */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-bold text-white tracking-tight">Verified Booking Platforms</h3>
                  <p className="text-xs text-slate-400">
                    Official booking providers with pre-filled routes. Directly checkout on their secure site.
                  </p>
                </div>
                <div className="text-xs text-slate-400 flex items-center space-x-1.5">
                  <Icons.ShieldCheck />
                  <span>Carrier Verified</span>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {currentCategoryPlatforms.map((plat, idx) => {
                  const dynamicLink = `${plat.url}?from=${encodeURIComponent(searchParams.origin)}&to=${encodeURIComponent(searchParams.destination)}&date=${encodeURIComponent(searchParams.date)}`;
                  return (
                    <div
                      key={idx}
                      className="rounded-xl bg-slate-900/60 border border-slate-800/80 p-5 flex flex-col justify-between hover:border-indigo-500/40 hover:bg-slate-800/40 transition-all group"
                    >
                      <div className="space-y-2.5">
                        <div className="flex items-start justify-between">
                          <div>
                            <h4 className="font-bold text-base text-white group-hover:text-indigo-300 transition-colors">
                              {plat.name}
                            </h4>
                            <span className="text-[11px] text-slate-400">{plat.type}</span>
                          </div>
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                            Verified
                          </span>
                        </div>
                        <p className="text-xs text-slate-300 leading-relaxed">{plat.notes}</p>
                      </div>

                      <div className="pt-4 border-t border-slate-800/60 flex items-center justify-between gap-2 mt-4">
                        <a
                          href={dynamicLink}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex-1 py-2 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs text-center shadow-md shadow-indigo-600/20 transition-all flex items-center justify-center space-x-1"
                        >
                          <span>Book on Site</span>
                          <span>➔</span>
                        </a>

                        <button
                          onClick={() => {
                            setSelectedPlatformForModal(plat);
                            setRegisterModalOpen(true);
                          }}
                          title="Save Draft or Record Carrier PNR"
                          className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700/60 text-slate-300 hover:text-white transition-colors"
                        >
                          <Icons.Ticket />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* View 2: PNR Status Tracker */}
        {activeTab === 'pnr' && (
          <div className="max-w-2xl mx-auto space-y-6">
            <div className="text-center space-y-2">
              <div className="w-12 h-12 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center mx-auto text-2xl">
                🔍
              </div>
              <h2 className="text-2xl font-bold text-white tracking-tight">Official PNR Live Status Tracker</h2>
              <p className="text-sm text-slate-400 max-w-md mx-auto">
                Enter your 10-digit Indian Railways PNR or 6-character Airline locator code to inspect live status and access official verification portals.
              </p>
            </div>

            <div className="rounded-2xl bg-slate-900/80 border border-slate-800 p-6 space-y-4 shadow-xl">
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={pnrInput}
                  onChange={(e) => setPnrInput(e.target.value.toUpperCase())}
                  onKeyDown={(e) => e.key === 'Enter' && handleTrackPnr()}
                  placeholder="e.g. 2451890342 (IRCTC) or K9QX2M (Airline)"
                  className="flex-1 bg-slate-950 border border-slate-700/80 rounded-xl px-4 py-3 text-sm font-mono text-white tracking-wider focus:outline-none focus:border-indigo-500"
                />
                <button
                  onClick={handleTrackPnr}
                  disabled={pnrLoading || !pnrInput.trim()}
                  className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 text-white font-semibold text-sm transition-all"
                >
                  {pnrLoading ? 'Checking...' : 'Track PNR'}
                </button>
              </div>

              {pnrResult && (
                <div className="pt-4 border-t border-slate-800 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-xs text-slate-400">System Detected:</span>
                      <h4 className="font-bold text-white text-base">{pnrResult.system}</h4>
                    </div>
                    <span className="px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-indigo-500/10 border border-indigo-500/30 text-indigo-300">
                      {pnrResult.pnr}
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-3.5 rounded-xl border border-slate-800">
                    {pnrResult.notes}
                  </p>

                  {pnrResult.verification_portals && pnrResult.verification_portals.length > 0 && (
                    <div className="space-y-2">
                      <div className="text-xs font-medium text-slate-400">Official Live Verification Portals:</div>
                      <div className="flex flex-wrap gap-2">
                        {pnrResult.verification_portals.map((portal, i) => (
                          <a
                            key={i}
                            href={portal.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/40 border border-indigo-500/30 text-indigo-300 text-xs font-medium flex items-center space-x-1 transition-all"
                          >
                            <span>{portal.name}</span>
                            <span>➔</span>
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* View 3: My Bookings & Boarding Passes */}
        {activeTab === 'bookings' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-white tracking-tight">Registered Bookings & Manifests</h2>
                <p className="text-xs text-slate-400">Active session reservations, drafts, and attached carrier PNRs.</p>
              </div>
              <button
                onClick={fetchBookings}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 flex items-center space-x-1"
              >
                <Icons.Refresh />
                <span>Refresh</span>
              </button>
            </div>

            {bookings.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-800 p-12 text-center space-y-3">
                <div className="text-3xl">🎫</div>
                <div className="text-base font-semibold text-white">No Bookings Recorded Yet</div>
                <p className="text-xs text-slate-400 max-w-sm mx-auto">
                  Select a platform to save a draft itinerary or book via the AI Co-Pilot assistant.
                </p>
                <button
                  onClick={() => setActiveTab('flight')}
                  className="mt-2 px-4 py-2 rounded-xl bg-indigo-600 text-white text-xs font-semibold"
                >
                  Explore Flights & Travel
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {bookings.map((b) => (
                  <div
                    key={b.ticket_id}
                    className="rounded-2xl bg-gradient-to-br from-slate-900 to-indigo-950/20 border border-slate-800 p-5 space-y-4 hover:border-slate-700 transition-all"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                          {b.category}
                        </span>
                        <h4 className="font-bold text-white text-lg mt-1">
                          {b.origin} ➔ {b.destination}
                        </h4>
                      </div>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                        {b.status}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-slate-500">Passenger:</span>
                        <div className="text-slate-300 font-medium">{b.passenger_name || 'Traveler'}</div>
                      </div>
                      <div>
                        <span className="text-slate-500">Departure:</span>
                        <div className="text-slate-300 font-medium">{b.date}</div>
                      </div>
                      <div>
                        <span className="text-slate-500">Draft Ref:</span>
                        <div className="text-indigo-300 font-mono">{b.pnr}</div>
                      </div>
                      <div>
                        <span className="text-slate-500">Official Carrier PNR:</span>
                        <div className="text-emerald-300 font-mono font-bold">
                          {b.official_pnr || 'Awaiting platform checkout'}
                        </div>
                      </div>
                    </div>

                    <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
                      <span className="text-slate-500">Platform: {b.platform}</span>
                      <button
                        onClick={() => {
                          setCoPilotOpen(true);
                          handleSendMessage(`Please check the status of ticket reservation ${b.ticket_id}`);
                        }}
                        className="text-indigo-400 hover:text-indigo-300 font-medium flex items-center space-x-1"
                      >
                        <span>Inspect Status</span>
                        <span>➔</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Floating AI Co-Pilot Toggle Button (FAB) */}
      {!coPilotOpen && (
        <button
          onClick={() => setCoPilotOpen(true)}
          className="fixed bottom-6 right-6 z-40 px-4 py-3 rounded-full bg-gradient-to-r from-indigo-600 via-indigo-500 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-semibold text-sm shadow-xl shadow-indigo-600/40 flex items-center space-x-2 transition-transform hover:scale-105 active:scale-95 border border-indigo-400/30"
        >
          <Icons.Bot />
          <span>Ask AI Co-Pilot</span>
        </button>
      )}

      {/* AI Co-Pilot Slide-over Helper Drawer */}
      {coPilotOpen && (
        <div className="fixed inset-y-0 right-0 z-50 w-full sm:w-[480px] bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col animate-slide-left">

          {/* Drawer Header */}
          <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/90">
            <div className="flex items-center space-x-3">
              <div className="w-9 h-9 rounded-xl bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center">
                <Icons.Bot />
              </div>
              <div>
                <h3 className="font-bold text-white text-sm">AI Booking Co-Pilot</h3>
                <p className="text-[11px] text-slate-400">LangGraph Assistant with Web & Booking Skills</p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={handleResetThread}
                title="Reset Conversation"
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
              >
                <Icons.Refresh />
              </button>
              <button
                onClick={() => setCoPilotOpen(false)}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
              >
                <Icons.Close />
              </button>
            </div>
          </div>

          {/* Quick AI Prompts */}
          <div className="px-4 py-2 border-b border-slate-800/60 bg-slate-950/40 flex items-center space-x-2 overflow-x-auto text-[11px]">
            <button
              onClick={() => handleSendMessage('Which platform is best for booking trains and how do I verify my IRCTC PNR?')}
              className="px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 shrink-0"
            >
              Train platforms & PNRs
            </button>
            <button
              onClick={() => handleSendMessage('Compare IndiGo and MakeMyTrip for Mumbai to Delhi flights')}
              className="px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 shrink-0"
            >
              Compare IndiGo vs MMT
            </button>
            <button
              onClick={() => handleSendMessage('Check capabilities and available booking platforms')}
              className="px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 shrink-0"
            >
              Platforms catalog
            </button>
          </div>

          {/* Chat Messages Log */}
          <div className="flex-1 p-4 overflow-y-auto space-y-4">
            {messages.map((m, idx) => (
              <MessageBubble key={idx} msg={m} />
            ))}

            {chatLoading && (
              <div className="flex items-start space-x-3 my-2">
                <div className="w-7 h-7 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center shrink-0">
                  <Icons.Bot />
                </div>
                <div className="bg-slate-800/80 px-4 py-3 rounded-2xl rounded-tl-none border border-slate-700/50 flex items-center space-x-2 text-xs text-slate-300">
                  <div className="flex space-x-1">
                    <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce"></div>
                    <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                  </div>
                  <span>Agent is searching platforms and comparing rules...</span>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Chat Input Bar */}
          <div className="p-3 border-t border-slate-800 bg-slate-900/90">
            <div className="flex items-center space-x-2">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                placeholder="Ask Co-Pilot for platforms, fares, or PNR checks..."
                className="flex-1 bg-slate-950 border border-slate-700/80 rounded-xl px-3.5 py-2.5 text-xs md:text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
              <button
                onClick={() => handleSendMessage()}
                disabled={chatLoading || !chatInput.trim()}
                className="p-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 text-white transition-all"
              >
                <Icons.Send />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Itinerary Draft / Official Carrier PNR Registration Modal */}
      {registerModalOpen && selectedPlatformForModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl bg-slate-900 border border-slate-800 p-6 space-y-5 shadow-2xl">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-bold text-white">Save Itinerary / Record Carrier PNR</h3>
                <p className="text-xs text-slate-400">Platform: {selectedPlatformForModal.name}</p>
              </div>
              <button
                onClick={() => setRegisterModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <Icons.Close />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Route</label>
                <div className="text-white font-medium bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  {searchParams.origin} ➔ {searchParams.destination} ({searchParams.date})
                </div>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Passenger Name</label>
                <input
                  type="text"
                  value={modalPassengerName}
                  onChange={(e) => setModalPassengerName(e.target.value)}
                  placeholder="e.g. John Doe"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Official Carrier PNR (Optional)</label>
                <input
                  type="text"
                  value={modalOfficialPnr}
                  onChange={(e) => setModalOfficialPnr(e.target.value.toUpperCase())}
                  placeholder="e.g. K9QX2M or 2451890342"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white font-mono"
                />
                <p className="text-[11px] text-slate-500 mt-1">
                  Once you complete checkout on {selectedPlatformForModal.name}, paste your official PNR here for live tracking.
                </p>
              </div>
            </div>

            <div className="flex space-x-2 pt-2">
              <button
                onClick={() => setRegisterModalOpen(false)}
                className="flex-1 py-2.5 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveDraftBooking}
                className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/30"
              >
                Save Itinerary
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

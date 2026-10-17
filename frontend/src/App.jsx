import React, { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import MessageBubble from './components/MessageBubble';
import BookingsDrawer from './components/BookingsDrawer';
import { Icons } from './components/Icons';

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [threadId, setThreadId] = useState('1');
  const [bookingCount, setBookingCount] = useState(0);
  const [bookings, setBookings] = useState([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [serverStatus, setServerStatus] = useState({ online: true, keyConfigured: true });

  const chatEndRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  useEffect(() => {
    fetchStatus();
    fetchBookings();
  }, [threadId]);

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/status');
      if (res.ok) {
        const data = await res.json();
        setServerStatus({
          online: true,
          keyConfigured: data.api_key_configured,
          model: data.model,
        });
        if (data.bookings_count !== undefined) {
          setBookingCount(data.bookings_count);
        }
      }
    } catch (e) {
      console.warn('Backend status check failed:', e);
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
      console.warn('Failed to fetch bookings:', e);
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
          content: `Started a fresh conversation session (Thread ID: ${newId}). MemorySaver checkpointer has been reset for this thread. How can I assist you with your travels or bookings?`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } catch (e) {
      setThreadId(String(Date.now()).slice(-4));
      setMessages([]);
    }
  };

  const handleSendMessage = async (textToSend) => {
    const text = (typeof textToSend === 'string' ? textToSend : input).trim();
    if (!text || loading) return;

    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userMsg = { sender: 'user', content: text, timestamp };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          thread_id: threadId,
        }),
      });

      const data = await res.json();

      if (res.ok && data.success) {
        const agentMsg = {
          sender: 'agent',
          content: data.reply,
          toolsCalled: data.tools_called || [],
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setMessages((prev) => [...prev, agentMsg]);
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
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          sender: 'agent',
          content: `⚠️ Connection failed: Could not reach Python backend server on /api/chat. Please ensure server.py is running.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-[#090D16]">
      {/* Header */}
      <Header
        threadId={threadId}
        onResetThread={handleResetThread}
        onOpenBookings={() => {
          fetchBookings();
          setDrawerOpen(true);
        }}
        bookingCount={bookingCount}
        serverStatus={serverStatus}
      />

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <Sidebar
          threadId={threadId}
          onResetThread={handleResetThread}
          bookingCount={bookingCount}
          onOpenBookings={() => setDrawerOpen(true)}
          onSendPrompt={handleSendMessage}
        />

        {/* Chat Area */}
        <main className="flex-1 flex flex-col h-full overflow-hidden relative">
          <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6 space-y-4">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto text-center space-y-6 my-auto py-12">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-violet-500 flex items-center justify-center glow-indigo animate-pulse-subtle">
                  <Icons.Sparkles />
                </div>

                <div className="space-y-2">
                  <h2 className="font-display font-bold text-2xl md:text-3xl text-white tracking-tight">
                    LangGraph AI Agent
                  </h2>
                  <p className="text-slate-400 text-sm md:text-base max-w-lg mx-auto">
                    Stateful LangGraph workflow equipped with Web Browsing, Multi-Mode Ticket Reservations, and PNR Status Verification.
                  </p>
                </div>

                <div className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300">
                  <Icons.ShieldCheck />
                  <span>API credentials are safely maintained by the backend server</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full text-left pt-4">
                  <button
                    onClick={() => handleSendMessage("Book a flight from New York (JFK) to London (LHR) on 2026-11-20 for Sarah Connor")}
                    className="p-4 rounded-xl glass-card hover:border-indigo-500/40 transition-all hover:scale-[1.01] text-left group"
                  >
                    <div className="text-indigo-400 font-semibold text-xs flex items-center space-x-1.5 mb-1">
                      <Icons.Plane />
                      <span>Flight Reservation</span>
                    </div>
                    <div className="text-xs text-slate-300">
                      "Book a flight from NYC to London on 2026-11-20 for Sarah Connor"
                    </div>
                  </button>

                  <button
                    onClick={() => handleSendMessage("Search train schedules and book 2 tickets from Paris to Lyon for tomorrow for Alice and Bob")}
                    className="p-4 rounded-xl glass-card hover:border-indigo-500/40 transition-all hover:scale-[1.01] text-left group"
                  >
                    <div className="text-sky-400 font-semibold text-xs flex items-center space-x-1.5 mb-1">
                      <Icons.Ticket />
                      <span>Train Booking</span>
                    </div>
                    <div className="text-xs text-slate-300">
                      "Book 2 train tickets from Paris to Lyon for tomorrow for Alice and Bob"
                    </div>
                  </button>

                  <button
                    onClick={() => handleSendMessage("Browse the top travel attractions and guidelines in Tokyo for Autumn 2026")}
                    className="p-4 rounded-xl glass-card hover:border-indigo-500/40 transition-all hover:scale-[1.01] text-left group"
                  >
                    <div className="text-amber-400 font-semibold text-xs flex items-center space-x-1.5 mb-1">
                      <Icons.Search />
                      <span>Live Web Research</span>
                    </div>
                    <div className="text-xs text-slate-300">
                      "Browse the top travel attractions and guidelines in Tokyo for Autumn 2026"
                    </div>
                  </button>

                  <button
                    onClick={() => handleSendMessage("Can you check what ticket skills and categories are supported?")}
                    className="p-4 rounded-xl glass-card hover:border-indigo-500/40 transition-all hover:scale-[1.01] text-left group"
                  >
                    <div className="text-emerald-400 font-semibold text-xs flex items-center space-x-1.5 mb-1">
                      <Icons.Sparkles />
                      <span>Check Capabilities</span>
                    </div>
                    <div className="text-xs text-slate-300">
                      "What ticket skills and categories are supported?"
                    </div>
                  </button>
                </div>
              </div>
            ) : (
              <div className="max-w-3xl mx-auto w-full pb-6">
                {messages.map((m, index) => (
                  <MessageBubble key={index} msg={m} />
                ))}

                {loading && (
                  <div className="flex items-start space-x-3 my-3">
                    <div className="w-8 h-8 rounded-xl bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center shrink-0">
                      <Icons.Bot />
                    </div>
                    <div className="glass-card px-4 py-3 rounded-2xl rounded-tl-none border border-slate-700/50 flex items-center space-x-2 text-xs text-slate-300">
                      <div className="flex space-x-1">
                        <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce"></div>
                        <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                        <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                      </div>
                      <span>LangGraph Agent is reasoning and executing skills...</span>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>
            )}
          </div>

          {/* Chat Input Bar */}
          <div className="p-4 md:px-8 border-t border-slate-800/80 glass-panel shrink-0">
            <div className="max-w-3xl mx-auto relative flex flex-col space-y-2">
              <div className="flex items-center space-x-2">
                <textarea
                  rows="2"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask the agent to browse travel info, book tickets (flights, trains, events), or check status..."
                  className="flex-1 bg-slate-900/90 border border-slate-700/60 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 resize-none transition-all"
                />
                <button
                  onClick={() => handleSendMessage()}
                  disabled={loading || !input.trim()}
                  className={`h-11 px-5 rounded-xl flex items-center justify-center transition-all font-medium text-sm ${
                    loading || !input.trim()
                      ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                      : 'bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white shadow-lg shadow-indigo-600/30 active:scale-95'
                  }`}
                >
                  <Icons.Send />
                </button>
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-500 px-1">
                <span>Press <kbd className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">Enter</kbd> to send, <kbd className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">Shift+Enter</kbd> for newline</span>
                <span className="flex items-center space-x-1">
                  <Icons.ShieldCheck />
                  <span>Backend-Secured Auth</span>
                </span>
              </div>
            </div>
          </div>
        </main>
      </div>

      {/* Bookings Modal Drawer */}
      <BookingsDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        bookings={bookings}
        onInquireBooking={(id) => handleSendMessage(`Please check the status of ticket reservation ${id}`)}
      />
    </div>
  );
}

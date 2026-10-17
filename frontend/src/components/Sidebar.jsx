import React from 'react';
import { Icons } from './Icons';

export default function Sidebar({ threadId, onResetThread, onSendPrompt }) {
  return (
    <aside className="w-72 glass-panel border-r border-slate-800/80 p-5 flex flex-col justify-between hidden md:flex shrink-0">
      <div className="space-y-6">
        {/* New Session Button */}
        <button
          onClick={onResetThread}
          className="w-full flex items-center justify-center space-x-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-medium text-sm transition-all shadow-lg shadow-indigo-600/25 active:scale-[0.98]"
        >
          <Icons.Refresh />
          <span>New Conversation</span>
        </button>

        {/* Active Skills Card */}
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 px-1">
            LangGraph Skills
          </h2>
          <div className="space-y-2">
            <div className="p-2.5 rounded-xl glass-card flex items-start space-x-3">
              <div className="p-1.5 rounded-lg bg-sky-500/10 text-sky-400 border border-sky-500/20 mt-0.5">
                <Icons.Search />
              </div>
              <div>
                <div className="text-xs font-semibold text-slate-200">browse_web</div>
                <div className="text-[11px] text-slate-400 leading-tight mt-0.5">
                  Live travel schedules, real-time queries & web pages
                </div>
              </div>
            </div>

            <div className="p-2.5 rounded-xl glass-card flex items-start space-x-3">
              <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mt-0.5">
                <Icons.Plane />
              </div>
              <div>
                <div className="text-xs font-semibold text-slate-200">book_ticket</div>
                <div className="text-[11px] text-slate-400 leading-tight mt-0.5">
                  Flights, Trains, Buses, Movies & Events booking
                </div>
              </div>
            </div>

            <div className="p-2.5 rounded-xl glass-card flex items-start space-x-3">
              <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 mt-0.5">
                <Icons.Ticket />
              </div>
              <div>
                <div className="text-xs font-semibold text-slate-200">check_ticket_status</div>
                <div className="text-[11px] text-slate-400 leading-tight mt-0.5">
                  Verified reservation & PNR status verification
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2 px-1">
            Suggested Actions
          </h2>
          <div className="space-y-1.5">
            <button
              onClick={() => onSendPrompt("Book a flight from New York (JFK) to London (LHR) on 2026-11-20 for Alex Morgan, Business Class")}
              className="w-full text-left p-2 rounded-lg text-xs text-slate-300 hover:text-white hover:bg-slate-800/60 transition-colors border border-transparent hover:border-slate-700/50 truncate"
            >
              ✈️ Book JFK ➔ LHR Flight
            </button>
            <button
              onClick={() => onSendPrompt("Book 2 train tickets from Paris to Lyon for tomorrow for Sophie Martin and Lucas Bernard")}
              className="w-full text-left p-2 rounded-lg text-xs text-slate-300 hover:text-white hover:bg-slate-800/60 transition-colors border border-transparent hover:border-slate-700/50 truncate"
            >
              🚆 Paris ➔ Lyon Train
            </button>
            <button
              onClick={() => onSendPrompt("Browse real-time travel recommendations for Kyoto in Autumn 2026")}
              className="w-full text-left p-2 rounded-lg text-xs text-slate-300 hover:text-white hover:bg-slate-800/60 transition-colors border border-transparent hover:border-slate-700/50 truncate"
            >
              🌐 Kyoto Autumn Travel Info
            </button>
          </div>
        </div>
      </div>

      {/* Security & Memory Architecture Note */}
      <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 text-[11px] space-y-2">
        <div className="flex items-center space-x-1.5 text-emerald-400 font-medium">
          <Icons.ShieldCheck />
          <span>Zero-Key Client Protection</span>
        </div>
        <p className="text-slate-400 leading-relaxed">
          API credentials are securely kept on the backend server (<code className="text-slate-300">env/.env</code>) and are never requested or stored on the UI.
        </p>
        <div className="pt-1.5 border-t border-slate-800 flex items-center justify-between text-slate-500">
          <span>MemorySaver Checkpointer</span>
          <span className="text-indigo-400 font-mono">thread={threadId}</span>
        </div>
      </div>
    </aside>
  );
}

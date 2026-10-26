import React from 'react';
import { Icons } from './Icons';

export default function Header({ threadId, onResetThread, onOpenBookings, bookingCount, serverStatus }) {
  return (
    <header className="glass-panel border-b border-slate-800/80 px-6 py-3.5 flex items-center justify-between z-20 shrink-0">
      <div className="flex items-center space-x-3.5">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-violet-500 flex items-center justify-center glow-indigo">
          <Icons.Sparkles />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="font-display font-bold text-lg text-white tracking-tight">Manta<span className="text-indigo-400">Booking</span></h1>
            <span className="text-[11px] font-semibold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
              AI Agent
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-violet-500/10 border border-violet-500/30 text-violet-300 hidden sm:inline-block">
              Chain: model | parser
            </span>
            <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-300 hidden md:inline-flex items-center space-x-1">
              <span>✉️ Gmail Itineraries</span>
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 hidden xl:inline-flex items-center space-x-1" title="Read/Write Separation: Primary Master SQLite (WAL) + 2 Read Replicas">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
              <span>DB: Master (W) + 2 Replicas (R)</span>
            </span>
          </div>
          <p className="text-xs text-slate-400 flex items-center space-x-2 mt-0.5">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>Server-Secured Auth</span>
            <span className="text-slate-600">•</span>
            <span>LCEL Chain</span>
            <span className="text-slate-600">•</span>
            <span className="text-cyan-300">Read/Write DB Separation</span>
          </p>
        </div>
      </div>

      <div className="flex items-center space-x-3">
        {/* Thread Info Badge */}
        <div className="hidden sm:flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/60 text-xs text-slate-300">
          <span className="text-slate-500">Thread:</span>
          <span className="font-mono text-indigo-300 font-medium">{threadId}</span>
          <button 
            onClick={onResetThread} 
            title="Start a new thread session"
            className="hover:text-white transition-colors ml-1 p-0.5 rounded hover:bg-slate-700/50"
          >
            <Icons.Refresh />
          </button>
        </div>

        {/* Bookings Drawer Toggle */}
        <button
          onClick={onOpenBookings}
          className="flex items-center space-x-2 px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-emerald-600/20 to-teal-600/20 hover:from-emerald-600/30 hover:to-teal-600/30 border border-emerald-500/30 text-emerald-300 text-xs font-medium transition-all"
        >
          <Icons.Ticket />
          <span>Bookings</span>
          {bookingCount > 0 && (
            <span className="px-1.5 py-0.2 rounded-full bg-emerald-500 text-slate-950 font-bold text-[10px]">
              {bookingCount}
            </span>
          )}
        </button>
      </div>
    </header>
  );
}

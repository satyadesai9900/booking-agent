import React from 'react';
import { Icons } from './Icons';

export default function BookingsDrawer({ isOpen, onClose, bookings, onInquireBooking }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm transition-opacity">
      <div className="w-full max-w-md bg-slate-900 border-l border-slate-800 h-full flex flex-col p-6 shadow-2xl">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center space-x-2">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Icons.Ticket />
            </div>
            <div>
              <h3 className="font-display font-bold text-white text-base">Active Reservations</h3>
              <p className="text-xs text-slate-400">{bookings.length} reservations • Served via Read Replica Pool</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <Icons.Close />
          </button>
        </div>

        {/* Read/Write Architecture Indicator */}
        <div className="mt-3 p-2.5 rounded-lg bg-cyan-950/40 border border-cyan-800/40 text-[11px] text-cyan-300 flex items-center justify-between">
          <div className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
            <span className="font-semibold">Read/Write CQRS Storage</span>
          </div>
          <span className="font-mono text-[10px] text-cyan-400 bg-cyan-900/50 px-1.5 py-0.5 rounded">
            Master SQLite (W) + 2 Replicas (R)
          </span>
        </div>

        <div className="flex-1 overflow-y-auto py-4 space-y-3.5">
          {bookings.length === 0 ? (
            <div className="h-64 flex flex-col items-center justify-center text-center p-6 text-slate-500">
              <div className="w-12 h-12 rounded-full bg-slate-800/80 flex items-center justify-center mb-3">
                <Icons.Ticket />
              </div>
              <p className="text-sm font-medium text-slate-400">No tickets booked yet</p>
              <p className="text-xs text-slate-500 mt-1">
                Ask the agent to book a flight, train, bus, or event to see your itinerary here.
              </p>
            </div>
          ) : (
            bookings.map((b, idx) => (
              <div key={idx} className="p-4 rounded-xl glass-card border border-slate-700/60 space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                    {b.category}
                  </span>
                  <span className="font-mono text-xs font-bold text-emerald-400">
                    {b.booking_id}
                  </span>
                </div>

                <div className="text-sm font-semibold text-white">
                  {b.origin} ➔ {b.destination}
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs text-slate-400">
                  <div>Date: <span className="text-slate-200">{b.date}</span></div>
                  <div>Class: <span className="text-slate-200">{b.ticket_class}</span></div>
                  <div>Platform: <span className="text-indigo-300 font-medium">{b.platform || "Direct"}</span></div>
                  <div>Cost: <span className="text-emerald-400 font-semibold">{b.total_cost_usd}</span></div>
                  {b.official_pnr && (
                    <div className="col-span-2">Official PNR: <span className="font-mono text-emerald-400 font-bold">{b.official_pnr}</span></div>
                  )}
                </div>

                {b.passenger_names && (
                  <div className="text-[11px] text-slate-400 truncate">
                    Names: <span className="text-slate-300">{b.passenger_names.join(", ")}</span>
                  </div>
                )}

                <div className="pt-2 border-t border-slate-800 flex justify-end space-x-2">
                  <button
                    onClick={() => {
                      onInquireBooking(b.booking_id);
                      onClose();
                    }}
                    className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                  >
                    Check Status in Chat ➔
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

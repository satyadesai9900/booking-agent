import React, { useState } from 'react';
import { Icons } from './Icons';

export default function TicketConfirmationCard({ text }) {
  const [copied, setCopied] = useState(false);
  
  // Match booking ID format: FL-XXXX, TR-XXXX, BS-XXXX, MV-XXXX, EV-XXXX, BK-XXXX
  const idMatch = text.match(/Booking ID:\s*([A-Z]{2}-[A-Za-z0-9]+)/i);
  if (!idMatch) return null;

  const bookingId = idMatch[1];
  const categoryMatch = text.match(/Category:\s*([A-Za-z]+)/i);
  const routeMatch = text.match(/Route \/ Event:\s*([^\n\r]+)/i);
  const dateMatch = text.match(/Date:\s*([^\n\r]+)/i);
  const classMatch = text.match(/Class:\s*([^\n\r]+)/i);
  const costMatch = text.match(/Total Cost:\s*(\$[0-9\.]+)/i);

  const copyId = () => {
    navigator.clipboard.writeText(bookingId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-3 rounded-2xl bg-gradient-to-br from-slate-900 to-indigo-950/40 border border-indigo-500/30 p-4 shadow-xl glow-emerald relative overflow-hidden">
      <div className="flex items-center justify-between pb-3 border-b border-indigo-500/20">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 rounded-lg bg-emerald-500/20 text-emerald-400">
            <Icons.Ticket />
          </div>
          <span className="font-display font-bold text-white text-sm tracking-wide">
            Confirmed Ticket Reservation
          </span>
        </div>
        <div className="flex items-center space-x-1.5">
          <span className="font-mono text-xs font-bold text-indigo-300 bg-indigo-500/20 px-2.5 py-1 rounded-md border border-indigo-500/30">
            {bookingId}
          </span>
          <button 
            onClick={copyId} 
            className="p-1.5 text-slate-400 hover:text-white rounded bg-slate-800/80 transition-colors"
            title="Copy Booking ID"
          >
            {copied ? <Icons.Check /> : <Icons.Copy />}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 py-3 text-xs">
        <div>
          <div className="text-[10px] uppercase font-semibold text-slate-400">Category</div>
          <div className="font-semibold text-slate-100">{categoryMatch ? categoryMatch[1] : 'Travel'}</div>
        </div>
        <div>
          <div className="text-[10px] uppercase font-semibold text-slate-400">Date</div>
          <div className="font-semibold text-slate-100">{dateMatch ? dateMatch[1] : 'Confirmed'}</div>
        </div>
        <div>
          <div className="text-[10px] uppercase font-semibold text-slate-400">Class</div>
          <div className="font-semibold text-indigo-300">{classMatch ? classMatch[1] : 'Economy'}</div>
        </div>
        <div>
          <div className="text-[10px] uppercase font-semibold text-slate-400">Total Paid</div>
          <div className="font-bold text-emerald-400 text-sm">{costMatch ? costMatch[1] : '$0.00'}</div>
        </div>
      </div>

      {routeMatch && (
        <div className="pt-2 border-t border-indigo-500/20 flex items-center justify-between text-xs text-slate-300">
          <span className="text-slate-400 font-medium">Route:</span>
          <span className="font-semibold text-white">{routeMatch[1]}</span>
        </div>
      )}
    </div>
  );
}

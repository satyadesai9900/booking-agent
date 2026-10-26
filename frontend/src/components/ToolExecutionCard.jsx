import React, { useState } from 'react';

export default function ToolExecutionCard({ toolEvent }) {
  const [expanded, setExpanded] = useState(false);
  const isPlatform = toolEvent.tool === "get_booking_platforms";
  const isBooking = toolEvent.tool === "book_ticket";
  const isBrowsing = toolEvent.tool === "browse_web";
  const isStatus = toolEvent.tool === "check_ticket_status";
  const isEmail = toolEvent.tool === "send_booking_email" || toolEvent.tool === "send_email";

  const badgeColor = isPlatform
    ? "bg-cyan-500/10 text-cyan-400 border-cyan-500/30"
    : isBooking 
    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
    : isBrowsing 
    ? "bg-sky-500/10 text-sky-400 border-sky-500/30"
    : isEmail
    ? "bg-purple-500/10 text-purple-300 border-purple-500/30"
    : "bg-amber-500/10 text-amber-400 border-amber-500/30";

  return (
    <div className="my-2 rounded-xl border border-slate-800 bg-slate-900/60 p-3 text-xs">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="text-slate-400 font-medium">Executed Tool:</span>
          <span className={`px-2 py-0.5 rounded-md font-mono font-medium border ${badgeColor}`}>
            {toolEvent.tool}
          </span>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-[11px] text-indigo-400 hover:text-indigo-300 transition-colors"
        >
          {expanded ? "Hide Details" : "View Output"}
        </button>
      </div>

      {/* Quick summary of arguments */}
      {toolEvent.args && (
        <div className="mt-2 text-slate-300 font-mono text-[11px] bg-slate-950/70 p-2 rounded-lg overflow-x-auto">
          {isPlatform && (
            <div>
              <span className="text-cyan-400 font-semibold">Platforms for {toolEvent.args.category?.toUpperCase()}: </span>
              {toolEvent.args.origin && toolEvent.args.destination ? `${toolEvent.args.origin} ➔ ${toolEvent.args.destination}` : 'General options'} {toolEvent.args.date ? `(${toolEvent.args.date})` : ''}
            </div>
          )}
          {isBooking && (
            <div>
              <span className="text-emerald-400 font-semibold">{toolEvent.args.category?.toUpperCase()}: </span>
              {toolEvent.args.origin} ➔ {toolEvent.args.destination} ({toolEvent.args.date}) | Platform: {toolEvent.args.platform || 'Selected'} | Class: {toolEvent.args.ticket_class || 'Economy'}
            </div>
          )}
          {isBrowsing && (
            <div>
              <span className="text-sky-400 font-semibold">Query: </span>
              "{toolEvent.args.query}"
            </div>
          )}
          {isStatus && (
            <div>
              <span className="text-amber-400 font-semibold">PNR: </span>
              {toolEvent.args.booking_id}
            </div>
          )}
          {isEmail && (
            <div>
              <span className="text-purple-400 font-semibold">📧 To: </span>
              {toolEvent.args.recipient_email}
              {toolEvent.args.booking_id && (
                <span className="text-slate-400 ml-2">| PNR: <span className="text-indigo-300">{toolEvent.args.booking_id}</span></span>
              )}
              {toolEvent.args.subject && (
                <div className="text-slate-400 text-[10px] mt-0.5 truncate">Subject: {toolEvent.args.subject}</div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Collapsible raw tool output */}
      {expanded && (
        <div className="mt-2.5 pt-2 border-t border-slate-800">
          <div className="text-[10px] uppercase font-semibold text-slate-500 mb-1">Tool Output Payload:</div>
          <pre className="p-2.5 rounded-lg bg-black/50 text-slate-300 text-[11px] font-mono whitespace-pre-wrap overflow-x-auto">
            {toolEvent.output}
          </pre>
        </div>
      )}
    </div>
  );
}

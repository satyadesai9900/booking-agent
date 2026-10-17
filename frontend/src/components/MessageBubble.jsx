import React from 'react';
import { Icons } from './Icons';
import ToolExecutionCard from './ToolExecutionCard';
import TicketConfirmationCard from './TicketConfirmationCard';

export default function MessageBubble({ msg }) {
  const isUser = msg.sender === "user";

  // Formatted text rendering (handles line breaks and paragraphs)
  const renderContent = (content) => {
    if (!content) return null;
    return content.split("\n").map((line, idx) => (
      <p key={idx} className={line.trim() === "" ? "h-2" : "leading-relaxed"}>
        {line}
      </p>
    ));
  };

  return (
    <div className={`flex w-full ${isUser ? "justify-end" : "justify-start"} my-3`}>
      <div className={`flex items-start max-w-[85%] md:max-w-[75%] space-x-3 ${isUser ? "flex-row-reverse space-x-reverse" : ""}`}>
        {/* Avatar */}
        <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
          isUser 
            ? "bg-gradient-to-tr from-slate-700 to-slate-600 shadow" 
            : "bg-gradient-to-tr from-indigo-600 via-indigo-500 to-violet-500 glow-indigo"
        }`}>
          {isUser ? <Icons.User /> : <Icons.Bot />}
        </div>

        {/* Bubble Container */}
        <div className="flex flex-col">
          <div className={`px-4 py-3 rounded-2xl text-sm ${
            isUser
              ? "bg-gradient-to-r from-indigo-600 to-violet-600 text-white rounded-tr-none shadow-lg shadow-indigo-600/10"
              : "glass-card text-slate-200 rounded-tl-none border border-slate-700/50"
          }`}>
            {/* Tool executions if any */}
            {msg.toolsCalled && msg.toolsCalled.length > 0 && (
              <div className="mb-2">
                {msg.toolsCalled.map((toolEvent, i) => (
                  <ToolExecutionCard key={i} toolEvent={toolEvent} />
                ))}
              </div>
            )}

            {/* Main text message */}
            <div className="space-y-1">
              {renderContent(msg.content)}
            </div>

            {/* Visual Boarding pass if booking confirmation text */}
            {!isUser && msg.content && msg.content.includes("Booking ID:") && (
              <TicketConfirmationCard text={msg.content} />
            )}
          </div>

          {/* Timestamp */}
          <span className={`text-[10px] text-slate-500 mt-1 px-1 ${isUser ? "text-right" : "text-left"}`}>
            {msg.timestamp || "Just now"}
          </span>
        </div>
      </div>
    </div>
  );
}

import React from 'react';
import { Icons } from './Icons';
import ToolExecutionCard from './ToolExecutionCard';
import TicketConfirmationCard from './TicketConfirmationCard';

export default function MessageBubble({ msg }) {
  const isUser = msg.sender === "user";

  // Formatted text rendering with clickable links, bolding, blockquotes, and headings
  const parseLine = (text) => {
    if (!text) return null;

    const tokenRegex = /(\[([^\]]+)\]\((https?:\/\/[^\s\)]+)\))|(https?:\/\/[^\s\)]+)|(\*\*([^*]+)\*\*)/g;
    const elements = [];
    let lastIndex = 0;
    let match;

    while ((match = tokenRegex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        elements.push(text.slice(lastIndex, match.index));
      }

      if (match[1]) {
        // [text](url) -> Markdown link
        const linkText = match[2];
        const url = match[3];
        elements.push(
          <a
            key={match.index}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center space-x-1 px-2 py-0.5 mx-0.5 rounded-md bg-indigo-500/20 hover:bg-indigo-500/35 text-indigo-300 hover:text-white border border-indigo-500/40 transition-all font-medium text-xs group cursor-pointer"
          >
            <span>{linkText}</span>
            <svg className="w-3 h-3 text-indigo-400 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        );
      } else if (match[4]) {
        // Bare URL
        const url = match[4];
        elements.push(
          <a
            key={match.index}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center space-x-1 text-indigo-400 hover:text-indigo-300 underline font-medium break-all"
          >
            <span>{url}</span>
            <svg className="w-3 h-3 ml-0.5 inline text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        );
      } else if (match[5]) {
        // **text** -> Bold
        elements.push(
          <strong key={match.index} className="font-semibold text-white">
            {match[6]}
          </strong>
        );
      }

      lastIndex = tokenRegex.lastIndex;
    }

    if (lastIndex < text.length) {
      elements.push(text.slice(lastIndex));
    }

    return elements.length > 0 ? elements : text;
  };

  const renderContent = (content) => {
    if (!content) return null;
    return content.split("\n").map((line, idx) => {
      const trimmed = line.trim();
      if (!trimmed) return <div key={idx} className="h-2" />;

      if (trimmed.startsWith("> ")) {
        return (
          <div key={idx} className="my-1.5 p-2 rounded-lg bg-indigo-500/10 border-l-2 border-indigo-400 text-xs text-indigo-200">
            {parseLine(trimmed.slice(2))}
          </div>
        );
      }

      if (trimmed.startsWith("### ")) {
        return (
          <h4 key={idx} className="font-bold text-white text-sm mt-2 mb-1">
            {parseLine(trimmed.slice(4))}
          </h4>
        );
      }

      return (
        <p key={idx} className="leading-relaxed">
          {parseLine(line)}
        </p>
      );
    });
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

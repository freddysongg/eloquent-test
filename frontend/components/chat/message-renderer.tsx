"use client";

import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { cn } from "@/lib/utils";

interface MessageRendererProps {
  content: string;
  className?: string;
}

interface CodeBlockProps {
  node?: any;
  inline?: boolean;
  className?: string;
  children?: React.ReactNode;
}

export function MessageRenderer({ content, className }: MessageRendererProps) {
  return (
    <div className={cn("prose prose-sm max-w-none", className)}>
      <ReactMarkdown
        components={{
          // Custom code block rendering with syntax highlighting
          code({
            node,
            inline,
            className,
            children,
            ...props
          }: CodeBlockProps) {
            const match = /language-(\w+)/.exec(className || "");
            const language = match ? match[1] : "";

            return !inline && language ? (
              <div className="my-4 overflow-hidden rounded-lg border border-border/50">
                <div className="flex items-center justify-between px-4 py-2 bg-muted/30 border-b border-border/50">
                  <span className="text-xs font-medium text-muted-foreground uppercase">
                    {language}
                  </span>
                </div>
                <SyntaxHighlighter
                  style={vscDarkPlus}
                  language={language}
                  PreTag="div"
                  className="!m-0 !bg-background"
                  customStyle={{
                    margin: 0,
                    padding: "16px",
                    background: "transparent",
                    fontSize: "0.875rem",
                    lineHeight: "1.5",
                  }}
                  {...props}
                >
                  {String(children).replace(/\n$/, "")}
                </SyntaxHighlighter>
              </div>
            ) : (
              <code
                className={cn(
                  "relative rounded px-[0.3rem] py-[0.2rem] font-mono text-sm",
                  "bg-muted/60 text-foreground border border-border/30",
                  className,
                )}
                {...props}
              >
                {children}
              </code>
            );
          },

          // Custom paragraph styling
          p: ({ children }) => (
            <p className="mb-4 last:mb-0 leading-relaxed text-[15px]">
              {children}
            </p>
          ),

          // Custom heading styles
          h1: ({ children }) => (
            <h1 className="text-xl font-semibold mb-4 text-foreground border-b border-border/30 pb-2">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-lg font-semibold mb-3 text-foreground">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-base font-semibold mb-2 text-foreground">
              {children}
            </h3>
          ),

          // Custom list styles
          ul: ({ children }) => (
            <ul className="mb-4 ml-4 space-y-1 list-disc marker:text-muted-foreground">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="mb-4 ml-4 space-y-1 list-decimal marker:text-muted-foreground">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="text-[15px] leading-relaxed">{children}</li>
          ),

          // Custom blockquote styling
          blockquote: ({ children }) => (
            <blockquote className="mb-4 pl-4 border-l-4 border-border/50 italic text-muted-foreground bg-muted/20 py-2 rounded-r-md">
              {children}
            </blockquote>
          ),

          // Custom link styling
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:text-primary/80 underline underline-offset-4 transition-colors"
            >
              {children}
            </a>
          ),

          // Custom strong/bold styling
          strong: ({ children }) => (
            <strong className="font-semibold text-foreground">
              {children}
            </strong>
          ),

          // Custom emphasis/italic styling
          em: ({ children }) => (
            <em className="italic text-muted-foreground">{children}</em>
          ),

          // Custom table styling
          table: ({ children }) => (
            <div className="mb-4 overflow-x-auto">
              <table className="w-full border-collapse border border-border/50 rounded-lg">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border border-border/50 bg-muted/30 px-3 py-2 text-left font-semibold text-sm">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-border/50 px-3 py-2 text-sm">
              {children}
            </td>
          ),

          // Custom horizontal rule
          hr: () => (
            <hr className="my-6 border-0 h-px bg-gradient-to-r from-transparent via-border to-transparent" />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

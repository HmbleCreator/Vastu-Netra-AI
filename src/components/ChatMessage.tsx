import { Message } from '@/hooks/useLocalLLM';
import { User, Bot } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  // Remove JSON code blocks from assistant messages for display
  const displayContent = isUser 
    ? message.content 
    : message.content.replace(/```json\s*[\s\S]*?\s*```/g, '').trim();

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Bot className="h-5 w-5" />
        </div>
      )}
      
      <div
        className={`max-w-[80%] rounded-lg px-4 py-2 transition-smooth ${
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-card border border-border'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap text-sm leading-relaxed">
            {displayContent}
          </p>
        ) : (
          <div className="prose prose-sm max-w-none dark:prose-invert prose-headings:mb-2 prose-headings:mt-3 prose-p:my-1 prose-ul:my-1 prose-ol:my-1">
            <ReactMarkdown>{displayContent}</ReactMarkdown>
          </div>
        )}
      </div>

      {isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-secondary text-secondary-foreground">
          <User className="h-5 w-5" />
        </div>
      )}
    </div>
  );
}

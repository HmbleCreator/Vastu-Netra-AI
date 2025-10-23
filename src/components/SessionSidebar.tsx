import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Plus, MessageSquare, Trash2 } from 'lucide-react';
import { ChatSession } from '@/hooks/useChatSessions';
import { cn } from '@/lib/utils';

interface SessionSidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSessionSelect: (sessionId: string) => void;
  onSessionCreate: () => void;
  onSessionDelete: (sessionId: string) => void;
}

export function SessionSidebar({
  sessions,
  activeSessionId,
  onSessionSelect,
  onSessionCreate,
  onSessionDelete,
}: SessionSidebarProps) {
  const sortedSessions = [...sessions].sort((a, b) => b.updatedAt - a.updatedAt);

  return (
    <div className="flex h-full flex-col border-r border-border bg-card/50">
      <div className="border-b border-border p-4">
        <Button onClick={onSessionCreate} className="w-full" size="sm">
          <Plus className="mr-2 h-4 w-4" />
          New Chat
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-1 p-2">
          {sortedSessions.map((session) => (
            <div
              key={session.id}
              className={cn(
                "group flex items-center gap-2 rounded-lg px-3 py-2 text-sm cursor-pointer transition-colors",
                session.id === activeSessionId
                  ? "bg-primary/10 text-primary"
                  : "hover:bg-muted text-muted-foreground hover:text-foreground"
              )}
              onClick={() => onSessionSelect(session.id)}
            >
              <MessageSquare className="h-4 w-4 shrink-0" />
              <div className="flex-1 truncate">
                <p className="truncate font-medium">{session.title}</p>
                <p className="text-xs opacity-70">
                  {session.messages.length} messages
                </p>
              </div>
              {sessions.length > 1 && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 opacity-0 group-hover:opacity-100"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSessionDelete(session.id);
                  }}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              )}
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}

import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Plus, MessageSquare, Trash2, PanelLeftClose, PanelLeft } from 'lucide-react';
import { ChatSession } from '@/hooks/useChatSessions';
import { cn } from '@/lib/utils';

interface SessionSidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSessionSelect: (sessionId: string) => void;
  onSessionCreate: () => void;
  onSessionDelete: (sessionId: string) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export function SessionSidebar({
  sessions,
  activeSessionId,
  onSessionSelect,
  onSessionCreate,
  onSessionDelete,
  collapsed,
  onToggleCollapse,
}: SessionSidebarProps) {
  const sortedSessions = [...sessions].sort((a, b) => b.updatedAt - a.updatedAt);

  if (collapsed) {
    return (
      <div className="flex h-full w-12 flex-col border-r border-border bg-card/50">
        <div className="border-b border-border p-2">
          <Button
            onClick={onToggleCollapse}
            variant="ghost"
            size="icon"
            className="h-8 w-8"
          >
            <PanelLeft className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex-1 space-y-2 p-2">
          <Button
            onClick={onSessionCreate}
            variant="ghost"
            size="icon"
            className="h-8 w-8"
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col border-r border-border bg-card/50 w-64 animate-slide-in-right">
      <div className="border-b border-border p-4 space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">Chat Sessions</h2>
          <Button
            onClick={onToggleCollapse}
            variant="ghost"
            size="icon"
            className="h-6 w-6"
          >
            <PanelLeftClose className="h-4 w-4" />
          </Button>
        </div>
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

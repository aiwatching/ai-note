import React from 'react';
import { useNavigate } from 'react-router-dom';
import { format, isToday, isYesterday, isThisWeek, isThisMonth } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { FileText, Calendar, Tag, Loader2 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { Note } from '@/types';

interface NoteTimelineProps {
  notes: Note[];
  isLoading: boolean;
}

interface GroupedNotes {
  label: string;
  notes: Note[];
}

function groupNotesByDate(notes: Note[]): GroupedNotes[] {
  const groups: { [key: string]: Note[] } = {};
  const sortedNotes = [...notes].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  sortedNotes.forEach((note) => {
    const date = new Date(note.created_at);
    let label: string;

    if (isToday(date)) {
      label = '今天';
    } else if (isYesterday(date)) {
      label = '昨天';
    } else if (isThisWeek(date)) {
      label = '本周';
    } else if (isThisMonth(date)) {
      label = '本月';
    } else {
      label = format(date, 'yyyy年MM月', { locale: zhCN });
    }

    if (!groups[label]) {
      groups[label] = [];
    }
    groups[label].push(note);
  });

  // Convert to array maintaining order
  const order = ['今天', '昨天', '本周', '本月'];
  const result: GroupedNotes[] = [];

  order.forEach((label) => {
    if (groups[label]) {
      result.push({ label, notes: groups[label] });
      delete groups[label];
    }
  });

  // Add remaining month groups in reverse chronological order
  Object.keys(groups)
    .sort()
    .reverse()
    .forEach((label) => {
      result.push({ label, notes: groups[label] });
    });

  return result;
}

export function NoteTimeline({ notes, isLoading }: NoteTimelineProps) {
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (notes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
        <FileText className="h-16 w-16 mb-4 opacity-30" />
        <p className="text-lg font-medium">暂无笔记</p>
        <p className="text-sm mt-1">开始记录你的第一条笔记吧</p>
      </div>
    );
  }

  const groupedNotes = groupNotesByDate(notes);

  return (
    <div className="space-y-8">
      {groupedNotes.map((group) => (
        <div key={group.label}>
          {/* Date Label */}
          <div className="flex items-center gap-3 mb-4">
            <div className="h-3 w-3 rounded-full bg-primary" />
            <h2 className="text-lg font-semibold text-foreground">{group.label}</h2>
            <div className="flex-1 h-px bg-border" />
            <span className="text-sm text-muted-foreground">{group.notes.length} 条</span>
          </div>

          {/* Notes */}
          <div className="ml-1.5 border-l-2 border-border pl-6 space-y-4">
            {group.notes.map((note) => (
              <TimelineItem key={note.id} note={note} onClick={() => navigate(`/notes/${note.id}`)} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

interface TimelineItemProps {
  note: Note;
  onClick: () => void;
}

function TimelineItem({ note, onClick }: TimelineItemProps) {
  const date = new Date(note.created_at);

  return (
    <div className="relative">
      {/* Timeline dot */}
      <div className="absolute -left-[29px] top-3 h-2 w-2 rounded-full bg-muted-foreground/50" />

      <Card
        className="p-4 cursor-pointer hover:bg-muted/50 transition-colors"
        onClick={onClick}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            {/* Title and Time */}
            <div className="flex items-center gap-2">
              <h3 className="font-medium truncate">{note.title || '无标题笔记'}</h3>
              <span className="text-xs text-muted-foreground flex-shrink-0">
                {format(date, 'HH:mm', { locale: zhCN })}
              </span>
            </div>

            {/* Summary */}
            {note.summary && (
              <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                {note.summary}
              </p>
            )}

            {/* Tags and Category */}
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              {note.category && (
                <Badge variant="secondary" className="text-xs">
                  {note.category}
                </Badge>
              )}
              {note.tags?.slice(0, 3).map((tag) => (
                <Badge key={tag} variant="outline" className="text-xs">
                  {tag}
                </Badge>
              ))}
              {(note.tags?.length || 0) > 3 && (
                <span className="text-xs text-muted-foreground">
                  +{note.tags!.length - 3}
                </span>
              )}
            </div>

            {/* Indicators */}
            <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
              {note.is_todo && (
                <span className="flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-yellow-500" />
                  包含待办
                </span>
              )}
              {note.is_schedule && (
                <span className="flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  包含日程
                </span>
              )}
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}

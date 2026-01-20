import React from 'react';
import { Link } from 'react-router-dom';
import { FileText, Clock, Tag, AlertCircle } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { Note } from '@/types';
import { formatRelativeDate } from '@/utils/date';
import { cn } from '@/utils/cn';

interface NoteListProps {
  notes: Note[];
  isLoading?: boolean;
}

export function NoteList({ notes, isLoading }: NoteListProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (notes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
        <FileText className="h-12 w-12 mb-4" />
        <p>No notes yet</p>
        <p className="text-sm">Start by creating a new note</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {notes.map((note) => (
        <NoteCard key={note.id} note={note} />
      ))}
    </div>
  );
}

function NoteCard({ note }: { note: Note }) {
  const priorityVariant = note.priority as 'high' | 'medium' | 'low' | undefined;

  return (
    <Link to={`/notes/${note.id}`}>
      <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
        <CardContent className="p-4">
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <h3 className="font-medium truncate">
                {note.title || 'Untitled Note'}
              </h3>
              {note.summary && (
                <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                  {note.summary}
                </p>
              )}
              <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {formatRelativeDate(note.created_at)}
                </span>
                {note.category && (
                  <Badge variant="secondary" className="text-xs">
                    {note.category}
                  </Badge>
                )}
              </div>
            </div>
            <div className="flex flex-col items-end gap-2 ml-4">
              {priorityVariant && (
                <Badge variant={priorityVariant} className="capitalize">
                  {note.priority}
                </Badge>
              )}
              <div className="flex gap-1">
                {note.is_todo && (
                  <Badge variant="outline" className="text-xs">
                    Todo
                  </Badge>
                )}
                {note.is_schedule && (
                  <Badge variant="outline" className="text-xs">
                    Schedule
                  </Badge>
                )}
              </div>
            </div>
          </div>
          {note.tags && note.tags.length > 0 && (
            <div className="flex items-center gap-1 mt-3 flex-wrap">
              <Tag className="h-3 w-3 text-muted-foreground" />
              {note.tags.slice(0, 5).map((tag) => (
                <Badge key={tag} variant="outline" className="text-xs">
                  {tag}
                </Badge>
              ))}
              {note.tags.length > 5 && (
                <span className="text-xs text-muted-foreground">
                  +{note.tags.length - 5} more
                </span>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}

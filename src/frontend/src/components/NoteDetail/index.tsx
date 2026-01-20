import React from 'react';
import MDEditor from '@uiw/react-md-editor';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  ArrowLeft,
  Calendar,
  Clock,
  Tag,
  User,
  Trash2,
  Edit,
  ListTodo,
} from 'lucide-react';
import type { NoteDetail as NoteDetailType } from '@/types';
import { formatDate } from '@/utils/date';

interface NoteDetailProps {
  note: NoteDetailType;
  onBack: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onCreateTodos: () => void;
  isLoading?: boolean;
}

export function NoteDetail({
  note,
  onBack,
  onEdit,
  onDelete,
  onCreateTodos,
  isLoading,
}: NoteDetailProps) {
  const priorityVariant = note.priority as 'high' | 'medium' | 'low' | undefined;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={onBack}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-xl font-semibold">
              {note.title || 'Untitled Note'}
            </h1>
            <p className="text-sm text-muted-foreground">
              <Clock className="h-3 w-3 inline mr-1" />
              {formatDate(note.created_at)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {note.is_todo && (
            <Button variant="outline" size="sm" onClick={onCreateTodos}>
              <ListTodo className="h-4 w-4 mr-2" />
              Extract Todos
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={onEdit}>
            <Edit className="h-4 w-4 mr-2" />
            Edit
          </Button>
          <Button variant="destructive" size="sm" onClick={onDelete}>
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Metadata */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Note Information</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 text-sm">
                {note.category && (
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">Category:</span>
                    <Badge variant="secondary">{note.category}</Badge>
                  </div>
                )}
                {priorityVariant && (
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">Priority:</span>
                    <Badge variant={priorityVariant} className="capitalize">
                      {note.priority}
                    </Badge>
                  </div>
                )}
                {note.related_persons && note.related_persons.length > 0 && (
                  <div className="flex items-center gap-2">
                    <User className="h-4 w-4 text-muted-foreground" />
                    <span>{note.related_persons.join(', ')}</span>
                  </div>
                )}
                {note.related_dates && note.related_dates.length > 0 && (
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <span>{note.related_dates.join(', ')}</span>
                  </div>
                )}
              </div>
              {note.tags && note.tags.length > 0 && (
                <div className="flex items-center gap-2 mt-4">
                  <Tag className="h-4 w-4 text-muted-foreground" />
                  {note.tags.map((tag) => (
                    <Badge key={tag} variant="outline">
                      {tag}
                    </Badge>
                  ))}
                </div>
              )}
              {note.summary && (
                <div className="mt-4 p-3 bg-muted rounded-md">
                  <p className="text-sm font-medium mb-1">Summary</p>
                  <p className="text-sm text-muted-foreground">{note.summary}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Content */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Content</CardTitle>
            </CardHeader>
            <CardContent>
              <div data-color-mode="light">
                <MDEditor.Markdown source={note.raw_content} />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

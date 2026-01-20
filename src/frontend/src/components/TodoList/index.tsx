import React from 'react';
import {
  CheckCircle2,
  Circle,
  Clock,
  MoreVertical,
  Trash2,
  Calendar,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import type { Todo } from '@/types';
import { formatSimpleDate } from '@/utils/date';
import { cn } from '@/utils/cn';

interface TodoListProps {
  todos: Todo[];
  onToggle: (id: number, currentStatus: string) => void;
  onDelete: (id: number) => void;
  isLoading?: boolean;
}

export function TodoList({
  todos,
  onToggle,
  onDelete,
  isLoading,
}: TodoListProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (todos.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
        <CheckCircle2 className="h-12 w-12 mb-4" />
        <p>No todos yet</p>
        <p className="text-sm">Create todos from your notes</p>
      </div>
    );
  }

  // Group todos by status
  const pending = todos.filter((t) => t.status === 'pending' || t.status === 'in_progress');
  const completed = todos.filter((t) => t.status === 'completed');

  return (
    <div className="space-y-6">
      {/* Pending */}
      {pending.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-muted-foreground mb-3">
            Pending ({pending.length})
          </h3>
          <div className="space-y-2">
            {pending.map((todo) => (
              <TodoItem
                key={todo.id}
                todo={todo}
                onToggle={onToggle}
                onDelete={onDelete}
              />
            ))}
          </div>
        </div>
      )}

      {/* Completed */}
      {completed.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-muted-foreground mb-3">
            Completed ({completed.length})
          </h3>
          <div className="space-y-2">
            {completed.map((todo) => (
              <TodoItem
                key={todo.id}
                todo={todo}
                onToggle={onToggle}
                onDelete={onDelete}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

interface TodoItemProps {
  todo: Todo;
  onToggle: (id: number, currentStatus: string) => void;
  onDelete: (id: number) => void;
}

function TodoItem({ todo, onToggle, onDelete }: TodoItemProps) {
  const isCompleted = todo.status === 'completed';
  const priorityVariant = todo.priority as 'high' | 'medium' | 'low';

  const isOverdue =
    todo.due_date &&
    !isCompleted &&
    new Date(todo.due_date) < new Date(new Date().toDateString());

  return (
    <Card
      className={cn(
        'transition-colors',
        isCompleted && 'opacity-60'
      )}
    >
      <CardContent className="p-3 flex items-start gap-3">
        <button
          className="mt-0.5 text-muted-foreground hover:text-primary transition-colors"
          onClick={() => onToggle(todo.id, todo.status)}
        >
          {isCompleted ? (
            <CheckCircle2 className="h-5 w-5 text-green-600" />
          ) : (
            <Circle className="h-5 w-5" />
          )}
        </button>

        <div className="flex-1 min-w-0">
          <p
            className={cn(
              'font-medium',
              isCompleted && 'line-through text-muted-foreground'
            )}
          >
            {todo.title}
          </p>
          {todo.description && (
            <p className="text-sm text-muted-foreground mt-1">
              {todo.description}
            </p>
          )}
          <div className="flex items-center gap-3 mt-2">
            <Badge variant={priorityVariant} className="capitalize text-xs">
              {todo.priority}
            </Badge>
            {todo.due_date && (
              <span
                className={cn(
                  'text-xs flex items-center gap-1',
                  isOverdue ? 'text-destructive' : 'text-muted-foreground'
                )}
              >
                <Calendar className="h-3 w-3" />
                {formatSimpleDate(todo.due_date)}
                {isOverdue && ' (Overdue)'}
              </span>
            )}
          </div>
        </div>

        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-muted-foreground hover:text-destructive"
          onClick={() => onDelete(todo.id)}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </CardContent>
    </Card>
  );
}

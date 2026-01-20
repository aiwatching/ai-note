import React, { useEffect, useState, useCallback } from 'react';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { TodoList } from '@/components/TodoList';
import { useTodoStore } from '@/store/todoStore';

export function TodoPage() {
  const [newTodoTitle, setNewTodoTitle] = useState('');
  const [filter, setFilter] = useState<string | null>(null);

  const {
    todos,
    isLoading,
    fetchTodos,
    createTodo,
    updateTodoStatus,
    deleteTodo,
  } = useTodoStore();

  useEffect(() => {
    fetchTodos({ status: filter || undefined });
  }, [fetchTodos, filter]);

  const handleCreateTodo = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!newTodoTitle.trim()) return;

      try {
        await createTodo({ title: newTodoTitle.trim() });
        setNewTodoTitle('');
      } catch (error) {
        console.error('Failed to create todo:', error);
      }
    },
    [newTodoTitle, createTodo]
  );

  const handleToggle = useCallback(
    async (id: number, currentStatus: string) => {
      const newStatus = currentStatus === 'completed' ? 'pending' : 'completed';
      await updateTodoStatus(id, newStatus);
    },
    [updateTodoStatus]
  );

  const handleDelete = useCallback(
    async (id: number) => {
      if (confirm('Are you sure you want to delete this todo?')) {
        await deleteTodo(id);
      }
    },
    [deleteTodo]
  );

  const filteredTodos = filter
    ? todos.filter((t) => t.status === filter)
    : todos;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b">
        <h1 className="text-2xl font-bold">Todos</h1>
        <p className="text-muted-foreground">
          {todos.filter((t) => t.status !== 'completed').length} pending tasks
        </p>
      </div>

      {/* Create Todo */}
      <form onSubmit={handleCreateTodo} className="p-4 border-b flex gap-2">
        <Input
          type="text"
          value={newTodoTitle}
          onChange={(e) => setNewTodoTitle(e.target.value)}
          placeholder="Add a new todo..."
          className="flex-1"
        />
        <Button type="submit" disabled={!newTodoTitle.trim()}>
          <Plus className="h-4 w-4 mr-2" />
          Add
        </Button>
      </form>

      {/* Filters */}
      <div className="p-4 border-b flex items-center gap-2">
        <Button
          variant={filter === null ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter(null)}
        >
          All
        </Button>
        <Button
          variant={filter === 'pending' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('pending')}
        >
          Pending
        </Button>
        <Button
          variant={filter === 'completed' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('completed')}
        >
          Completed
        </Button>
      </div>

      {/* Todo List */}
      <div className="flex-1 overflow-auto p-4">
        <TodoList
          todos={filteredTodos}
          onToggle={handleToggle}
          onDelete={handleDelete}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
}

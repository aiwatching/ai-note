import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Plus, Filter } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { NoteList } from '@/components/NoteList';
import { NoteDetail } from '@/components/NoteDetail';
import { useNoteStore } from '@/store/noteStore';
import { useTodoStore } from '@/store/todoStore';
import { CATEGORIES } from '@/types';

export function NotesPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const {
    notes,
    currentNote,
    isLoading,
    fetchNotes,
    fetchNote,
    deleteNote,
    setCurrentNote,
  } = useNoteStore();

  const { createTodosFromNote } = useTodoStore();

  useEffect(() => {
    fetchNotes({ category: selectedCategory || undefined });
  }, [fetchNotes, selectedCategory]);

  useEffect(() => {
    if (id) {
      fetchNote(parseInt(id, 10));
    } else {
      setCurrentNote(null);
    }
  }, [id, fetchNote, setCurrentNote]);

  const handleBack = () => {
    navigate('/notes');
  };

  const handleEdit = () => {
    // For MVP, we'll navigate to home with content
    navigate('/');
  };

  const handleDelete = async () => {
    if (currentNote && confirm('Are you sure you want to delete this note?')) {
      await deleteNote(currentNote.id);
      navigate('/notes');
    }
  };

  const handleCreateTodos = async () => {
    if (currentNote) {
      try {
        const todos = await createTodosFromNote(currentNote.id);
        alert(`Created ${todos.length} todos from this note!`);
      } catch (error) {
        console.error('Failed to create todos:', error);
      }
    }
  };

  // Show note detail if id is provided
  if (id && currentNote) {
    return (
      <NoteDetail
        note={currentNote}
        onBack={handleBack}
        onEdit={handleEdit}
        onDelete={handleDelete}
        onCreateTodos={handleCreateTodos}
        isLoading={isLoading}
      />
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Notes</h1>
          <p className="text-muted-foreground">
            {notes.length} notes
          </p>
        </div>
        <Button onClick={() => navigate('/')}>
          <Plus className="h-4 w-4 mr-2" />
          New Note
        </Button>
      </div>

      {/* Filters */}
      <div className="p-4 border-b flex items-center gap-2 overflow-x-auto">
        <Filter className="h-4 w-4 text-muted-foreground flex-shrink-0" />
        <Button
          variant={selectedCategory === null ? 'default' : 'outline'}
          size="sm"
          onClick={() => setSelectedCategory(null)}
        >
          All
        </Button>
        {CATEGORIES.map((category) => (
          <Button
            key={category}
            variant={selectedCategory === category ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSelectedCategory(category)}
          >
            {category}
          </Button>
        ))}
      </div>

      {/* Note List */}
      <div className="flex-1 overflow-auto p-4">
        <NoteList notes={notes} isLoading={isLoading} />
      </div>
    </div>
  );
}

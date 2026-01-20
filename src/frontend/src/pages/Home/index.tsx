import React, { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { NoteEditor } from '@/components/NoteEditor';
import { useNoteStore } from '@/store/noteStore';

export function HomePage() {
  const navigate = useNavigate();
  const { createNote, isLoading } = useNoteStore();

  const handleSave = useCallback(
    async (content: string) => {
      try {
        const note = await createNote({ content });
        // Navigate to the created note
        navigate(`/notes/${note.id}`);
      } catch (error) {
        console.error('Failed to create note:', error);
      }
    },
    [createNote, navigate]
  );

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b">
        <h1 className="text-2xl font-bold">Quick Note</h1>
        <p className="text-muted-foreground">
          Write anything and AI will help you organize it
        </p>
      </div>
      <div className="flex-1 min-h-0">
        <NoteEditor onSave={handleSave} isLoading={isLoading} />
      </div>
    </div>
  );
}

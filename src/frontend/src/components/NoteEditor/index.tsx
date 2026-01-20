import React, { useState, useCallback } from 'react';
import MDEditor from '@uiw/react-md-editor';
import { Button } from '@/components/ui/button';
import { Loader2, Save } from 'lucide-react';

interface NoteEditorProps {
  initialContent?: string;
  onSave: (content: string) => Promise<void>;
  isLoading?: boolean;
  placeholder?: string;
}

export function NoteEditor({
  initialContent = '',
  onSave,
  isLoading = false,
  placeholder = 'Start writing your note here...\n\nYou can use Markdown formatting:\n- **Bold** text\n- *Italic* text\n- `code` snippets\n- Lists and more',
}: NoteEditorProps) {
  const [content, setContent] = useState(initialContent);
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = useCallback(async () => {
    if (!content.trim() || isSaving) return;

    setIsSaving(true);
    try {
      await onSave(content);
      setContent(''); // Clear after successful save
    } catch (error) {
      console.error('Failed to save note:', error);
    } finally {
      setIsSaving(false);
    }
  }, [content, onSave, isSaving]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      // Cmd/Ctrl + S to save
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        handleSave();
      }
    },
    [handleSave]
  );

  return (
    <div className="flex flex-col h-full" onKeyDown={handleKeyDown}>
      <div className="flex-1 min-h-0" data-color-mode="light">
        <MDEditor
          value={content}
          onChange={(val) => setContent(val || '')}
          height="100%"
          preview="edit"
          textareaProps={{
            placeholder,
          }}
        />
      </div>
      <div className="flex items-center justify-between p-4 border-t bg-muted/30">
        <div className="text-sm text-muted-foreground">
          {content.length} characters
          <span className="ml-4">Press Cmd+S to save</span>
        </div>
        <Button
          onClick={handleSave}
          disabled={!content.trim() || isSaving || isLoading}
        >
          {isSaving || isLoading ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Save className="h-4 w-4 mr-2" />
          )}
          Save Note
        </Button>
      </div>
    </div>
  );
}

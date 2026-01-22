import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Plus, Filter, Clock, LayoutList, CheckSquare, Calendar, Layers } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { NoteList } from '@/components/NoteList';
import { NoteDetail } from '@/components/NoteDetail';
import { NoteTimeline } from '@/components/NoteTimeline';
import { NoteGroupedList } from '@/components/NoteGroupedList';
import { TodoList } from '@/components/TodoList';
import { ScheduleList } from '@/components/ScheduleList';
import { useNoteStore } from '@/store/noteStore';
import { useTodoStore } from '@/store/todoStore';
import { useScheduleStore } from '@/store/scheduleStore';
import { CATEGORIES } from '@/types';

type TabMode = 'notes' | 'todos' | 'schedules';
type NoteViewMode = 'timeline' | 'list' | 'grouped';

export function NotesPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [tabMode, setTabMode] = useState<TabMode>('notes');
  const [noteViewMode, setNoteViewMode] = useState<NoteViewMode>('grouped');

  const {
    notes,
    noteGroups,
    currentNote,
    isLoading: notesLoading,
    fetchNotes,
    fetchNotesGrouped,
    fetchNote,
    deleteNote,
    setCurrentNote,
  } = useNoteStore();

  const {
    todos,
    isLoading: todosLoading,
    fetchTodos,
    updateTodoStatus,
    deleteTodo,
    createTodosFromNote,
  } = useTodoStore();

  const {
    schedules,
    isLoading: schedulesLoading,
    fetchSchedules,
    updateScheduleStatus,
    deleteSchedule,
  } = useScheduleStore();

  useEffect(() => {
    if (tabMode === 'notes') {
      if (noteViewMode === 'grouped') {
        fetchNotesGrouped({ category: selectedCategory || undefined });
      } else {
        fetchNotes({ category: selectedCategory || undefined });
      }
    } else if (tabMode === 'todos') {
      fetchTodos();
    } else if (tabMode === 'schedules') {
      fetchSchedules();
    }
  }, [tabMode, noteViewMode, fetchNotes, fetchNotesGrouped, fetchTodos, fetchSchedules, selectedCategory]);

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
    // 传递 note id 到 Home 页面进行编辑
    if (currentNote) {
      navigate('/', { state: { editNoteId: currentNote.id } });
    } else {
      navigate('/');
    }
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
        const newTodos = await createTodosFromNote(currentNote.id);
        alert(`Created ${newTodos.length} todos from this note!`);
      } catch (error) {
        console.error('Failed to create todos:', error);
      }
    }
  };

  const handleTodoToggle = async (id: number, currentStatus: string) => {
    const newStatus = currentStatus === 'completed' ? 'pending' : 'completed';
    await updateTodoStatus(id, newStatus);
  };

  const handleTodoDelete = async (id: number) => {
    if (confirm('确定要删除这个待办事项吗？')) {
      await deleteTodo(id);
    }
  };

  const handleScheduleStatusChange = async (id: number, status: string) => {
    await updateScheduleStatus(id, status);
  };

  const handleScheduleDelete = async (id: number) => {
    if (confirm('确定要删除这个日程吗？')) {
      await deleteSchedule(id);
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
        isLoading={notesLoading}
      />
    );
  }

  const getTabTitle = () => {
    switch (tabMode) {
      case 'notes':
        return { title: '笔记', count: notes.length };
      case 'todos':
        return { title: '待办', count: todos.length };
      case 'schedules':
        return { title: '日程', count: schedules.length };
    }
  };

  const { title, count } = getTabTitle();

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{title}</h1>
          <p className="text-muted-foreground">
            {count} 条记录
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Note View Mode Toggle (only show for notes tab) */}
          {tabMode === 'notes' && (
            <div className="flex items-center border rounded-md">
              <Button
                variant={noteViewMode === 'grouped' ? 'default' : 'ghost'}
                size="sm"
                className="rounded-r-none"
                onClick={() => setNoteViewMode('grouped')}
                title="按主题分组"
              >
                <Layers className="h-4 w-4 mr-1" />
                分组
              </Button>
              <Button
                variant={noteViewMode === 'timeline' ? 'default' : 'ghost'}
                size="sm"
                className="rounded-none border-l"
                onClick={() => setNoteViewMode('timeline')}
                title="时间轴视图"
              >
                <Clock className="h-4 w-4 mr-1" />
                时间轴
              </Button>
              <Button
                variant={noteViewMode === 'list' ? 'default' : 'ghost'}
                size="sm"
                className="rounded-l-none border-l"
                onClick={() => setNoteViewMode('list')}
                title="列表视图"
              >
                <LayoutList className="h-4 w-4 mr-1" />
                列表
              </Button>
            </div>
          )}
          <Button onClick={() => navigate('/')}>
            <Plus className="h-4 w-4 mr-2" />
            新记录
          </Button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="p-4 border-b flex items-center gap-2">
        <Button
          variant={tabMode === 'notes' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setTabMode('notes')}
        >
          <LayoutList className="h-4 w-4 mr-1" />
          笔记
        </Button>
        <Button
          variant={tabMode === 'todos' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setTabMode('todos')}
        >
          <CheckSquare className="h-4 w-4 mr-1" />
          待办
        </Button>
        <Button
          variant={tabMode === 'schedules' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setTabMode('schedules')}
        >
          <Calendar className="h-4 w-4 mr-1" />
          日程
        </Button>
      </div>

      {/* Category Filters (only show for notes tab) */}
      {tabMode === 'notes' && (
        <div className="p-4 border-b flex items-center gap-2 overflow-x-auto">
          <Filter className="h-4 w-4 text-muted-foreground flex-shrink-0" />
          <Button
            variant={selectedCategory === null ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSelectedCategory(null)}
          >
            全部
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
      )}

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {tabMode === 'notes' && (
          noteViewMode === 'grouped' ? (
            <NoteGroupedList groups={noteGroups} isLoading={notesLoading} />
          ) : noteViewMode === 'timeline' ? (
            <NoteTimeline notes={notes} isLoading={notesLoading} />
          ) : (
            <NoteList notes={notes} isLoading={notesLoading} />
          )
        )}

        {tabMode === 'todos' && (
          <TodoList
            todos={todos}
            onToggle={handleTodoToggle}
            onDelete={handleTodoDelete}
            isLoading={todosLoading}
          />
        )}

        {tabMode === 'schedules' && (
          <ScheduleList
            schedules={schedules}
            onStatusChange={handleScheduleStatusChange}
            onDelete={handleScheduleDelete}
            isLoading={schedulesLoading}
          />
        )}
      </div>
    </div>
  );
}

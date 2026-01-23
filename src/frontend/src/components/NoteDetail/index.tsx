import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
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
  Link2,
  Check,
  Loader2,
  MessageSquare,
  ExternalLink,
} from 'lucide-react';
import type { NoteDetail as NoteDetailType } from '@/types';
import { formatDate } from '@/utils/date';
import { noteService } from '@/services/noteService';
import { chatService, ChatSessionOut } from '@/services/chatService';

interface Suggestion {
  note_id: number;
  title: string;
  category: string | null;
  summary: string | null;
  created_at: string;
  similarity: number;
  is_linked: boolean;
}

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
  const navigate = useNavigate();
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [linkingId, setLinkingId] = useState<number | null>(null);
  const [linkedChats, setLinkedChats] = useState<ChatSessionOut[]>([]);
  const [loadingChats, setLoadingChats] = useState(false);

  const priorityVariant = note.priority as 'high' | 'medium' | 'low' | undefined;

  // Load suggested relations
  useEffect(() => {
    async function loadSuggestions() {
      setLoadingSuggestions(true);
      try {
        const result = await noteService.getSuggestedRelations(note.id, 0.15);
        setSuggestions(result.suggestions);
      } catch (error) {
        console.error('Failed to load suggestions:', error);
      } finally {
        setLoadingSuggestions(false);
      }
    }
    loadSuggestions();
  }, [note.id]);

  // Load linked chat sessions
  useEffect(() => {
    async function loadLinkedChats() {
      setLoadingChats(true);
      try {
        const sessions = await chatService.getSessionsByNote(note.id);
        setLinkedChats(sessions);
      } catch (error) {
        console.error('Failed to load linked chats:', error);
      } finally {
        setLoadingChats(false);
      }
    }
    loadLinkedChats();
  }, [note.id]);

  // Handle linking a note
  const handleLink = async (targetId: number) => {
    setLinkingId(targetId);
    try {
      await noteService.createManualRelation(note.id, targetId);
      // Update local state
      setSuggestions(prev =>
        prev.map(s => s.note_id === targetId ? { ...s, is_linked: true } : s)
      );
    } catch (error) {
      console.error('Failed to link note:', error);
    } finally {
      setLinkingId(null);
    }
  };

  // Handle unlinking a note
  const handleUnlink = async (targetId: number) => {
    setLinkingId(targetId);
    try {
      await noteService.deleteRelation(note.id, targetId);
      // Update local state
      setSuggestions(prev =>
        prev.map(s => s.note_id === targetId ? { ...s, is_linked: false } : s)
      );
    } catch (error) {
      console.error('Failed to unlink note:', error);
    } finally {
      setLinkingId(null);
    }
  };

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

          {/* Linked Chat Sessions */}
          {(linkedChats.length > 0 || loadingChats) && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" />
                  关联的 AI 对话
                  {linkedChats.length > 0 && (
                    <Badge variant="secondary" className="text-xs">
                      {linkedChats.length} 个对话
                    </Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {loadingChats ? (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    加载中...
                  </div>
                ) : (
                  <div className="space-y-2">
                    {linkedChats.map((chat) => (
                      <div
                        key={chat.id}
                        className="flex items-center justify-between p-3 rounded-md border hover:bg-muted/50 cursor-pointer"
                        onClick={() => navigate(`/chat?session=${chat.id}`)}
                      >
                        <div className="flex-1">
                          <p className="font-medium text-sm flex items-center gap-2">
                            <MessageSquare className="h-4 w-4 text-primary" />
                            {chat.title || '未命名对话'}
                          </p>
                          <div className="flex items-center gap-2 mt-1">
                            {chat.providers.map((provider) => (
                              <Badge key={provider} variant="outline" className="text-xs">
                                {provider}
                              </Badge>
                            ))}
                            <span className="text-xs text-muted-foreground">
                              {chat.message_count} 条消息
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {formatDate(chat.updated_at)}
                            </span>
                          </div>
                        </div>
                        <Button variant="ghost" size="sm">
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Suggested Relations */}
          {suggestions.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <Link2 className="h-4 w-4" />
                  相关笔记建议
                  <Badge variant="secondary" className="text-xs">
                    {suggestions.filter(s => !s.is_linked).length} 条待关联
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {loadingSuggestions ? (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    加载中...
                  </div>
                ) : (
                  <div className="space-y-2">
                    {suggestions.map((suggestion) => (
                      <div
                        key={suggestion.note_id}
                        className={`flex items-center justify-between p-3 rounded-md border ${
                          suggestion.is_linked ? 'bg-green-50 border-green-200' : 'hover:bg-muted/50'
                        }`}
                      >
                        <div
                          className="flex-1 cursor-pointer"
                          onClick={() => navigate(`/notes/${suggestion.note_id}`)}
                        >
                          <p className="font-medium text-sm">{suggestion.title}</p>
                          <div className="flex items-center gap-2 mt-1">
                            {suggestion.category && (
                              <Badge variant="outline" className="text-xs">
                                {suggestion.category}
                              </Badge>
                            )}
                            <span className="text-xs text-muted-foreground">
                              相似度: {(suggestion.similarity * 100).toFixed(0)}%
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {formatDate(suggestion.created_at)}
                            </span>
                          </div>
                        </div>
                        <div className="ml-2">
                          {suggestion.is_linked ? (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleUnlink(suggestion.note_id)}
                              disabled={linkingId === suggestion.note_id}
                              className="text-green-600"
                            >
                              {linkingId === suggestion.note_id ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <>
                                  <Check className="h-4 w-4 mr-1" />
                                  已关联
                                </>
                              )}
                            </Button>
                          ) : (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleLink(suggestion.note_id)}
                              disabled={linkingId === suggestion.note_id}
                            >
                              {linkingId === suggestion.note_id ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <>
                                  <Link2 className="h-4 w-4 mr-1" />
                                  关联
                                </>
                              )}
                            </Button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  Bot,
  User,
  Loader2,
  FileText,
  X,
  Check,
  AlertCircle,
  Sparkles,
  Plus,
  History,
  Trash2,
  Download,
  Edit2,
  Archive,
  MessageSquare,
  ExternalLink,
  Link2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  chatService,
  ChatMessage,
  ProviderResponse,
  ChatSessionOut,
  ChatSessionDetail,
} from '@/services/chatService';
import { noteService } from '@/services/noteService';
import type { Note } from '@/types';
import MDEditor from '@uiw/react-md-editor';
import { useNavigate, useSearchParams } from 'react-router-dom';

// Provider colors and icons
const PROVIDER_CONFIG: Record<string, { color: string; bgColor: string; name: string }> = {
  claude: { color: 'text-orange-600', bgColor: 'bg-orange-50', name: 'Claude' },
  deepseek: { color: 'text-blue-600', bgColor: 'bg-blue-50', name: 'DeepSeek' },
  gemini: { color: 'text-purple-600', bgColor: 'bg-purple-50', name: 'Gemini' },
  grok: { color: 'text-gray-600', bgColor: 'bg-gray-50', name: 'Grok' },
};

interface ConversationMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  provider?: string;
  responses?: ProviderResponse[];
  timestamp: Date;
}

export function ChatPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [availableProviders, setAvailableProviders] = useState<string[]>([]);
  const [selectedProviders, setSelectedProviders] = useState<string[]>([]);
  const [providerDescriptions, setProviderDescriptions] = useState<Record<string, string>>({});

  // Session management
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);
  const [sessions, setSessions] = useState<ChatSessionOut[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [editingTitle, setEditingTitle] = useState<number | null>(null);
  const [editTitleValue, setEditTitleValue] = useState('');
  const [initialSessionLoaded, setInitialSessionLoaded] = useState(false);

  // Note selection
  const [showNoteSelector, setShowNoteSelector] = useState(false);
  const [notes, setNotes] = useState<Note[]>([]);
  const [selectedNotes, setSelectedNotes] = useState<Note[]>([]);
  const [loadingNotes, setLoadingNotes] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load available providers
  useEffect(() => {
    async function loadProviders() {
      try {
        const result = await chatService.getProviders();
        setAvailableProviders(result.providers);
        setProviderDescriptions(result.descriptions);
        if (result.providers.length > 0) {
          setSelectedProviders([result.providers[0]]);
        }
      } catch (error) {
        console.error('Failed to load providers:', error);
      }
    }
    loadProviders();
  }, []);

  // Load sessions
  useEffect(() => {
    loadSessions();
  }, []);

  // Handle session query parameter (e.g., /chat?session=123)
  useEffect(() => {
    const sessionParam = searchParams.get('session');
    if (sessionParam && !initialSessionLoaded && availableProviders.length > 0) {
      const sessionId = parseInt(sessionParam, 10);
      if (!isNaN(sessionId)) {
        handleLoadSession(sessionId);
        setInitialSessionLoaded(true);
        // Clear the query param after loading
        setSearchParams({});
      }
    }
  }, [searchParams, availableProviders, initialSessionLoaded]);

  const loadSessions = async () => {
    setLoadingSessions(true);
    try {
      const result = await chatService.listSessions(1, 50);
      setSessions(result.items);
    } catch (error) {
      console.error('Failed to load sessions:', error);
    } finally {
      setLoadingSessions(false);
    }
  };

  // Load notes when selector is opened
  useEffect(() => {
    async function loadNotes() {
      if (!showNoteSelector) return;
      setLoadingNotes(true);
      try {
        const result = await noteService.getNotes({ page: 1, page_size: 50 });
        setNotes(result.items);
      } catch (error) {
        console.error('Failed to load notes:', error);
      } finally {
        setLoadingNotes(false);
      }
    }
    loadNotes();
  }, [showNoteSelector]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const toggleProvider = (provider: string) => {
    setSelectedProviders(prev => {
      if (prev.includes(provider)) {
        return prev.filter(p => p !== provider);
      } else {
        return [...prev, provider];
      }
    });
  };

  const toggleNoteSelection = (note: Note) => {
    setSelectedNotes(prev => {
      if (prev.find(n => n.id === note.id)) {
        return prev.filter(n => n.id !== note.id);
      } else {
        return [...prev, note];
      }
    });
  };

  const handleNewChat = () => {
    setCurrentSessionId(null);
    setMessages([]);
    setSelectedNotes([]);
  };

  const handleLoadSession = async (sessionId: number) => {
    try {
      const detail = await chatService.getSession(sessionId);
      setCurrentSessionId(sessionId);
      setSelectedProviders(detail.providers.length > 0 ? detail.providers : selectedProviders);

      // Convert messages
      const loadedMessages: ConversationMessage[] = detail.messages.map(msg => ({
        id: String(msg.id),
        role: msg.role as 'user' | 'assistant',
        content: msg.content,
        provider: msg.provider || undefined,
        responses: msg.all_responses.length > 0 ? msg.all_responses : undefined,
        timestamp: new Date(msg.created_at),
      }));

      setMessages(loadedMessages);

      // Load linked notes
      if (detail.linked_note_ids.length > 0) {
        const notesResult = await noteService.getNotes({ page: 1, page_size: 50 });
        const linked = notesResult.items.filter(n => detail.linked_note_ids.includes(n.id));
        setSelectedNotes(linked);
      } else {
        setSelectedNotes([]);
      }

      setShowHistory(false);
    } catch (error) {
      console.error('Failed to load session:', error);
    }
  };

  const handleDeleteSession = async (sessionId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('确定要删除这个对话吗？')) return;

    try {
      await chatService.deleteSession(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        handleNewChat();
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  const handleArchiveSession = async (sessionId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await chatService.updateSession(sessionId, { status: 'archived' });
      loadSessions();
    } catch (error) {
      console.error('Failed to archive session:', error);
    }
  };

  const handleUpdateTitle = async (sessionId: number) => {
    if (!editTitleValue.trim()) {
      setEditingTitle(null);
      return;
    }

    try {
      await chatService.updateSession(sessionId, { title: editTitleValue });
      setSessions(prev =>
        prev.map(s => (s.id === sessionId ? { ...s, title: editTitleValue } : s))
      );
      setEditingTitle(null);
    } catch (error) {
      console.error('Failed to update title:', error);
    }
  };

  const handleExportToNote = async () => {
    if (!currentSessionId) return;

    try {
      const result = await chatService.exportToNote(currentSessionId);
      alert(`已导出到笔记: ${result.note_title}`);
      navigate(`/notes/${result.note_id}`);
    } catch (error) {
      console.error('Failed to export to note:', error);
      alert('导出失败');
    }
  };

  const handleSend = async () => {
    if (!input.trim() || selectedProviders.length === 0) return;

    const userMessage: ConversationMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const result = await chatService.sendMessage(
        userMessage.content,
        selectedProviders,
        selectedNotes.map(n => n.id),
        undefined, // No longer passing history - session handles it
        currentSessionId
      );

      // Update session ID if new session was created
      if (result.session_id && !currentSessionId) {
        setCurrentSessionId(result.session_id);
        loadSessions(); // Refresh session list
      }

      const assistantMessage: ConversationMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: result.responses[0]?.content || '',
        responses: result.responses,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      const errorMessage: ConversationMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '发送消息失败，请重试。',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return '今天';
    if (days === 1) return '昨天';
    if (days < 7) return `${days}天前`;
    return date.toLocaleDateString('zh-CN');
  };

  return (
    <div className="h-full flex">
      {/* History Sidebar */}
      {showHistory && (
        <div className="w-72 border-r bg-muted/30 flex flex-col">
          <div className="p-3 border-b flex items-center justify-between">
            <h3 className="font-medium">对话历史</h3>
            <Button variant="ghost" size="sm" onClick={() => setShowHistory(false)}>
              <X className="h-4 w-4" />
            </Button>
          </div>
          <div className="flex-1 overflow-auto p-2 space-y-1">
            {loadingSessions ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : sessions.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                暂无对话历史
              </p>
            ) : (
              sessions.map(session => (
                <div
                  key={session.id}
                  className={`p-2 rounded-md cursor-pointer group ${
                    currentSessionId === session.id
                      ? 'bg-primary/10'
                      : 'hover:bg-muted'
                  }`}
                  onClick={() => handleLoadSession(session.id)}
                >
                  {editingTitle === session.id ? (
                    <Input
                      value={editTitleValue}
                      onChange={e => setEditTitleValue(e.target.value)}
                      onBlur={() => handleUpdateTitle(session.id)}
                      onKeyDown={e => e.key === 'Enter' && handleUpdateTitle(session.id)}
                      onClick={e => e.stopPropagation()}
                      autoFocus
                      className="h-7 text-sm"
                    />
                  ) : (
                    <>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium truncate flex-1">
                          {session.title || '新对话'}
                        </span>
                        <div className="opacity-0 group-hover:opacity-100 flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={e => {
                              e.stopPropagation();
                              setEditingTitle(session.id);
                              setEditTitleValue(session.title || '');
                            }}
                          >
                            <Edit2 className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={e => handleArchiveSession(session.id, e)}
                          >
                            <Archive className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6 text-destructive"
                            onClick={e => handleDeleteSession(session.id, e)}
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-muted-foreground">
                          {formatDate(session.updated_at)}
                        </span>
                        <Badge variant="outline" className="text-xs h-4">
                          {session.message_count} 条
                        </Badge>
                      </div>
                    </>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowHistory(!showHistory)}
              >
                <History className="h-4 w-4 mr-1" />
                历史
              </Button>
              <Button variant="outline" size="sm" onClick={handleNewChat}>
                <Plus className="h-4 w-4 mr-1" />
                新对话
              </Button>
              {currentSessionId && (
                <Button variant="outline" size="sm" onClick={handleExportToNote}>
                  <Download className="h-4 w-4 mr-1" />
                  导出为笔记
                </Button>
              )}
            </div>
            <div>
              <h1 className="text-xl font-bold flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" />
                AI Chat
                {currentSessionId && (
                  <Badge variant="secondary" className="ml-2">
                    #{currentSessionId}
                  </Badge>
                )}
              </h1>
            </div>
          </div>

          {/* Provider Selector */}
          <div className="mt-3">
            <p className="text-sm text-muted-foreground mb-2">选择 AI 模型：</p>
            <div className="flex flex-wrap gap-2">
              {availableProviders.map(provider => {
                const config = PROVIDER_CONFIG[provider] || {
                  color: 'text-gray-600',
                  bgColor: 'bg-gray-50',
                  name: provider,
                };
                const isSelected = selectedProviders.includes(provider);
                return (
                  <Button
                    key={provider}
                    variant={isSelected ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => toggleProvider(provider)}
                    className={isSelected ? '' : config.bgColor}
                    title={providerDescriptions[provider]}
                  >
                    {isSelected && <Check className="h-3 w-3 mr-1" />}
                    {config.name}
                  </Button>
                );
              })}
              {availableProviders.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  没有可用的 AI，请在 .env 中配置 API Key
                </p>
              )}
            </div>
          </div>

          {/* Note Context */}
          <div className="mt-3">
            <div className="flex items-center gap-2 flex-wrap">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowNoteSelector(!showNoteSelector)}
              >
                <FileText className="h-4 w-4 mr-1" />
                关联笔记 {selectedNotes.length > 0 && `(${selectedNotes.length})`}
              </Button>
              {selectedNotes.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {selectedNotes.map(note => (
                    <Badge
                      key={note.id}
                      variant="secondary"
                      className="flex items-center gap-1 pr-1"
                    >
                      <Link2 className="h-3 w-3" />
                      <span
                        className="cursor-pointer hover:underline"
                        onClick={() => navigate(`/notes/${note.id}`)}
                        title="点击查看笔记"
                      >
                        {note.title || `#${note.id}`}
                      </span>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-4 w-4 ml-1 hover:bg-destructive/20"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleNoteSelection(note);
                        }}
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </Badge>
                  ))}
                </div>
              )}
            </div>

            {showNoteSelector && (
              <Card className="mt-2 p-3 max-h-48 overflow-auto">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-medium">选择要关联的笔记：</p>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowNoteSelector(false)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
                {loadingNotes ? (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    加载中...
                  </div>
                ) : (
                  <div className="space-y-1">
                    {notes.map(note => {
                      const isSelected = selectedNotes.find(n => n.id === note.id);
                      return (
                        <div
                          key={note.id}
                          className={`p-2 rounded cursor-pointer flex items-center gap-2 ${
                            isSelected ? 'bg-primary/10' : 'hover:bg-muted'
                          }`}
                          onClick={() => toggleNoteSelection(note)}
                        >
                          {isSelected ? (
                            <Check className="h-4 w-4 text-primary" />
                          ) : (
                            <div className="h-4 w-4" />
                          )}
                          <span className="text-sm truncate flex-1">
                            {note.title || '无标题'}
                          </span>
                          <Badge variant="outline" className="text-xs">
                            {note.category || '未分类'}
                          </Badge>
                        </div>
                      );
                    })}
                  </div>
                )}
              </Card>
            )}
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-auto p-4">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
              <MessageSquare className="h-16 w-16 mb-4 opacity-30" />
              <p>开始与 AI 助手对话</p>
              <p className="text-sm mt-2">对话会自动保存，可随时继续</p>
            </div>
          ) : (
            <div className="space-y-4 max-w-4xl mx-auto">
              {messages.map(message => (
                <div
                  key={message.id}
                  className={`flex gap-3 ${
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {message.role === 'assistant' && (
                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <Bot className="h-4 w-4 text-primary" />
                    </div>
                  )}
                  <div
                    className={`max-w-[80%] ${
                      message.role === 'user'
                        ? 'bg-primary text-primary-foreground rounded-2xl rounded-br-sm px-4 py-2'
                        : 'space-y-2'
                    }`}
                  >
                    {message.role === 'user' ? (
                      <p className="whitespace-pre-wrap">{message.content}</p>
                    ) : message.responses && message.responses.length > 0 ? (
                      message.responses.map((response, idx) => {
                        const config = PROVIDER_CONFIG[response.provider] || {
                          color: 'text-gray-600',
                          bgColor: 'bg-gray-50',
                          name: response.provider,
                        };
                        return (
                          <Card key={idx} className={`p-3 ${config.bgColor} border-l-4`}>
                            <div className="flex items-center gap-2 mb-2">
                              <Badge variant="outline" className={config.color}>
                                {config.name}
                              </Badge>
                              {response.error && (
                                <Badge variant="destructive" className="text-xs">
                                  <AlertCircle className="h-3 w-3 mr-1" />
                                  错误
                                </Badge>
                              )}
                            </div>
                            {response.error ? (
                              <p className="text-sm text-destructive">{response.error}</p>
                            ) : (
                              <div
                                data-color-mode="light"
                                className="prose prose-sm max-w-none"
                              >
                                <MDEditor.Markdown source={response.content} />
                              </div>
                            )}
                          </Card>
                        );
                      })
                    ) : (
                      <Card className="p-3">
                        <p className="whitespace-pre-wrap">{message.content}</p>
                      </Card>
                    )}
                  </div>
                  {message.role === 'user' && (
                    <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                      <User className="h-4 w-4 text-primary-foreground" />
                    </div>
                  )}
                </div>
              ))}
              {isLoading && (
                <div className="flex gap-3 justify-start">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <Bot className="h-4 w-4 text-primary" />
                  </div>
                  <Card className="p-3">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>AI 正在思考...</span>
                    </div>
                  </Card>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-4 border-t bg-background">
          <div className="max-w-4xl mx-auto flex gap-2">
            <Textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
              className="flex-1 min-h-[60px] max-h-[200px] resize-none"
              rows={2}
            />
            <Button
              onClick={handleSend}
              disabled={!input.trim() || selectedProviders.length === 0 || isLoading}
              size="lg"
              className="h-auto"
            >
              {isLoading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Send className="h-5 w-5" />
              )}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground text-center mt-2">
            已选择: {selectedProviders.map(p => PROVIDER_CONFIG[p]?.name || p).join(', ') || '无'}
            {selectedNotes.length > 0 && ` · 关联 ${selectedNotes.length} 条笔记`}
          </p>
        </div>
      </div>
    </div>
  );
}

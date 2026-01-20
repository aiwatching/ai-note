import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Send,
  Loader2,
  Plus,
  Sparkles,
  RotateCcw,
  FileText,
  Save,
  X,
  BrainCircuit,
  FolderOpen,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useNoteStore } from '@/store/noteStore';
import { useSearchStore } from '@/store/searchStore';
import { useConversationStore, type Message } from '@/store/conversationStore';
import type { Note } from '@/types';

// 触发分析的关键词
const ANALYZE_KEYWORDS = ['帮我分析', '分析一下', '帮忙分析', '帮我总结', '总结一下'];
// 触发保存的关键词
const SAVE_KEYWORDS = ['帮我记录', '记录一下', '保存', '记下来', '帮忙记录'];

// 检查触发类型
function getTriggerType(text: string): 'analyze' | 'save' | 'search' | null {
  if (/^(查|找|搜|有哪些|什么|哪些|search|find|what|which)/i.test(text)) {
    return 'search';
  }
  if (ANALYZE_KEYWORDS.some((keyword) => text.includes(keyword))) {
    return 'analyze';
  }
  if (SAVE_KEYWORDS.some((keyword) => text.includes(keyword))) {
    return 'save';
  }
  return null;
}

// 将对话转换为日志 note 内容（只包含用户输入）
function conversationToLogContent(messages: Message[], existingContent?: string): string {
  const userMessages = messages.filter((m) => m.type === 'user');
  const lines: string[] = [];

  // 如果有已存在的内容，先添加
  if (existingContent) {
    lines.push(existingContent);
    lines.push('\n---\n');
    lines.push('## 补充记录\n');
  }

  userMessages.forEach((msg) => {
    const time = new Date(msg.timestamp).toLocaleString('zh-CN');
    lines.push(`[${time}]\n${msg.content}\n`);
  });

  return lines.join('\n');
}

export function HomePage() {
  const navigate = useNavigate();
  const [input, setInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [showNotesList, setShowNotesList] = useState(false);
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { notes, fetchNotes, createNote, updateNote, isLoading: noteLoading } = useNoteStore();
  const { search } = useSearchStore();
  const {
    conversations,
    currentConversationId,
    createConversation,
    addMessage,
    markLogSaved,
    markResultSaved,
  } = useConversationStore();

  // 计算当前对话
  const currentConversation = useMemo(() => {
    if (!currentConversationId) return null;
    return conversations.find((conv) => conv.id === currentConversationId) || null;
  }, [conversations, currentConversationId]);

  const messages = currentConversation?.messages || [];

  // 只显示用户消息（日志）
  const userMessages = useMemo(() => messages.filter((m) => m.type === 'user'), [messages]);

  // 分析结果消息
  const resultMessages = useMemo(() => messages.filter((m) => m.type === 'result'), [messages]);

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 初始化：如果没有当前对话，创建一个新的
  useEffect(() => {
    if (!currentConversationId) {
      createConversation();
    }
  }, [currentConversationId, createConversation]);

  // 加载笔记列表
  useEffect(() => {
    if (showNotesList) {
      fetchNotes({ page: 1 });
    }
  }, [showNotesList, fetchNotes]);

  // 选择已有笔记
  const handleSelectNote = useCallback((note: Note) => {
    setSelectedNote(note);
    setShowNotesList(false);
    // 创建新对话来补充这个笔记
    createConversation();
  }, [createConversation]);

  // 取消选择笔记
  const handleClearSelectedNote = useCallback(() => {
    setSelectedNote(null);
  }, []);

  // 发送消息处理
  const handleSubmit = useCallback(
    async (e?: React.FormEvent) => {
      e?.preventDefault();
      if (!input.trim() || isProcessing) return;

      const userInput = input.trim();
      setInput('');

      // 检查触发类型
      const triggerType = getTriggerType(userInput);

      if (triggerType === 'search') {
        // 搜索不记录到对话
        setIsProcessing(true);
        try {
          await search(userInput);
          setTimeout(() => navigate('/search'), 500);
        } finally {
          setIsProcessing(false);
        }
        return;
      }

      // 添加用户消息到对话（不添加助手反馈）
      addMessage({
        type: 'user',
        content: userInput,
      });

      // 如果有触发词，执行保存/分析
      if (triggerType && currentConversationId) {
        setIsProcessing(true);
        try {
          // 获取所有用户消息（包括刚添加的）
          const allUserMessages = [
            ...userMessages,
            { type: 'user' as const, content: userInput, id: '', timestamp: new Date() },
          ];

          let logNote: Note;

          if (selectedNote) {
            // 如果选择了已有笔记，更新它
            const logContent = conversationToLogContent(allUserMessages, selectedNote.summary || '');
            logNote = await updateNote(selectedNote.id, { content: logContent, reanalyze: triggerType === 'analyze' });
          } else {
            // 创建新笔记
            const logContent = conversationToLogContent(allUserMessages);
            logNote = await createNote({ content: logContent });
          }

          markLogSaved(currentConversationId, logNote.id);

          if (triggerType === 'analyze') {
            // 添加分析结果消息
            addMessage({
              type: 'result',
              content: `分析完成！\n\n标题：${logNote.title || '对话记录'}\n摘要：${logNote.summary || '无'}\n分类：${logNote.category || '无'}\n标签：${logNote.tags?.join(', ') || '无'}`,
              noteId: logNote.id,
            });

            markResultSaved(currentConversationId, logNote.id);
          } else {
            // 只保存，添加保存成功的结果消息
            addMessage({
              type: 'result',
              content: selectedNote
                ? `已补充到笔记：${logNote.title || '对话记录'}`
                : `日志已保存！标题：${logNote.title || '对话记录'}`,
              noteId: logNote.id,
            });
          }

          // 保存后清除选择的笔记
          setSelectedNote(null);
        } catch (error) {
          addMessage({
            type: 'result',
            content: '处理失败，请稍后重试。',
          });
        } finally {
          setIsProcessing(false);
        }
      }
    },
    [input, isProcessing, userMessages, selectedNote, createNote, updateNote, search, navigate, addMessage, markLogSaved, markResultSaved, currentConversationId]
  );

  // 新建对话
  const handleNewConversation = useCallback(() => {
    createConversation();
    setSelectedNote(null);
    setShowNotesList(false);
  }, [createConversation]);

  // 手动保存当前对话日志
  const handleSaveLog = useCallback(async () => {
    if (userMessages.length === 0 || !currentConversationId) return;

    setIsProcessing(true);
    try {
      let logNote: Note;

      if (selectedNote) {
        const logContent = conversationToLogContent(userMessages, selectedNote.summary || '');
        logNote = await updateNote(selectedNote.id, { content: logContent });
      } else {
        const logContent = conversationToLogContent(userMessages);
        logNote = await createNote({ content: logContent });
      }

      markLogSaved(currentConversationId, logNote.id);

      addMessage({
        type: 'result',
        content: selectedNote
          ? `已补充到笔记：${logNote.title || '对话记录'}`
          : `日志已保存！标题：${logNote.title || '对话记录'}`,
        noteId: logNote.id,
      });

      setSelectedNote(null);
    } catch (error) {
      addMessage({
        type: 'result',
        content: '保存失败，请稍后重试。',
      });
    } finally {
      setIsProcessing(false);
    }
  }, [userMessages, selectedNote, createNote, updateNote, addMessage, markLogSaved, currentConversationId]);

  // 手动分析当前对话
  const handleAnalyze = useCallback(async () => {
    if (userMessages.length === 0 || !currentConversationId) return;

    setIsProcessing(true);
    try {
      let logNote: Note;

      if (selectedNote) {
        const logContent = conversationToLogContent(userMessages, selectedNote.summary || '');
        logNote = await updateNote(selectedNote.id, { content: logContent, reanalyze: true });
      } else {
        const logContent = conversationToLogContent(userMessages);
        logNote = await createNote({ content: logContent });
      }

      markLogSaved(currentConversationId, logNote.id);
      markResultSaved(currentConversationId, logNote.id);

      addMessage({
        type: 'result',
        content: `分析完成！\n\n标题：${logNote.title || '对话记录'}\n摘要：${logNote.summary || '无'}\n分类：${logNote.category || '无'}\n标签：${logNote.tags?.join(', ') || '无'}`,
        noteId: logNote.id,
      });

      setSelectedNote(null);
    } catch (error) {
      addMessage({
        type: 'result',
        content: '分析失败，请稍后重试。',
      });
    } finally {
      setIsProcessing(false);
    }
  }, [userMessages, selectedNote, createNote, updateNote, addMessage, markLogSaved, markResultSaved, currentConversationId]);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-primary" />
            AI Notes
          </h1>
          <p className="text-muted-foreground text-sm">
            {selectedNote ? (
              <span className="text-blue-600">正在补充笔记：{selectedNote.title || '无标题'}</span>
            ) : (
              '输入内容记录日志，说"帮我分析"或"帮我记录"来保存'
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={() => setShowNotesList(!showNotesList)}
            variant="outline"
            size="sm"
            title="选择已有笔记补充"
          >
            <FolderOpen className="h-4 w-4 mr-1" />
            选择笔记
          </Button>
          <Button
            onClick={handleNewConversation}
            variant="outline"
            size="sm"
            title="新建对话"
          >
            <RotateCcw className="h-4 w-4 mr-1" />
            新对话
          </Button>
          {userMessages.length > 0 && (
            <>
              <Button
                onClick={handleSaveLog}
                variant="outline"
                size="sm"
                disabled={isProcessing}
                title="保存日志"
              >
                <Save className="h-4 w-4 mr-1" />
                保存
              </Button>
              <Button
                onClick={handleAnalyze}
                variant="outline"
                size="sm"
                disabled={isProcessing}
                title="分析内容"
              >
                <BrainCircuit className="h-4 w-4 mr-1" />
                分析
              </Button>
            </>
          )}
          <Button onClick={() => navigate('/notes')} variant="outline" size="sm">
            <Plus className="h-4 w-4 mr-1" />
            所有笔记
          </Button>
        </div>
      </div>

      {/* Selected Note Indicator */}
      {selectedNote && (
        <div className="px-4 py-2 bg-blue-50 border-b flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-blue-600" />
            <span className="text-sm">
              补充到：<strong>{selectedNote.title || '无标题笔记'}</strong>
              {selectedNote.category && (
                <Badge variant="secondary" className="ml-2 text-xs">{selectedNote.category}</Badge>
              )}
            </span>
          </div>
          <Button variant="ghost" size="sm" onClick={handleClearSelectedNote}>
            <X className="h-4 w-4" />
            取消
          </Button>
        </div>
      )}

      {/* Notes List Panel */}
      {showNotesList && (
        <div className="border-b bg-muted/30 p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-medium flex items-center gap-2">
              <FolderOpen className="h-4 w-4" />
              选择要补充的笔记
            </h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowNotesList(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
          <div className="space-y-2 max-h-48 overflow-auto">
            {noteLoading ? (
              <p className="text-sm text-muted-foreground">加载中...</p>
            ) : notes.length === 0 ? (
              <p className="text-sm text-muted-foreground">暂无笔记</p>
            ) : (
              notes.map((note) => (
                <Card
                  key={note.id}
                  className={`p-3 cursor-pointer hover:bg-muted/50 transition-colors ${
                    selectedNote?.id === note.id ? 'border-primary' : ''
                  }`}
                  onClick={() => handleSelectNote(note)}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-sm truncate max-w-[300px]">
                        {note.title || '无标题'}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(note.created_at).toLocaleString('zh-CN')}
                        {note.summary && ` · ${note.summary.slice(0, 30)}...`}
                      </p>
                    </div>
                    <div className="flex gap-1">
                      {note.category && (
                        <Badge variant="secondary" className="text-xs">
                          {note.category}
                        </Badge>
                      )}
                    </div>
                  </div>
                </Card>
              ))
            )}
          </div>
        </div>
      )}

      {/* Main Content: 左边日志，右边结果 */}
      <div className="flex-1 overflow-hidden flex">
        {/* 左侧：对话日志 */}
        <div className="flex-1 overflow-auto p-4 border-r">
          <div className="flex items-center gap-2 mb-4 text-sm text-muted-foreground">
            <FileText className="h-4 w-4" />
            <span>对话日志</span>
            {currentConversation?.logNoteId && (
              <Badge variant="secondary" className="text-xs">已保存</Badge>
            )}
          </div>
          {userMessages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
              <Sparkles className="h-12 w-12 mb-4 text-primary/30" />
              <p className="font-medium">开始记录</p>
              <p className="text-sm mt-2 text-center max-w-xs">
                {selectedNote
                  ? '输入内容后保存，将补充到选中的笔记。'
                  : '输入内容后点击发送，内容会记录在这里。'}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {userMessages.map((message) => (
                <div key={message.id} className="bg-muted/50 rounded-lg p-3">
                  <p className="text-xs text-muted-foreground mb-1">
                    {new Date(message.timestamp).toLocaleString('zh-CN')}
                  </p>
                  <p className="whitespace-pre-wrap">{message.content}</p>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* 右侧：分析结果 */}
        <div className="w-80 overflow-auto p-4 bg-muted/20">
          <div className="flex items-center gap-2 mb-4 text-sm text-muted-foreground">
            <BrainCircuit className="h-4 w-4" />
            <span>分析结果</span>
            {currentConversation?.resultNoteId && (
              <Badge variant="outline" className="text-xs">已保存</Badge>
            )}
          </div>
          {resultMessages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
              <BrainCircuit className="h-10 w-10 mb-3 text-primary/30" />
              <p className="text-sm text-center">
                说"帮我分析"或点击分析按钮查看结果
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {resultMessages.map((message) => (
                <Card
                  key={message.id}
                  className={`p-3 ${message.noteId ? 'cursor-pointer hover:bg-muted/50' : ''}`}
                  onClick={() => message.noteId && navigate(`/notes/${message.noteId}`)}
                >
                  <p className="text-xs text-muted-foreground mb-2">
                    {new Date(message.timestamp).toLocaleString('zh-CN')}
                  </p>
                  <p className="whitespace-pre-wrap text-sm">{message.content}</p>
                  {message.noteId && (
                    <p className="text-xs text-primary mt-2">点击查看详情</p>
                  )}
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Input */}
      <div className="p-4 border-t bg-muted/30">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
          <div className="relative">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={selectedNote ? `输入内容补充到"${selectedNote.title || '无标题'}"...` : '输入内容记录... (点击发送按钮发送)'}
              className="pr-12 min-h-[60px] max-h-[200px] resize-none"
              rows={2}
            />
            <Button
              type="submit"
              size="icon"
              className="absolute right-2 bottom-2"
              disabled={!input.trim() || isProcessing}
            >
              {isProcessing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

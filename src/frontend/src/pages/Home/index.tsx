import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import MDEditor from '@uiw/react-md-editor';
import {
  Loader2,
  Plus,
  Sparkles,
  FileText,
  Save,
  BrainCircuit,
  FolderOpen,
  X,
  Settings,
  Eye,
  Edit3,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useNoteStore } from '@/store/noteStore';
import { useSettingsStore } from '@/store/settingsStore';
import { noteService } from '@/services/noteService';
import type { Note, NoteDetail } from '@/types';

export function HomePage() {
  const navigate = useNavigate();
  const location = useLocation();

  // 主编辑区内容
  const [noteContent, setNoteContent] = useState('');
  // AI 提示词输入
  const [promptInput, setPromptInput] = useState('');
  // 处理状态
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  // 关联的笔记
  const [linkedNote, setLinkedNote] = useState<NoteDetail | null>(null);
  // 分析结果
  const [analysisResult, setAnalysisResult] = useState<Note | null>(null);
  // 笔记选择列表
  const [showNotesList, setShowNotesList] = useState(false);
  // Markdown 编辑器预览模式: 'edit' | 'preview' | 'live'
  const [editorMode, setEditorMode] = useState<'edit' | 'preview' | 'live'>('live');

  const { notes, fetchNotes, createNote, updateNote, isLoading: noteLoading } = useNoteStore();
  const { deepAnalysisPrompt } = useSettingsStore();

  // 键盘快捷键: Cmd/Ctrl + S 保存
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        if (noteContent.trim() && !isSaving && !isProcessing) {
          handleSave();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [noteContent, isSaving, isProcessing]);

  // 从 Notes 页面传来的编辑 note id
  const editNoteId = (location.state as { editNoteId?: number } | null)?.editNoteId;

  // 加载笔记列表
  useEffect(() => {
    if (showNotesList) {
      fetchNotes({ page: 1 });
    }
  }, [showNotesList, fetchNotes]);

  // 从 Notes 页面跳转过来时，加载指定的 note
  useEffect(() => {
    if (editNoteId) {
      window.history.replaceState({}, document.title);
      loadNote(editNoteId);
    }
  }, [editNoteId]);

  // 加载笔记内容
  const loadNote = async (noteId: number) => {
    setIsProcessing(true);
    try {
      const noteDetail = await noteService.getNote(noteId);
      setNoteContent(noteDetail.raw_content || '');
      setLinkedNote(noteDetail);
      setAnalysisResult(noteDetail);
    } catch (error) {
      console.error('Failed to load note:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  // 选择已有笔记
  const handleSelectNote = useCallback(async (note: Note) => {
    setShowNotesList(false);
    await loadNote(note.id);
  }, []);

  // 新建笔记
  const handleNewNote = useCallback(() => {
    setNoteContent('');
    setPromptInput('');
    setLinkedNote(null);
    setAnalysisResult(null);
    setShowNotesList(false);
  }, []);

  // 保存（仅保存，不分析）
  const handleSave = useCallback(async () => {
    if (!noteContent.trim()) return;

    setIsSaving(true);
    try {
      let savedNote: Note;

      if (linkedNote) {
        // 更新已有笔记（不触发重新分析）
        savedNote = await updateNote(linkedNote.id, {
          content: noteContent,
          reanalyze: false
        });
      } else {
        // 创建新笔记（不带自定义 prompt，使用服务端默认处理）
        savedNote = await createNote({ content: noteContent });
        // 加载完整的笔记详情
        const noteDetail = await noteService.getNote(savedNote.id);
        setLinkedNote(noteDetail);
      }

      setAnalysisResult(savedNote);
    } catch (error) {
      console.error('Failed to save note:', error);
    } finally {
      setIsSaving(false);
    }
  }, [noteContent, linkedNote, createNote, updateNote]);

  // 分析（使用自定义 prompt 或默认 prompt）
  const handleAnalyze = useCallback(async () => {
    if (!noteContent.trim()) return;

    setIsProcessing(true);
    try {
      // 使用用户输入的 prompt，如果没有则使用默认 prompt
      const customPrompt = promptInput.trim() || deepAnalysisPrompt;

      let savedNote: Note;

      if (linkedNote) {
        // 更新并重新分析
        savedNote = await updateNote(linkedNote.id, {
          content: noteContent,
          reanalyze: true,
          custom_prompt: customPrompt
        });
      } else {
        // 创建新笔记并分析
        savedNote = await createNote({
          content: noteContent,
          custom_prompt: customPrompt
        });
      }

      // 加载完整的笔记详情
      const noteDetail = await noteService.getNote(savedNote.id);
      setLinkedNote(noteDetail);
      setAnalysisResult(savedNote);

      // 清空提示词输入
      setPromptInput('');
    } catch (error) {
      console.error('Failed to analyze note:', error);
    } finally {
      setIsProcessing(false);
    }
  }, [noteContent, promptInput, deepAnalysisPrompt, linkedNote, createNote, updateNote]);

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
            {linkedNote ? (
              <span className="text-green-600">编辑笔记：{linkedNote.title || '无标题'}</span>
            ) : (
              '输入内容，保存或分析'
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={() => setShowNotesList(!showNotesList)}
            variant="outline"
            size="sm"
          >
            <FolderOpen className="h-4 w-4 mr-1" />
            选择笔记
          </Button>
          <Button
            onClick={handleNewNote}
            variant="outline"
            size="sm"
          >
            <Plus className="h-4 w-4 mr-1" />
            新建
          </Button>
          <Button onClick={() => navigate('/notes')} variant="outline" size="sm">
            <FileText className="h-4 w-4 mr-1" />
            所有笔记
          </Button>
        </div>
      </div>

      {/* Linked Note Indicator */}
      {linkedNote && (
        <div className="px-4 py-2 bg-green-50 border-b flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-green-600" />
            <span className="text-sm">
              编辑中：<strong>{linkedNote.title || '无标题笔记'}</strong>
              {linkedNote.category && (
                <Badge variant="secondary" className="ml-2 text-xs">{linkedNote.category}</Badge>
              )}
            </span>
          </div>
          <Button variant="ghost" size="sm" onClick={handleNewNote}>
            <X className="h-4 w-4" />
            新建
          </Button>
        </div>
      )}

      {/* Notes List Panel */}
      {showNotesList && (
        <div className="border-b bg-muted/30 p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-medium flex items-center gap-2">
              <FolderOpen className="h-4 w-4" />
              选择要编辑的笔记
            </h3>
            <Button variant="ghost" size="sm" onClick={() => setShowNotesList(false)}>
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
                    linkedNote?.id === note.id ? 'border-primary bg-primary/5' : ''
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
                      </p>
                    </div>
                    <div className="flex gap-1">
                      {linkedNote?.id === note.id && (
                        <Badge variant="default" className="text-xs">当前</Badge>
                      )}
                      {note.category && (
                        <Badge variant="secondary" className="text-xs">{note.category}</Badge>
                      )}
                    </div>
                  </div>
                </Card>
              ))
            )}
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 overflow-hidden flex">
        {/* 左侧：编辑区 */}
        <div className="flex-1 flex flex-col p-4 border-r">
          {/* 笔记内容编辑区 */}
          <div className="flex-1 flex flex-col min-h-0">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <FileText className="h-4 w-4" />
                <span>笔记内容</span>
                {linkedNote && (
                  <Badge variant="secondary" className="text-xs">
                    #{linkedNote.id}
                  </Badge>
                )}
                <Badge variant="outline" className="text-xs">Markdown</Badge>
              </div>
              <div className="flex items-center gap-1">
                <Button
                  variant={editorMode === 'edit' ? 'default' : 'ghost'}
                  size="sm"
                  className="h-7 px-2"
                  onClick={() => setEditorMode('edit')}
                  title="仅编辑"
                >
                  <Edit3 className="h-3 w-3" />
                </Button>
                <Button
                  variant={editorMode === 'live' ? 'default' : 'ghost'}
                  size="sm"
                  className="h-7 px-2"
                  onClick={() => setEditorMode('live')}
                  title="实时预览"
                >
                  <Edit3 className="h-3 w-3 mr-1" />
                  <Eye className="h-3 w-3" />
                </Button>
                <Button
                  variant={editorMode === 'preview' ? 'default' : 'ghost'}
                  size="sm"
                  className="h-7 px-2"
                  onClick={() => setEditorMode('preview')}
                  title="仅预览"
                >
                  <Eye className="h-3 w-3" />
                </Button>
              </div>
            </div>
            <div className="flex-1 min-h-[200px]" data-color-mode="light">
              <MDEditor
                value={noteContent}
                onChange={(val) => setNoteContent(val || '')}
                preview={editorMode}
                height="100%"
                textareaProps={{
                  placeholder: '在这里输入笔记内容...\n\n支持 Markdown 格式：\n- **粗体** 文本\n- *斜体* 文本\n- `代码` 片段\n- 列表和更多',
                }}
              />
            </div>
          </div>

          {/* AI 提示词输入区 */}
          <div className="mt-4 pt-4 border-t">
            <div className="flex items-center gap-2 mb-2 text-sm text-muted-foreground">
              <BrainCircuit className="h-4 w-4" />
              <span>深度分析指令（可选，点击"深度分析"时使用）</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-5 px-1"
                onClick={() => navigate('/settings')}
                title="修改默认分析 Prompt"
              >
                <Settings className="h-3 w-3" />
              </Button>
            </div>
            <Textarea
              value={promptInput}
              onChange={(e) => setPromptInput(e.target.value)}
              placeholder="输入深度分析指令，例如：帮我提取关键要点、待办事项..."
              className="min-h-[80px] resize-none text-sm"
              rows={3}
            />
            <p className="text-xs text-muted-foreground mt-1">
              "保存"会自动提取标题，"深度分析"会进行完整的 AI 分析
            </p>
          </div>

          {/* 操作按钮 */}
          <div className="mt-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Button
                onClick={handleSave}
                disabled={!noteContent.trim() || isSaving || isProcessing}
                variant="outline"
                title="保存笔记并自动提取标题"
              >
                {isSaving ? (
                  <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                ) : (
                  <Save className="h-4 w-4 mr-1" />
                )}
                {linkedNote ? '更新' : '保存'}
              </Button>
              <Button
                onClick={handleAnalyze}
                disabled={!noteContent.trim() || isProcessing}
                title="进行深度 AI 分析"
              >
                {isProcessing ? (
                  <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                ) : (
                  <BrainCircuit className="h-4 w-4 mr-1" />
                )}
                深度分析
              </Button>
              {linkedNote && (
                <span className="text-xs text-muted-foreground ml-2">
                  上次更新：{new Date(linkedNote.updated_at).toLocaleString('zh-CN')}
                </span>
              )}
            </div>
            <div className="text-xs text-muted-foreground">
              {noteContent.length} 字符 · ⌘S 保存
            </div>
          </div>
        </div>

        {/* 右侧：分析结果 */}
        <div className="w-80 overflow-auto p-4 bg-muted/20">
          <div className="flex items-center gap-2 mb-4 text-sm text-muted-foreground">
            <BrainCircuit className="h-4 w-4" />
            <span>分析结果</span>
          </div>

          {!analysisResult ? (
            <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
              <BrainCircuit className="h-10 w-10 mb-3 text-primary/30" />
              <p className="text-sm text-center">
                保存或分析后查看结果
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* 标题 */}
              <Card className="p-3">
                <p className="text-xs text-muted-foreground mb-1">标题</p>
                <p className="font-medium">{analysisResult.title || '无标题'}</p>
              </Card>

              {/* 分类 */}
              <Card className="p-3">
                <p className="text-xs text-muted-foreground mb-1">分类</p>
                <Badge variant="secondary">{analysisResult.category || '未分类'}</Badge>
              </Card>

              {/* 标签 */}
              {analysisResult.tags && analysisResult.tags.length > 0 && (
                <Card className="p-3">
                  <p className="text-xs text-muted-foreground mb-2">标签</p>
                  <div className="flex flex-wrap gap-1">
                    {analysisResult.tags.map((tag, i) => (
                      <Badge key={i} variant="outline" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </Card>
              )}

              {/* 摘要 */}
              {analysisResult.summary && (
                <Card className="p-3">
                  <p className="text-xs text-muted-foreground mb-1">摘要</p>
                  <p className="text-sm">{analysisResult.summary}</p>
                </Card>
              )}

              {/* 待办/日程标记 */}
              <Card className="p-3">
                <p className="text-xs text-muted-foreground mb-2">识别内容</p>
                <div className="flex gap-2">
                  <Badge variant={analysisResult.is_todo ? 'default' : 'outline'}>
                    {analysisResult.is_todo ? '包含待办' : '无待办'}
                  </Badge>
                  <Badge variant={analysisResult.is_schedule ? 'default' : 'outline'}>
                    {analysisResult.is_schedule ? '包含日程' : '无日程'}
                  </Badge>
                </div>
              </Card>

              {/* 查看详情 */}
              <Button
                variant="outline"
                className="w-full"
                onClick={() => navigate(`/notes/${analysisResult.id}`)}
              >
                查看完整详情
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Trash2, AlertTriangle, Loader2 } from 'lucide-react';
import { noteService } from '@/services/noteService';
import { useConversationStore } from '@/store/conversationStore';

export function SettingsPage() {
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteResult, setDeleteResult] = useState<string | null>(null);
  const { conversations } = useConversationStore();

  // 清空所有 notes（软删除）
  const handleDeleteAllNotes = async () => {
    if (!confirm('确定要删除所有笔记吗？（软删除，可恢复）')) {
      return;
    }

    setIsDeleting(true);
    setDeleteResult(null);
    try {
      const result = await noteService.deleteAllNotes(false);
      setDeleteResult(`已删除 ${result.count} 条笔记`);
    } catch (error) {
      setDeleteResult('删除失败，请稍后重试');
    } finally {
      setIsDeleting(false);
    }
  };

  // 永久删除所有 notes
  const handleHardDeleteAllNotes = async () => {
    if (!confirm('警告：这将永久删除所有笔记，无法恢复！确定继续吗？')) {
      return;
    }
    if (!confirm('再次确认：所有笔记将被永久删除！')) {
      return;
    }

    setIsDeleting(true);
    setDeleteResult(null);
    try {
      const result = await noteService.deleteAllNotes(true);
      setDeleteResult(`已永久删除 ${result.count} 条笔记`);
    } catch (error) {
      setDeleteResult('删除失败，请稍后重试');
    } finally {
      setIsDeleting(false);
    }
  };

  // 清空所有对话记录
  const handleClearConversations = () => {
    if (!confirm('确定要清空所有对话记录吗？')) {
      return;
    }

    // 直接清空 localStorage 中的对话记录
    localStorage.removeItem('ai-note-conversations');
    window.location.reload();
  };

  return (
    <div className="h-full overflow-auto">
      <div className="p-4 border-b">
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground">
          Configure your AI Notes application
        </p>
      </div>

      <div className="p-4 max-w-2xl space-y-6">
        {/* AI Configuration */}
        <Card>
          <CardHeader>
            <CardTitle>AI Service</CardTitle>
            <CardDescription>
              Configure the AI service for note analysis
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">Provider</label>
              <div className="flex items-center gap-2 mt-1">
                <Badge>Claude (Anthropic)</Badge>
                <span className="text-sm text-muted-foreground">
                  Powered by Claude Sonnet
                </span>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium">API Key</label>
              <p className="text-xs text-muted-foreground mb-2">
                Configure in the backend .env file
              </p>
              <Input
                type="password"
                placeholder="sk-ant-..."
                disabled
                value="************************"
              />
            </div>
          </CardContent>
        </Card>

        {/* Data Storage */}
        <Card>
          <CardHeader>
            <CardTitle>Data Storage</CardTitle>
            <CardDescription>
              Where your notes are stored
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">Database</label>
              <p className="text-sm text-muted-foreground mt-1">
                SQLite (Local)
              </p>
            </div>
            <div>
              <label className="text-sm font-medium">Notes Directory</label>
              <p className="text-sm text-muted-foreground mt-1">
                ./data/notes/
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Debug Tools */}
        <Card className="border-orange-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-orange-600">
              <AlertTriangle className="h-5 w-5" />
              Debug Tools
            </CardTitle>
            <CardDescription>
              Development and debugging tools - use with caution
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* 清空笔记 */}
            <div className="space-y-2">
              <label className="text-sm font-medium">清空所有笔记</label>
              <p className="text-xs text-muted-foreground">
                删除数据库中的所有笔记记录
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDeleteAllNotes}
                  disabled={isDeleting}
                >
                  {isDeleting ? (
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  ) : (
                    <Trash2 className="h-4 w-4 mr-1" />
                  )}
                  软删除
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleHardDeleteAllNotes}
                  disabled={isDeleting}
                >
                  {isDeleting ? (
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  ) : (
                    <Trash2 className="h-4 w-4 mr-1" />
                  )}
                  永久删除
                </Button>
              </div>
              {deleteResult && (
                <p className="text-sm text-green-600">{deleteResult}</p>
              )}
            </div>

            {/* 清空对话记录 */}
            <div className="space-y-2 pt-4 border-t">
              <label className="text-sm font-medium">清空对话记录</label>
              <p className="text-xs text-muted-foreground">
                清空浏览器中保存的所有对话记录（当前有 {conversations.length} 条对话）
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={handleClearConversations}
              >
                <Trash2 className="h-4 w-4 mr-1" />
                清空对话
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* About */}
        <Card>
          <CardHeader>
            <CardTitle>About</CardTitle>
            <CardDescription>
              AI Notes - Intelligent Note Taking System
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm">Version: 1.0.0 (MVP)</p>
            <p className="text-sm text-muted-foreground">
              An intelligent note-taking system with AI-powered analysis,
              categorization, and conversational search.
            </p>
            <div className="pt-4">
              <p className="text-xs text-muted-foreground">
                Built with FastAPI + React + Claude AI
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

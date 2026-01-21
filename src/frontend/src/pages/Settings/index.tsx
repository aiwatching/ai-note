import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Trash2, AlertTriangle, Loader2, RotateCcw, Save, Plus, X } from 'lucide-react';
import { noteService } from '@/services/noteService';
import { useConversationStore } from '@/store/conversationStore';
import {
  useSettingsStore,
  DEFAULT_DEEP_ANALYSIS_PROMPT,
  DEFAULT_CATEGORIES,
  DEFAULT_DOMAINS,
} from '@/store/settingsStore';

export function SettingsPage() {
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteResult, setDeleteResult] = useState<string | null>(null);
  const [promptSaved, setPromptSaved] = useState(false);
  const [newCategory, setNewCategory] = useState('');
  const [newDomain, setNewDomain] = useState('');

  const { conversations } = useConversationStore();
  const {
    deepAnalysisPrompt,
    categories,
    domains,
    setDeepAnalysisPrompt,
    setCategories,
    setDomains,
    resetToDefaults,
  } = useSettingsStore();

  const [editingPrompt, setEditingPrompt] = useState(deepAnalysisPrompt);

  // 保存 Prompt
  const handleSavePrompt = () => {
    setDeepAnalysisPrompt(editingPrompt);
    setPromptSaved(true);
    setTimeout(() => setPromptSaved(false), 2000);
  };

  // 重置为默认值
  const handleResetAll = () => {
    if (confirm('确定要重置所有设置为默认值吗？')) {
      resetToDefaults();
      setEditingPrompt(DEFAULT_DEEP_ANALYSIS_PROMPT);
    }
  };

  // 添加分类
  const handleAddCategory = () => {
    if (newCategory.trim() && !categories.includes(newCategory.trim())) {
      setCategories([...categories, newCategory.trim()]);
      setNewCategory('');
    }
  };

  // 删除分类
  const handleRemoveCategory = (cat: string) => {
    setCategories(categories.filter((c) => c !== cat));
  };

  // 添加领域
  const handleAddDomain = () => {
    if (newDomain.trim() && !domains.includes(newDomain.trim())) {
      setDomains([...domains, newDomain.trim()]);
      setNewDomain('');
    }
  };

  // 删除领域
  const handleRemoveDomain = (domain: string) => {
    setDomains(domains.filter((d) => d !== domain));
  };

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
    localStorage.removeItem('ai-note-conversations');
    window.location.reload();
  };

  return (
    <div className="h-full overflow-auto">
      <div className="p-4 border-b">
        <h1 className="text-2xl font-bold">设置</h1>
        <p className="text-muted-foreground">配置 AI Notes 系统参数</p>
      </div>

      <div className="p-4 max-w-4xl space-y-6">
        {/* AI 深度分析 Prompt */}
        <Card>
          <CardHeader>
            <CardTitle>深度分析 Prompt</CardTitle>
            <CardDescription>
              第一步笔记分析使用的 AI 提示词模板。支持变量：{'{content}'}, {'{current_date}'},{' '}
              {'{categories}'}, {'{domains}'}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Textarea
              value={editingPrompt}
              onChange={(e) => setEditingPrompt(e.target.value)}
              placeholder="输入深度分析提示词..."
              className="min-h-[400px] font-mono text-xs"
            />
            <div className="flex items-center gap-2">
              <Button onClick={handleSavePrompt} size="sm">
                <Save className="h-4 w-4 mr-1" />
                保存 Prompt
              </Button>
              <Button
                onClick={() => setEditingPrompt(DEFAULT_DEEP_ANALYSIS_PROMPT)}
                variant="outline"
                size="sm"
              >
                <RotateCcw className="h-4 w-4 mr-1" />
                恢复默认 Prompt
              </Button>
              {promptSaved && <span className="text-sm text-green-600">已保存</span>}
            </div>
          </CardContent>
        </Card>

        {/* 分类配置 */}
        <Card>
          <CardHeader>
            <CardTitle>笔记分类</CardTitle>
            <CardDescription>自定义笔记分类列表，AI 分析时会从中选择</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {categories.map((cat) => (
                <Badge key={cat} variant="secondary" className="text-sm py-1 px-2">
                  {cat}
                  <button
                    onClick={() => handleRemoveCategory(cat)}
                    className="ml-1 hover:text-red-500"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
            </div>
            <div className="flex gap-2">
              <Input
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
                placeholder="添加新分类..."
                className="max-w-xs"
                onKeyDown={(e) => e.key === 'Enter' && handleAddCategory()}
              />
              <Button onClick={handleAddCategory} size="sm" variant="outline">
                <Plus className="h-4 w-4 mr-1" />
                添加
              </Button>
              <Button
                onClick={() => setCategories(DEFAULT_CATEGORIES)}
                size="sm"
                variant="ghost"
              >
                恢复默认
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* 领域配置 */}
        <Card>
          <CardHeader>
            <CardTitle>领域列表</CardTitle>
            <CardDescription>自定义领域列表，用于笔记主题分析</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {domains.map((domain) => (
                <Badge key={domain} variant="outline" className="text-sm py-1 px-2">
                  {domain}
                  <button
                    onClick={() => handleRemoveDomain(domain)}
                    className="ml-1 hover:text-red-500"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
            </div>
            <div className="flex gap-2">
              <Input
                value={newDomain}
                onChange={(e) => setNewDomain(e.target.value)}
                placeholder="添加新领域..."
                className="max-w-xs"
                onKeyDown={(e) => e.key === 'Enter' && handleAddDomain()}
              />
              <Button onClick={handleAddDomain} size="sm" variant="outline">
                <Plus className="h-4 w-4 mr-1" />
                添加
              </Button>
              <Button onClick={() => setDomains(DEFAULT_DOMAINS)} size="sm" variant="ghost">
                恢复默认
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* AI 服务配置 */}
        <Card>
          <CardHeader>
            <CardTitle>AI 服务</CardTitle>
            <CardDescription>AI 分析服务配置（在后端 .env 文件中修改）</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">当前服务商</label>
              <div className="flex items-center gap-2 mt-1">
                <Badge>Claude (Anthropic)</Badge>
                <span className="text-sm text-muted-foreground">Powered by Claude Sonnet</span>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium">API Key</label>
              <p className="text-xs text-muted-foreground mb-2">在后端 .env 文件中配置</p>
              <Input type="password" placeholder="sk-ant-..." disabled value="************************" />
            </div>
          </CardContent>
        </Card>

        {/* 数据存储 */}
        <Card>
          <CardHeader>
            <CardTitle>数据存储</CardTitle>
            <CardDescription>笔记存储位置</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">数据库</label>
              <p className="text-sm text-muted-foreground mt-1">SQLite (本地)</p>
            </div>
            <div>
              <label className="text-sm font-medium">笔记目录</label>
              <p className="text-sm text-muted-foreground mt-1">./data/notes/</p>
            </div>
          </CardContent>
        </Card>

        {/* 调试工具 */}
        <Card className="border-orange-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-orange-600">
              <AlertTriangle className="h-5 w-5" />
              调试工具
            </CardTitle>
            <CardDescription>开发调试工具，请谨慎使用</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* 重置所有设置 */}
            <div className="space-y-2">
              <label className="text-sm font-medium">重置所有设置</label>
              <p className="text-xs text-muted-foreground">将所有配置恢复为默认值</p>
              <Button variant="outline" size="sm" onClick={handleResetAll}>
                <RotateCcw className="h-4 w-4 mr-1" />
                重置所有设置
              </Button>
            </div>

            {/* 清空笔记 */}
            <div className="space-y-2 pt-4 border-t">
              <label className="text-sm font-medium">清空所有笔记</label>
              <p className="text-xs text-muted-foreground">删除数据库中的所有笔记记录</p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={handleDeleteAllNotes} disabled={isDeleting}>
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
              {deleteResult && <p className="text-sm text-green-600">{deleteResult}</p>}
            </div>

            {/* 清空对话记录 */}
            <div className="space-y-2 pt-4 border-t">
              <label className="text-sm font-medium">清空对话记录</label>
              <p className="text-xs text-muted-foreground">
                清空浏览器中保存的所有对话记录（当前有 {conversations.length} 条对话）
              </p>
              <Button variant="outline" size="sm" onClick={handleClearConversations}>
                <Trash2 className="h-4 w-4 mr-1" />
                清空对话
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* 关于 */}
        <Card>
          <CardHeader>
            <CardTitle>关于</CardTitle>
            <CardDescription>AI Notes - 智能笔记管理系统</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm">版本: 1.0.0 (Beta)</p>
            <p className="text-sm text-muted-foreground">
              支持深度 AI 分析、实体识别、笔记关联和智能聚合的笔记管理系统
            </p>
            <div className="pt-4">
              <p className="text-xs text-muted-foreground">Built with FastAPI + React + Claude AI</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

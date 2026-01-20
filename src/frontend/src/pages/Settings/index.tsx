import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export function SettingsPage() {
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

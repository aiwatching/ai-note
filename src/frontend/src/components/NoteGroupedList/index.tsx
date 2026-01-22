import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronDown, ChevronRight, FileText, Clock, FolderOpen, Loader2 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { NoteGroup } from '@/types';

interface NoteGroupedListProps {
  groups: NoteGroup[];
  isLoading: boolean;
}

export function NoteGroupedList({ groups, isLoading }: NoteGroupedListProps) {
  const navigate = useNavigate();
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  const toggleGroup = (title: string) => {
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(title)) {
      newExpanded.delete(title);
    } else {
      newExpanded.add(title);
    }
    setExpandedGroups(newExpanded);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12 text-muted-foreground">
        <Loader2 className="h-8 w-8 animate-spin mr-2" />
        <span>加载中...</span>
      </div>
    );
  }

  if (groups.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <FolderOpen className="h-12 w-12 mx-auto mb-4 opacity-50" />
        <p>暂无笔记</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {groups.map((group) => {
        const isExpanded = expandedGroups.has(group.title);
        const hasSingleNote = group.note_count === 1;

        return (
          <Card key={group.title} className="overflow-hidden">
            {/* Group Header */}
            <div
              className="p-4 cursor-pointer hover:bg-muted/50 transition-colors flex items-center justify-between"
              onClick={() => {
                if (hasSingleNote) {
                  // Single note - navigate directly
                  navigate(`/notes/${group.notes[0].id}`);
                } else {
                  // Multiple notes - toggle expansion
                  toggleGroup(group.title);
                }
              }}
            >
              <div className="flex items-center gap-3">
                {!hasSingleNote && (
                  <div className="text-muted-foreground">
                    {isExpanded ? (
                      <ChevronDown className="h-5 w-5" />
                    ) : (
                      <ChevronRight className="h-5 w-5" />
                    )}
                  </div>
                )}
                {hasSingleNote && <FileText className="h-5 w-5 text-muted-foreground" />}
                <div>
                  <h3 className="font-medium">{group.title}</h3>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                    <Clock className="h-3 w-3" />
                    <span>
                      {new Date(group.latest_updated_at).toLocaleString('zh-CN')}
                    </span>
                    {group.notes[0]?.category && (
                      <Badge variant="outline" className="text-xs">
                        {group.notes[0].category}
                      </Badge>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {!hasSingleNote && (
                  <Badge variant="secondary" className="text-xs">
                    {group.note_count} 条笔记
                  </Badge>
                )}
              </div>
            </div>

            {/* Expanded Notes List */}
            {isExpanded && !hasSingleNote && (
              <div className="border-t bg-muted/20">
                {group.notes.map((note, index) => (
                  <div
                    key={note.id}
                    className={`px-4 py-3 cursor-pointer hover:bg-muted/50 transition-colors flex items-center gap-3 ${
                      index !== group.notes.length - 1 ? 'border-b' : ''
                    }`}
                    onClick={() => navigate(`/notes/${note.id}`)}
                  >
                    <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0 ml-6" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm truncate">
                        {note.summary || note.title || '无摘要'}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(note.created_at).toLocaleString('zh-CN')}
                      </p>
                    </div>
                    <Badge variant="outline" className="text-xs flex-shrink-0">
                      #{note.id}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
}

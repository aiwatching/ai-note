import React from 'react';
import { Link } from 'react-router-dom';
import { FileText, Lightbulb, ArrowRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { SearchResult, SearchSuggestion } from '@/types';
import { formatRelativeDate } from '@/utils/date';

interface SearchResultsProps {
  intent: string;
  results: SearchResult[];
  suggestions: SearchSuggestion[];
  isLoading?: boolean;
}

export function SearchResults({
  intent,
  results,
  suggestions,
  isLoading,
}: SearchResultsProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
        <FileText className="h-12 w-12 mb-4" />
        <p>No results found</p>
        <p className="text-sm">Try a different search query</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Intent */}
      <div className="p-4 bg-muted/50 rounded-lg">
        <p className="text-sm">
          <span className="text-muted-foreground">Understanding: </span>
          <span className="font-medium">{intent}</span>
        </p>
        <p className="text-sm text-muted-foreground mt-1">
          Found {results.length} relevant notes
        </p>
      </div>

      {/* Results */}
      <div className="space-y-3">
        {results.map((result) => (
          <SearchResultCard key={result.note_id} result={result} />
        ))}
      </div>

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Lightbulb className="h-4 w-4" />
              Suggested Actions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {suggestions.map((suggestion, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-2 bg-muted/50 rounded-md"
                >
                  <span className="text-sm">{suggestion.description}</span>
                  <Button variant="ghost" size="sm">
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function SearchResultCard({ result }: { result: SearchResult }) {
  return (
    <Link to={`/notes/${result.note_id}`}>
      <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
        <CardContent className="p-4">
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <h3 className="font-medium truncate">
                {result.title || 'Untitled Note'}
              </h3>
              {result.highlight && (
                <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                  {result.highlight}
                </p>
              )}
              <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                <span>{formatRelativeDate(result.created_at)}</span>
                {result.category && (
                  <Badge variant="secondary" className="text-xs">
                    {result.category}
                  </Badge>
                )}
              </div>
            </div>
            <div className="ml-4">
              <Badge variant="outline">
                {Math.round(result.relevance_score * 100)}% match
              </Badge>
            </div>
          </div>
          {result.tags && result.tags.length > 0 && (
            <div className="flex items-center gap-1 mt-3 flex-wrap">
              {result.tags.slice(0, 3).map((tag) => (
                <Badge key={tag} variant="outline" className="text-xs">
                  {tag}
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}

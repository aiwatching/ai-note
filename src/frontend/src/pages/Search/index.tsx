import React, { useCallback } from 'react';
import { SearchBar } from '@/components/SearchBar';
import { SearchResults } from '@/components/SearchResults';
import { useSearchStore } from '@/store/searchStore';

export function SearchPage() {
  const { intent, results, suggestions, isLoading, search } = useSearchStore();

  const handleSearch = useCallback(
    (query: string) => {
      search(query);
    },
    [search]
  );

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b">
        <h1 className="text-2xl font-bold">Search</h1>
        <p className="text-muted-foreground">
          Ask questions about your notes in natural language
        </p>
      </div>

      {/* Search Bar */}
      <div className="p-4 border-b">
        <SearchBar onSearch={handleSearch} isLoading={isLoading} />
      </div>

      {/* Results */}
      <div className="flex-1 overflow-auto p-4">
        {(results.length > 0 || intent) && (
          <SearchResults
            intent={intent}
            results={results}
            suggestions={suggestions}
            isLoading={isLoading}
          />
        )}
        {!isLoading && results.length === 0 && !intent && (
          <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
            <p className="text-lg font-medium">Ask a question</p>
            <p className="text-sm mt-2">Examples:</p>
            <ul className="mt-2 space-y-1 text-sm">
              <li>"有哪些需求问题还没确定？"</li>
              <li>"上周和客户A相关的问题"</li>
              <li>"我学了哪些关于Python的知识？"</li>
              <li>"本周需要开哪些会？"</li>
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { HomePage } from '@/pages/Home';
import { NotesPage } from '@/pages/Notes';
import { SearchPage } from '@/pages/Search';
import { TodoPage } from '@/pages/Todo';
import { SettingsPage } from '@/pages/Settings';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="notes" element={<NotesPage />} />
        <Route path="notes/:id" element={<NotesPage />} />
        <Route path="search" element={<SearchPage />} />
        <Route path="todos" element={<TodoPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}

export default App;

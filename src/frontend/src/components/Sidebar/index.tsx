import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  FileText,
  Home,
  Search,
  CheckSquare,
  Settings,
  PenLine,
  MessageSquare,
} from 'lucide-react';
import { cn } from '@/utils/cn';

const navItems = [
  { to: '/', icon: Home, label: 'Home' },
  { to: '/notes', icon: FileText, label: 'Notes' },
  { to: '/chat', icon: MessageSquare, label: 'AI Chat' },
  { to: '/search', icon: Search, label: 'Search' },
  { to: '/todos', icon: CheckSquare, label: 'Todos' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

export function Sidebar() {
  return (
    <aside className="w-64 border-r bg-muted/40 flex flex-col">
      {/* Logo */}
      <div className="p-4 border-b">
        <div className="flex items-center gap-2">
          <PenLine className="h-6 w-6 text-primary" />
          <span className="text-lg font-semibold">AI Notes</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              )
            }
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t">
        <p className="text-xs text-muted-foreground text-center">
          Powered by Claude AI
        </p>
      </div>
    </aside>
  );
}

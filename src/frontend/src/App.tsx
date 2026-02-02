import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { useChatStore } from './store/chatStore';
import DebugPanel from './components/DebugPanel';
import {
  Send,
  Plus,
  MessageSquare,
  Trash2,
  Settings,
  Bot,
  User,
  Loader2,
  ChevronDown,
} from 'lucide-react';

function App() {
  const [input, setInput] = useState('');
  const [showSidebar, setShowSidebar] = useState(true);
  const [showDebugPanel, setShowDebugPanel] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    messages,
    isLoading,
    error,
    selectedModel,
    availableModels,
    conversations,
    sendMessage,
    loadConversation,
    newConversation,
    loadConversations,
    deleteConversation,
    setModel,
    loadModels,
  } = useChatStore();

  // 初始化
  useEffect(() => {
    loadConversations();
    loadModels();
  }, []);

  // 自动滚动
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 发送消息
  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    const message = input.trim();
    setInput('');
    await sendMessage(message);
  };

  // 键盘事件 - Ctrl+Enter 或 Cmd+Enter 发送
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-screen bg-gray-100">
      {/* 侧边栏 */}
      {showSidebar && (
        <div className="w-60 bg-gray-900 text-gray-100 flex flex-col">
          {/* 新对话按钮 */}
          <div className="p-3">
            <button
              onClick={newConversation}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-md border border-gray-700 hover:bg-gray-800 transition text-sm"
            >
              <Plus size={16} />
              新对话
            </button>
          </div>

          {/* 对话列表 */}
          <div className="flex-1 overflow-y-auto px-2">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                className="group flex items-center gap-2 px-3 py-2 rounded-md hover:bg-gray-800 cursor-pointer mb-1"
                onClick={() => loadConversation(conv.id)}
              >
                <MessageSquare size={14} className="text-gray-500 flex-shrink-0" />
                <span className="flex-1 truncate text-sm text-gray-300">
                  {conv.title || '新对话'}
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteConversation(conv.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            ))}
          </div>

          {/* 底部 */}
          <div className="p-3 border-t border-gray-800">
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <Settings size={14} />
              <span>AI Assistant v2.0</span>
            </div>
          </div>
        </div>
      )}

      {/* 主内容区 */}
      <div className={`flex-1 flex flex-col ${showDebugPanel ? 'pb-72' : ''}`}>
        {/* 顶部栏 */}
        <div className="h-12 bg-white border-b flex items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowSidebar(!showSidebar)}
              className="p-1.5 hover:bg-gray-100 rounded"
            >
              <MessageSquare size={18} />
            </button>
            <span className="text-sm font-medium text-gray-700">AI Assistant</span>
          </div>

          {/* 模型选择 */}
          <div className="relative">
            <select
              value={selectedModel}
              onChange={(e) => setModel(e.target.value)}
              className="appearance-none bg-gray-100 text-sm px-3 py-1.5 pr-8 rounded-md cursor-pointer hover:bg-gray-200"
            >
              {availableModels.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
            <ChevronDown
              size={14}
              className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-gray-500"
            />
          </div>
        </div>

        {/* 消息区域 */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto py-4 px-4">
            {messages.length === 0 ? (
              <div className="text-center text-gray-400 mt-20">
                <Bot size={40} className="mx-auto mb-3 text-gray-300" />
                <p className="text-sm">开始一个新对话</p>
              </div>
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-3 mb-4 ${
                    msg.role === 'user' ? 'justify-end' : ''
                  }`}
                >
                  {msg.role === 'assistant' && (
                    <div className="w-7 h-7 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0">
                      <Bot size={14} className="text-white" />
                    </div>
                  )}

                  <div
                    className={`max-w-[85%] rounded-lg px-3 py-2 ${
                      msg.role === 'user'
                        ? 'bg-blue-500 text-white'
                        : 'bg-white border shadow-sm'
                    }`}
                  >
                    {msg.role === 'assistant' ? (
                      <div className="markdown-content text-sm text-gray-800">
                        <ReactMarkdown>{msg.content || '...'}</ReactMarkdown>
                        {msg.isStreaming && (
                          <span className="inline-block w-1.5 h-4 bg-gray-400 ml-0.5 animate-pulse" />
                        )}
                      </div>
                    ) : (
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    )}
                  </div>

                  {msg.role === 'user' && (
                    <div className="w-7 h-7 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
                      <User size={14} className="text-gray-600" />
                    </div>
                  )}
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="mx-4 mb-2 px-3 py-2 bg-red-50 border border-red-200 text-red-600 text-sm rounded-md">
            {error}
          </div>
        )}

        {/* 输入区域 */}
        <div className="bg-white border-t p-4">
          <div className="max-w-3xl mx-auto">
            <div className="flex gap-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="输入消息... (Ctrl+Enter 发送)"
                className="flex-1 resize-none border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[40px] max-h-[120px]"
                rows={1}
                disabled={isLoading}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center gap-2"
              >
                {isLoading ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Send size={16} />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Debug Panel */}
      <DebugPanel
        isOpen={showDebugPanel}
        onToggle={() => setShowDebugPanel(!showDebugPanel)}
      />
    </div>
  );
}

export default App;

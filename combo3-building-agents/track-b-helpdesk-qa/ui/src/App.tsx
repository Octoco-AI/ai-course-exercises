import { ChatPanel } from "./components/ChatPanel";
import { InputBar } from "./components/InputBar";
import { useStreamingChat } from "./hooks/useStreamingChat";

export function App() {
  const { messages, isStreaming, send, cancel } = useStreamingChat();

  return (
    <div className="app">
      <header className="app__header">
        <h1>Streakly · Helpdesk Agent</h1>
        <span className="app__subtitle">
          Drafts KB-backed replies. Escalates when a human is needed.
        </span>
      </header>
      <main className="app__main">
        <ChatPanel messages={messages} />
      </main>
      <footer className="app__footer">
        <InputBar onSend={send} onCancel={cancel} isStreaming={isStreaming} />
      </footer>
    </div>
  );
}

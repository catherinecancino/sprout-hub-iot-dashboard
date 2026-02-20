// frontend/src/components/Chatbot.jsx
import { useState, useEffect } from 'react';
import { MessageCircle, Send, X, Bot } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext'; // ADD THIS

export default function Chatbot() {
  const { language, t } = useLanguage(); // ADD THIS
  
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  
  // CHANGE: Make initial message dynamic based on language
  const getInitialMessage = () => {
    if (language === 'fil') {
      return 'Kumusta! Ako ang iyong AI Agronomist. Magtanong tungkol sa kalusugan ng iyong lupa o tanim.';
    }
    return 'Hello! I am your AI Agronomist. Ask me about your soil health or crop conditions.';
  };

  const [messages, setMessages] = useState([
    { role: 'assistant', text: getInitialMessage() }
  ]);

  // ADD: Update greeting when language changes
  useEffect(() => {
    setMessages([{ role: 'assistant', text: getInitialMessage() }]);
  }, [language]);

  const API_BASE = 'http://127.0.0.1:8000/api/v1';

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMsg = { role: 'user', text: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/chat/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userMsg.text })
      });
      
      const data = await res.json();
      
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        text: data.answer,
        model: data.model
      }]);
    } catch (err) {
      const errorMsg = language === 'fil' 
        ? "Error sa pag-connect sa AI. Siguruhing tumatakbo ang server."
        : "Error connecting to AI. Please check if the server is running.";
      
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        text: errorMsg
      }]);
    } finally {
      setLoading(false);
    }
  };

  // Dynamic placeholder based on language
  const placeholderText = language === 'fil' 
    ? 'Magtanong tungkol sa lupa, tanim...'
    : 'Ask about soil, crops...';

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {!isOpen && (
        <button 
          onClick={() => setIsOpen(true)}
          className="bg-green-600 hover:bg-green-700 text-white p-4 rounded-full shadow-lg transition-all"
        >
          <MessageCircle size={28} />
        </button>
      )}

      {isOpen && (
        <div className="bg-white w-80 md:w-96 h-[500px] rounded-2xl shadow-2xl flex flex-col border border-gray-200 overflow-hidden">
          <div className="bg-green-600 p-4 text-white flex justify-between items-center">
            <div className="flex items-center gap-2">
              <Bot size={20} />
              <span className="font-bold">
                {language === 'fil' ? 'AI Agronomo' : 'AI Agronomist'}
              </span>
            </div>
            <button onClick={() => setIsOpen(false)}>
              <X size={20} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
            {messages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] p-3 rounded-xl text-sm ${
                  msg.role === 'user' 
                    ? 'bg-green-600 text-white rounded-br-none' 
                    : 'bg-white border border-gray-200 text-gray-800 rounded-bl-none shadow-sm'
                }`}>
                  {msg.text}
                  {msg.model && (
                    <div className="text-xs text-gray-400 mt-1">
                      via {msg.model}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-white border border-gray-200 p-3 rounded-xl text-sm text-gray-500">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="p-3 bg-white border-t flex gap-2">
            <input 
              className="flex-1 border rounded-full px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
              placeholder={placeholderText}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            />
            <button 
              onClick={sendMessage}
              disabled={loading}
              className="bg-green-600 text-white p-2 rounded-full hover:bg-green-700 disabled:bg-gray-400"
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
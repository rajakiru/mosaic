import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles } from 'lucide-react';

const DecisionTreeApp = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [tiles, setTiles] = useState([]);
  const [connections, setConnections] = useState([]);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const colors = [
    { bg: 'linear-gradient(135deg, #fef9ef 0%, #e8f0fe 50%, #fce4ec 100%)', border: '#e0d8cf', shadow: 'rgba(200, 180, 160, 0.25)' },
    { bg: 'linear-gradient(135deg, #e8f0fe 0%, #f3e8fd 50%, #fef9ef 100%)', border: '#c8d4e8', shadow: 'rgba(160, 180, 210, 0.25)' },
    { bg: 'linear-gradient(135deg, #f3e8fd 0%, #fce4ec 50%, #e8f0fe 100%)', border: '#dcc8e8', shadow: 'rgba(190, 160, 210, 0.25)' },
    { bg: 'linear-gradient(135deg, #fce4ec 0%, #fef9ef 50%, #e0f5e9 100%)', border: '#e8c8c8', shadow: 'rgba(210, 160, 170, 0.25)' },
    { bg: 'linear-gradient(135deg, #e0f5e9 0%, #e8f0fe 50%, #fef9ef 100%)', border: '#c0dcc8', shadow: 'rgba(150, 200, 170, 0.25)' },
  ];

  const getRandomPosition = (index, total) => {
    const cols = Math.ceil(Math.sqrt(total));
    const row = Math.floor(index / cols);
    const col = index % cols;
    
    const baseX = col * 280 + 50;
    const baseY = row * 200 + 50;
    
    const randomX = baseX + (Math.random() - 0.5) * 40;
    const randomY = baseY + (Math.random() - 0.5) * 40;
    
    return { x: randomX, y: randomY };
  };

  const handleSendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    
    const newMessages = [...messages, { role: 'user', content: userMessage }];
    setMessages(newMessages);
    setLoading(true);

    // Add user tile immediately
    const userTileId = `tile-${Date.now()}-user`;
    const userPosition = getRandomPosition(tiles.length, tiles.length + 1);
    
    setTimeout(() => {
      setTiles(prev => [...prev, {
        id: userTileId,
        content: userMessage,
        type: 'user',
        color: colors[tiles.length % colors.length],
        position: userPosition,
        rotation: (Math.random() - 0.5) * 8,
        scale: 0
      }]);
      
      // Animate in
      setTimeout(() => {
        setTiles(prev => prev.map(t => 
          t.id === userTileId ? { ...t, scale: 1 } : t
        ));
      }, 50);
    }, 100);

    try {
      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 1000,
          messages: newMessages,
          system: `You are a helpful decision-making assistant. Your job is to help users make decisions by asking clarifying questions.

When the user asks their first question, acknowledge it briefly and ask 2-3 relevant clarifying questions to understand their situation better.

After each user response, provide thoughtful follow-up questions that help narrow down the decision.

After 3-4 exchanges, provide a clear recommendation or insight based on the conversation.

Keep responses concise and friendly. Each response should be 2-4 sentences max.`
        })
      });

      const data = await response.json();
      const assistantMessage = data.content
        .map(item => item.type === 'text' ? item.text : '')
        .join('\n');

      setMessages([...newMessages, { role: 'assistant', content: assistantMessage }]);
      
      // Add AI tile with connection
      const aiTileId = `tile-${Date.now()}-ai`;
      const aiPosition = getRandomPosition(tiles.length + 1, tiles.length + 2);
      
      setTimeout(() => {
        setTiles(prev => [...prev, {
          id: aiTileId,
          content: assistantMessage,
          type: 'assistant',
          color: colors[(tiles.length + 1) % colors.length],
          position: aiPosition,
          rotation: (Math.random() - 0.5) * 8,
          scale: 0
        }]);
        
        // Add connection line
        setConnections(prev => [...prev, {
          from: userTileId,
          to: aiTileId,
          id: `conn-${Date.now()}`
        }]);
        
        // Animate in
        setTimeout(() => {
          setTiles(prev => prev.map(t => 
            t.id === aiTileId ? { ...t, scale: 1 } : t
          ));
        }, 50);
      }, 500);
      
    } catch (error) {
      console.error('Error:', error);
      setMessages([...newMessages, { 
        role: 'assistant', 
        content: 'Sorry, I encountered an error. Please try again.' 
      }]);
    } finally {
      setLoading(false);
    }
  };

  const MosaicTile = ({ tile }) => {
    const isUser = tile.type === 'user';

    return (
      <div
        style={{
          position: 'absolute',
          left: `${tile.position.x}px`,
          top: `${tile.position.y}px`,
          transform: `rotate(${tile.rotation}deg) scale(${tile.scale})`,
          transition: 'all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)',
        }}
        className="w-64"
      >
        <div
          style={{
            background: tile.color.bg,
            borderColor: tile.color.border,
            boxShadow: `0 8px 32px ${tile.color.shadow}, 0 2px 8px rgba(0,0,0,0.04)`,
          }}
          className="border rounded-2xl p-4 hover:shadow-xl transition-all cursor-pointer hover:scale-105 backdrop-blur-sm"
        >
          <div className="flex items-start gap-2 mb-2">
            <div className={`w-2 h-2 rounded-full mt-1 ${isUser ? 'bg-blue-300' : 'bg-emerald-300'}`}></div>
            <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
              {isUser ? 'You' : 'Insight'}
            </div>
          </div>
          <div className="text-sm text-gray-600 leading-relaxed">
            {tile.content}
          </div>
        </div>
      </div>
    );
  };

  const ConnectionLine = ({ connection }) => {
    const fromTile = tiles.find(t => t.id === connection.from);
    const toTile = tiles.find(t => t.id === connection.to);

    if (!fromTile || !toTile) return null;

    const x1 = fromTile.position.x + 128;
    const y1 = fromTile.position.y + 60;
    const x2 = toTile.position.x + 128;
    const y2 = toTile.position.y + 60;

    return (
      <line
        x1={x1}
        y1={y1}
        x2={x2}
        y2={y2}
        stroke="#d4c8be"
        strokeWidth="1.5"
        strokeDasharray="6,4"
        opacity="0.4"
        className="transition-all duration-500"
      />
    );
  };

  return (
    <div className="h-screen flex" style={{ background: '#f5f2ee' }}>
      {/* Chat Panel */}
      <div className="w-2/5 flex flex-col border-r" style={{ background: '#faf8f5', borderColor: '#e8e2da' }}>
        <div className="p-6 border-b" style={{ borderColor: '#e8e2da', background: 'linear-gradient(135deg, #fef9ef 0%, #e8f0fe 50%, #f3e8fd 100%)' }}>
          <div className="flex items-center gap-3">
            <Sparkles className="text-amber-300" size={28} />
            <div>
              <h1 className="text-2xl font-bold" style={{ color: '#2d2a26' }}>Mosaic Mind</h1>
              <p className="text-sm mt-1" style={{ color: '#8a8279' }}>Build clarity from fragments</p>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 && (
            <div className="text-center mt-20">
              <div className="text-6xl mb-4">✨</div>
              <p className="text-lg font-medium mb-2" style={{ color: '#4a453e' }}>Enter with fragments</p>
              <p className="text-sm max-w-xs mx-auto leading-relaxed" style={{ color: '#8a8279' }}>
                Ask a question. Watch ideas refract and snap into place. Each response becomes a tile in your mosaic.
              </p>
              <p className="text-xs mt-4" style={{ color: '#b0a99f' }}>Try: "Should I start my own business?"</p>
            </div>
          )}

          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className="max-w-xs lg:max-w-md px-4 py-3 rounded-2xl"
                style={
                  message.role === 'user'
                    ? { background: 'linear-gradient(135deg, #c8d8f0 0%, #d8c8e8 100%)', color: '#2d2a26' }
                    : { background: '#ffffff', color: '#4a453e', border: '1px solid #e8e2da' }
                }
              >
                {message.content}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="px-4 py-3 rounded-2xl" style={{ background: '#ffffff', border: '1px solid #e8e2da' }}>
                <div className="flex gap-1">
                  <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: '#e8c8a0' }}></div>
                  <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: '#a0c0e8', animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: '#c8a0d8', animationDelay: '0.2s' }}></div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 border-t" style={{ borderColor: '#e8e2da', background: '#faf8f5' }}>
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              placeholder="Add a fragment..."
              className="flex-1 px-4 py-3 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-200"
              style={{ background: '#ffffff', border: '1px solid #e0d8cf', color: '#2d2a26' }}
              disabled={loading}
            />
            <button
              onClick={handleSendMessage}
              disabled={loading || !input.trim()}
              className="px-6 py-3 rounded-xl disabled:opacity-40 disabled:cursor-not-allowed transition-all hover:opacity-90"
              style={{ background: 'linear-gradient(135deg, #c8d8f0 0%, #d8c8e8 50%, #f0d8c8 100%)', color: '#4a453e' }}
            >
              <Send size={20} />
            </button>
          </div>
        </div>
      </div>

      {/* Mosaic Visualization Panel */}
      <div className="w-3/5 flex flex-col relative overflow-hidden" style={{ background: '#f0ece6' }}>
        <div className="absolute inset-0 opacity-30">
          <div className="absolute inset-0" style={{
            backgroundImage: 'radial-gradient(circle at 2px 2px, rgba(180,170,155,0.15) 1px, transparent 0)',
            backgroundSize: '40px 40px'
          }}></div>
        </div>

        {/* Decorative floating orbs like the hackathon site */}
        <div className="absolute -top-20 -left-20 w-64 h-64 rounded-full opacity-20" style={{ background: 'radial-gradient(circle, #f0e8ff 0%, transparent 70%)' }}></div>
        <div className="absolute top-1/3 -right-10 w-48 h-48 rounded-full opacity-15" style={{ background: 'radial-gradient(circle, #e0f0ff 0%, transparent 70%)' }}></div>
        <div className="absolute bottom-20 left-1/4 w-56 h-56 rounded-full opacity-15" style={{ background: 'radial-gradient(circle, #fff0e0 0%, transparent 70%)' }}></div>

        <div className="p-6 border-b backdrop-blur-sm relative z-10" style={{ borderColor: '#e0d8cf', background: 'rgba(245, 242, 238, 0.8)' }}>
          <h2 className="text-xl font-bold" style={{ color: '#2d2a26' }}>The Mosaic</h2>
          <p className="text-sm mt-1" style={{ color: '#8a8279' }}>
            {tiles.length === 0
              ? "Floating tiles will appear here"
              : `${tiles.length} fragments collected`}
          </p>
        </div>

        <div className="flex-1 overflow-auto relative">
          {tiles.length === 0 ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="text-7xl mb-4">🧩</div>
                <p className="text-lg" style={{ color: '#8a8279' }}>Nothing arrives whole</p>
                <p className="text-sm mt-2" style={{ color: '#b0a99f' }}>Everything begins as a piece</p>
              </div>
            </div>
          ) : (
            <div className="relative min-h-full" style={{ minWidth: '1200px', minHeight: '1200px' }}>
              <svg className="absolute inset-0 w-full h-full pointer-events-none">
                {connections.map(conn => (
                  <ConnectionLine key={conn.id} connection={conn} />
                ))}
              </svg>

              {tiles.map(tile => (
                <MosaicTile key={tile.id} tile={tile} />
              ))}
            </div>
          )}
        </div>

        {tiles.length > 0 && (
          <div className="p-4 backdrop-blur-sm border-t text-center relative z-10" style={{ borderColor: '#e0d8cf', background: 'rgba(245, 242, 238, 0.8)' }}>
            <p className="text-sm italic" style={{ color: '#8a8279' }}>
              "Every insight becomes a tile, every response a new color"
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default DecisionTreeApp;
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, MessageSquare, Copy, Check } from 'lucide-react';

interface WeChatModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const WeChatModal: React.FC<WeChatModalProps> = ({ isOpen, onClose }) => {
  const [copied, setCopied] = useState(false);
  const wechatId = "drawf890";

  const handleCopy = () => {
    navigator.clipboard.writeText(wechatId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm"
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            onClick={(e) => e.stopPropagation()}
            className="bg-navy rounded-2xl shadow-2xl max-w-sm w-full p-8 relative border-2 border-yellow"
          >
            <button
              onClick={onClose}
              className="absolute top-4 right-4 text-gray-400 hover:text-yellow transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
            
            <div className="text-center">
              <div className="w-16 h-16 bg-green-500/10 rounded-full flex items-center justify-center mx-auto mb-6 border border-green-500/20">
                <MessageSquare className="w-8 h-8 text-green-500" />
              </div>
              
              <h2 className="text-2xl font-bold text-white mb-2">Connect on WeChat</h2>
              <p className="text-gray-300 mb-8 leading-relaxed">
                Add Andrew on WeChat for direct support using the ID below.
              </p>
              
              <div className="bg-navy-light p-4 rounded-xl mb-8 border border-white/10 flex items-center justify-between">
                <span className="text-xl font-mono text-yellow font-bold tracking-wider">{wechatId}</span>
                <button 
                  onClick={handleCopy}
                  className="p-2 hover:bg-white/10 rounded-lg transition-colors text-gray-400 hover:text-white"
                  title="Copy ID"
                >
                  {copied ? <Check className="w-5 h-5 text-green-500" /> : <Copy className="w-5 h-5" />}
                </button>
              </div>

              <button 
                onClick={onClose}
                className="block w-full py-4 bg-green-600 text-white font-bold rounded-xl hover:bg-green-500 transition-colors shadow-lg shadow-green-900/20"
              >
                Done
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default WeChatModal;
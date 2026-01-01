import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText, ExternalLink, UserPlus, MessageCircle, X, Copy, Check } from 'lucide-react';
import { courseLinks } from '../data/links';

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
};

const item = {
  hidden: { y: 20, opacity: 0 },
  show: { y: 0, opacity: 1 }
};

const CourseContentLinks: React.FC = () => {
  const [showWeChatModal, setShowWeChatModal] = useState(false);
  const [copied, setCopied] = useState(false);
  const weChatId = 'drawf890';

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(weChatId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // Function to get the appropriate icon based on link title
  const getIcon = (title: string) => {
    if (title.toLowerCase().includes('syllabus') || title.toLowerCase().includes('course')) {
      return <FileText className="w-6 h-6 text-navy" />;
    } else if (title.toLowerCase().includes('register')) {
      return <UserPlus className="w-6 h-6 text-navy" />;
    } else if (title.toLowerCase().includes('wechat')) {
      return <MessageCircle className="w-6 h-6 text-navy" />;
    }
    // Default icon
    return <FileText className="w-6 h-6 text-navy" />;
  };

  return (
    <div className="w-full bg-navy-light py-16 px-4" id="content">
      <div className="container mx-auto">
        <div className="text-center mb-12">
          <motion.h2 
            initial={{ opacity: 0, y: -20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-3xl font-bold text-yellow mb-4"
          >
            Course Content
          </motion.h2>
          <motion.p 
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-gray-300 max-w-2xl mx-auto"
          >
            Access all your course materials, assignments, and resources here. 
            New content will be added weekly.
          </motion.p>
        </div>

        <motion.div 
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {courseLinks.map((link) => {
            const isWeChat = link.title.toLowerCase().includes('wechat');
            
            if (isWeChat) {
              return (
                <motion.button
                  key={link.id}
                  variants={item}
                  whileHover={{ scale: 1.03, y: -5 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => setShowWeChatModal(true)}
                  className="group bg-navy p-6 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 border-2 border-transparent hover:border-yellow block w-full text-left"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="p-3 bg-yellow rounded-lg">
                      {getIcon(link.title)}
                    </div>
                    <MessageCircle className="w-4 h-4 text-gray-400 group-hover:text-yellow transition-colors" />
                  </div>
                  
                  <h3 className="text-xl font-bold text-white mb-2 group-hover:text-yellow transition-colors">
                    {link.title}
                  </h3>
                  
                  {link.description && (
                    <p className="text-gray-400 text-sm">
                      {link.description}
                    </p>
                  )}
                </motion.button>
              );
            }
            
            return (
              <motion.a 
                key={link.id}
                variants={item}
                whileHover={{ scale: 1.03, y: -5 }}
                whileTap={{ scale: 0.98 }}
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group bg-navy p-6 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 border-2 border-transparent hover:border-yellow block"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="p-3 bg-yellow rounded-lg">
                    {getIcon(link.title)}
                  </div>
                  <ExternalLink className="w-4 h-4 text-gray-400 group-hover:text-yellow transition-colors" />
                </div>
                
                <h3 className="text-xl font-bold text-white mb-2 group-hover:text-yellow transition-colors">
                  {link.title}
                </h3>
                
                {link.description && (
                  <p className="text-gray-400 text-sm">
                    {link.description}
                  </p>
                )}
              </motion.a>
            );
          })}
        </motion.div>

        {/* WeChat Modal */}
        <AnimatePresence>
          {showWeChatModal && (
            <>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setShowWeChatModal(false)}
                className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
              >
                <motion.div
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0.9, opacity: 0 }}
                  onClick={(e) => e.stopPropagation()}
                  className="bg-navy rounded-xl shadow-2xl max-w-md w-full p-6 relative border-2 border-yellow"
                >
                  <button
                    onClick={() => setShowWeChatModal(false)}
                    className="absolute top-4 right-4 text-gray-300 hover:text-yellow transition-colors"
                  >
                    <X className="w-6 h-6" />
                  </button>
                  <div className="text-center">
                    <div className="w-16 h-16 bg-yellow rounded-full flex items-center justify-center mx-auto mb-4">
                      <MessageCircle className="w-8 h-8 text-navy" />
                    </div>
                    <h2 className="text-2xl font-bold text-yellow mb-2">Add Andrew on WeChat</h2>
                    <p className="text-gray-300 mb-4">
                      You can add Andrew on WeChat with this ID:
                    </p>
                    <div
                      onClick={handleCopy}
                      className="bg-navy-light rounded-lg p-4 mb-4 cursor-pointer hover:bg-navy-light/80 transition-colors group border-2 border-yellow/30 hover:border-yellow"
                    >
                      <div className="flex items-center justify-center gap-3">
                        <code className="text-yellow text-xl font-mono font-bold select-all">
                          {weChatId}
                        </code>
                        {copied ? (
                          <Check className="w-5 h-5 text-green-400" />
                        ) : (
                          <Copy className="w-5 h-5 text-gray-400 group-hover:text-yellow transition-colors" />
                        )}
                      </div>
                      <p className="text-gray-300 text-sm mt-2">
                        {copied ? 'Copied!' : 'Click to copy'}
                      </p>
                    </div>
                  </div>
                </motion.div>
              </motion.div>
            </>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default CourseContentLinks;

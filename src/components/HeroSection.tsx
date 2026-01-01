import React from 'react';
import { motion } from 'framer-motion';
import frontImage from '../assets/front.png';
import andrewImage from '../assets/andrew.png';

const HeroSection: React.FC = () => {
  return (
    <div className="w-full bg-navy relative">
      {/* Banner Image - full width, touching sides */}
      <div className="w-full relative">
        <motion.img 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1 }}
          src={frontImage} 
          alt="Gemini 3 Masterclass Banner" 
          className="w-full h-auto object-cover min-h-[500px] max-h-[75vh]"
        />
        
        {/* Overlay Content in the "Blue Area" (Left side) */}
        <div className="absolute inset-0 flex items-center">
          <div className="container mx-auto px-4">
            <div className="w-full md:w-[45%] lg:w-[40%] flex flex-col gap-6 pl-4 md:pl-8 lg:pl-12">
              
              {/* Instructor Profile */}
              <motion.div 
                initial={{ x: -50, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ duration: 0.8, delay: 0.2 }}
                className="flex flex-col gap-4"
              >
                <div className="flex items-center gap-4">
                  <div className="relative shrink-0">
                    <motion.div 
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: "spring", stiffness: 260, damping: 20, delay: 0.5 }}
                      className="absolute inset-0 bg-yellow rounded-full transform translate-x-1 translate-y-1"
                    ></motion.div>
                    <img 
                      src={andrewImage} 
                      alt="Andrew - Co-founder and CEO of Azure Partners" 
                      className="relative w-24 h-24 md:w-32 md:h-32 object-cover rounded-full border-2 border-white shadow-xl"
                    />
                  </div>
                  <div>
                    <h3 className="text-xl md:text-2xl font-bold text-white">Andrew</h3>
                    <p className="text-yellow font-medium text-sm md:text-base leading-tight">Co-founder & CEO,<br/>Azure Partners</p>
                  </div>
                </div>
                
                {/* Bio & Course Info */}
                <motion.div 
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.8, delay: 0.6 }}
                  className="text-white/90 space-y-4"
                >
                  <p className="text-sm md:text-base leading-relaxed font-light text-gray-200">
                    Co-founder and CEO of Azure Partners, an AI strategist and author with experience at Amazon, IBM, and multiple startups. Currently leads the AI Mastery program at Columbia University and advises global startups on AI innovation, education, and go-to-market strategy.
                  </p>
                  
                  <div className="border-l-2 border-yellow pl-4 py-1">
                    <p className="text-sm md:text-base font-medium text-white leading-snug">
                      Master the full capabilities of <span className="text-yellow">Gemini 3 Pro</span>, <span className="text-yellow">NotebookLM</span>, and <span className="text-yellow">Antigravity</span>. Learn to build logical reasoning paths, summarize hundreds of documents instantly, and use AI agents to create websites and dashboards for you.
                    </p>
                  </div>
                </motion.div>
              </motion.div>

            </div>
          </div>
        </div>
      </div>
      
      {/* Yellow accent line at bottom of hero */}
      <div className="w-full h-2 bg-yellow"></div>
    </div>
  );
};

export default HeroSection;

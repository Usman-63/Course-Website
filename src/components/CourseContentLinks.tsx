import React from 'react';
import { motion } from 'framer-motion';
import { FileText, ExternalLink } from 'lucide-react';
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
          {courseLinks.map((link) => (
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
                  <FileText className="w-6 h-6 text-navy" />
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
          ))}
        </motion.div>
      </div>
    </div>
  );
};

export default CourseContentLinks;

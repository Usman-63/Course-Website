import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { FileText, ExternalLink, Calendar, Loader2 } from 'lucide-react';
import { getCourseData, CourseModule, CourseLink } from '../services/api';

const Syllabus: React.FC = () => {
  const [modules, setModules] = useState<CourseModule[]>([]);
  const [links, setLinks] = useState<CourseLink[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await getCourseData();
        setModules(data.modules || []);
        // Filter out WeChat link as it's now handled via the popup in other locations
        const filteredLinks = (data.links || []).filter(link => 
          link.iconType !== 'wechat' && link.title.toLowerCase() !== 'wechat'
        );
        setLinks(filteredLinks);
      } catch (error) {
        console.error('Failed to fetch course data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-navy flex items-center justify-center pt-20">
        <Loader2 className="w-12 h-12 text-yellow animate-spin" />
      </div>
    );
  }

  return (
    <div className="pt-20 pb-24">
      <div className="container mx-auto px-4 md:px-6">
        {/* Header */}
          <div className="text-center mb-16 pt-10">
            <h1 className="text-4xl md:text-6xl font-bold text-white mb-6">Course Curriculum</h1>
            <p className="text-xl text-gray-400 max-w-2xl mx-auto">
              As your instructor for the Gemini 3 Masterclass, Andrew bridges the gap between cutting-edge AI research and real world application, providing students with the strategic framework and technical insight needed to master the next generation of AI.
            </p>
          </div>


        {/* Timeline / Modules */}
        <div className="max-w-4xl mx-auto space-y-12 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-white/10 before:to-transparent">
          {modules.sort((a, b) => (a.order || 0) - (b.order || 0)).map((week, index) => (
            <motion.div 
              key={week.id}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ delay: index * 0.1 }}
              className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active"
            >
              {/* Icon */}
              <div className="flex items-center justify-center w-10 h-10 rounded-full border border-white/10 bg-navy shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10 group-hover:border-yellow transition-colors">
                <span className="text-yellow font-bold text-sm">{index + 1}</span>
              </div>
              
              {/* Content Card */}
              <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] bg-navy-light p-6 md:p-8 rounded-2xl border border-white/5 hover:border-yellow/30 transition-all shadow-xl">
                <div className="flex items-center justify-between mb-4">
                  <span className="inline-block px-3 py-1 bg-white/5 rounded-full text-xs font-medium text-gray-400">
                    Week {index + 1}
                  </span>
                  <div className="flex gap-2">
                    <Calendar className="w-4 h-4 text-gray-500" />
                  </div>
                </div>
                <h3 className="text-2xl font-bold text-white mb-3">{week.title}</h3>
                <p className="text-gray-400 mb-6 text-sm md:text-base">Focus: {week.focus}</p>
                
                <ul className="space-y-3">
                  {week.topics.map((topic, i) => (
                    <li key={i} className="flex items-start gap-3 text-sm text-gray-300">
                      <div className="mt-1 w-1.5 h-1.5 rounded-full bg-yellow shrink-0"></div>
                      {topic}
                    </li>
                  ))}
                </ul>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Resources Section */}
        <div className="mt-32">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-white mb-4">Student Resources</h2>
            <p className="text-gray-400">Additional resources and links will be available here soon.</p>
          </div>
          
          {links.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {links.sort((a, b) => (a.order || 0) - (b.order || 0)).map((link) => (
                <a 
                  key={link.id}
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group bg-navy-light p-6 rounded-xl border border-white/5 hover:border-yellow/50 transition-all hover:bg-navy-light/80"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="p-3 bg-navy rounded-lg border border-white/5 group-hover:bg-yellow group-hover:text-navy transition-colors text-yellow">
                      <FileText className="w-6 h-6" />
                    </div>
                    <ExternalLink className="w-4 h-4 text-gray-500 group-hover:text-yellow transition-colors" />
                  </div>
                  <h3 className="text-lg font-bold text-white mb-2">{link.title}</h3>
                  <p className="text-sm text-gray-400">{link.description}</p>
                </a>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="bg-navy-light p-6 rounded-xl border border-white/5 border-dashed opacity-50"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="p-3 bg-navy rounded-lg border border-white/5 text-gray-500">
                      <FileText className="w-6 h-6" />
                    </div>
                    <ExternalLink className="w-4 h-4 text-gray-500" />
                  </div>
                  <h3 className="text-lg font-bold text-gray-500 mb-2">Resource {i}</h3>
                  <p className="text-sm text-gray-600">Coming soon</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Syllabus;
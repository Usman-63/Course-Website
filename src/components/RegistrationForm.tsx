import React from 'react';
import { motion } from 'framer-motion';
import { ExternalLink } from 'lucide-react';

const RegistrationForm: React.FC = () => {
  return (
    <div className="w-full bg-navy py-12" id="registration">
      <div className="container mx-auto px-4">
        <div className="text-center mb-12">
          <motion.h2 
            initial={{ opacity: 0, y: -20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-4xl font-bold text-yellow mb-4"
          >
            Register Now
          </motion.h2>
          <motion.p 
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-gray-300 text-lg max-w-2xl mx-auto"
          >
            Ready to join? Click the button below to open the secure registration form.
          </motion.p>
        </div>
        
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="flex justify-center"
        >
          <a 
            href="https://docs.google.com/forms/d/e/1FAIpQLSe3WKayEEbdwZNox_w5rOFrPcCEhMvzHLcPHbz-SzYDSMWFcw/viewform"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center px-8 py-5 bg-yellow text-navy font-bold text-xl rounded-xl hover:bg-yellow-hover transition-all transform hover:scale-105 shadow-xl shadow-yellow/20 gap-3"
          >
            Open Registration Form
            <ExternalLink className="w-6 h-6" />
          </a>
        </motion.div>
        
        <div className="text-center mt-8">
          <p className="text-gray-500 text-sm">
            Powered by Google Forms. Secure submission.
          </p>
        </div>
      </div>
    </div>
  );
};

export default RegistrationForm;

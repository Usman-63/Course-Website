import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';

const RegistrationForm: React.FC = () => {
  const [isLoading, setIsLoading] = useState(true);

  return (
    <div className="w-full bg-navy py-20" id="registration">
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
            Secure your spot in the masterclass. Choose your program tier and payment method below.
          </motion.p>
        </div>
        
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="w-full max-w-3xl mx-auto bg-navy rounded-xl overflow-hidden shadow-2xl border border-navy-light/50 relative min-h-[600px]"
        >
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-navy z-10">
              <Loader2 className="w-12 h-12 text-yellow animate-spin" />
            </div>
          )}
          
          <div className="bg-navy w-full h-full relative">
            <iframe 
              src="https://docs.google.com/forms/d/e/1FAIpQLSe3WKayEEbdwZNox_w5rOFrPcCEhMvzHLcPHbz-SzYDSMWFcw/viewform?embedded=true" 
              width="100%" 
              height="1600" 
              frameBorder="0" 
              marginHeight={0} 
              marginWidth={0}
              onLoad={() => setIsLoading(false)}
              className="w-full bg-transparent filter invert hue-rotate-180 mix-blend-screen opacity-[0.93]"
              title="Registration Form"
            >
              Loading…
            </iframe>
          </div>
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

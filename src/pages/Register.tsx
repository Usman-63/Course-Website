import React, { useEffect, useState } from 'react';
import RegistrationForm from '../components/RegistrationForm';
import { Check, Loader2 } from 'lucide-react';
import { getCourseData } from '../services/api';

interface PricingTier {
  name: string;
  price: number;
  key: string;
  features?: string[];
}

const Register: React.FC = () => {
  const [pricingTiers, setPricingTiers] = useState<PricingTier[]>([]);
  const [schedule, setSchedule] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPricing = async () => {
      try {
        const data = await getCourseData();
        const pricing = data.metadata?.pricing || {};
        setSchedule(data.metadata?.schedule || '');
        
        // Convert pricing object to array of tiers
        const tiers: PricingTier[] = Object.entries(pricing).map(([key, value]) => {
          // Handle legacy format (standard/student as numbers)
          if (typeof value === 'number') {
            const tierName = key === 'standard' ? 'Standard' : key === 'student' ? 'Student' : key;
            return {
              name: tierName,
              price: value,
              key,
              features: []
            };
          }
          
          // Handle new format (object with name, price, and features)
          return {
            name: value.name || key,
            price: value.price || 0,
            key,
            features: value.features || []
          };
        });
        
        // Sort by price (ascending) - lowest price first
        tiers.sort((a, b) => a.price - b.price);
        setPricingTiers(tiers);
      } catch (error) {
        console.error('Failed to fetch pricing:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchPricing();
  }, []);

  const scrollToForm = (e: React.MouseEvent) => {
    e.preventDefault();
    const element = document.getElementById('registration-form');
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="pt-24 pb-20">
      <div className="container mx-auto px-4">
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-6xl font-bold text-white mb-6">Choose Your Path</h1>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            Invest in your future with the most comprehensive AI masterclass available.
          </p>
        </div>

        {/* Schedule Information */}
        {schedule && (
          <div className="text-center mb-12">
            <p className="text-gray-400 text-sm max-w-2xl mx-auto">
              {schedule}
            </p>
          </div>
        )}

        {/* Pricing Cards */}
        {loading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="w-12 h-12 text-yellow animate-spin" />
          </div>
        ) : pricingTiers.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-gray-400 text-lg">Pricing information will be available soon.</p>
          </div>
        ) : (
          <div className={`grid grid-cols-1 ${pricingTiers.length === 1 ? 'md:grid-cols-1' : pricingTiers.length === 2 ? 'md:grid-cols-2' : 'md:grid-cols-3'} gap-8 max-w-6xl mx-auto mb-20`}>
            {pricingTiers.map((tier) => {
              return (
                <div
                  key={tier.key}
                  className="bg-navy-light border border-white/5 hover:border-yellow/50 rounded-3xl p-8 transition-all duration-300 relative overflow-hidden group hover:shadow-2xl hover:shadow-yellow/10"
                >
                  <div className="relative z-10">
                    <h3 className="text-xl font-medium text-gray-400 group-hover:text-yellow mb-2 transition-colors">
                      {tier.name}
                    </h3>
                    <div className="flex items-baseline gap-1 mb-6">
                      <span className="text-4xl font-bold text-white">${tier.price}</span>
                      <span className="text-gray-500">USD</span>
                    </div>
                    
                    {tier.features && tier.features.length > 0 && (
                      <ul className="space-y-4 mb-8">
                        {tier.features.map((feature, i) => (
                          <li key={i} className="flex items-center gap-3 text-gray-300">
                            <Check className="w-5 h-5 text-yellow shrink-0" />
                            <span>{feature}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                    
                    <button
                      onClick={scrollToForm}
                      className="block w-full py-4 bg-white/10 hover:bg-yellow hover:text-navy text-white font-bold text-center rounded-xl transition-all duration-300 group-hover:shadow-lg"
                    >
                      Select {tier.name}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Embedded Form */}
        <div id="registration-form" className="scroll-mt-32">
           <RegistrationForm />
        </div>
      </div>
    </div>
  );
};

export default Register;
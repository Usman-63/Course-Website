import React, { useState } from 'react';
import { Plus, Trash2, X, ChevronRight, ChevronDown } from 'lucide-react';
import { PricingTier } from '../services/api';

interface PricingTiersEditorProps {
  pricing: { [key: string]: number | PricingTier };
  onChange: (newPricing: { [key: string]: number | PricingTier }) => void;
}

const PricingTiersEditor: React.FC<PricingTiersEditorProps> = ({ pricing, onChange }) => {
  const [newTierKey, setNewTierKey] = useState('');
  const [expandedTiers, setExpandedTiers] = useState<Set<string>>(new Set(Object.keys(pricing)));

  const handleAddTier = () => {
    if (!newTierKey.trim()) return;
    const key = newTierKey.trim().toLowerCase().replace(/\s+/g, '_');
    
    if (pricing[key]) {
      alert('A tier with this ID already exists');
      return;
    }

    onChange({
      ...pricing,
      [key]: {
        name: newTierKey,
        price: 0,
        features: []
      }
    });
    setNewTierKey('');
    setExpandedTiers(prev => new Set(prev).add(key));
  };

  const handleRemoveTier = (key: string) => {
    if (!window.confirm('Are you sure you want to delete this pricing tier?')) return;
    const newPricing = { ...pricing };
    delete newPricing[key];
    onChange(newPricing);
  };

  const updateTier = (key: string, updates: Partial<PricingTier>) => {
    const current = pricing[key];
    // Convert number legacy format to object format if needed
    const currentObj: PricingTier = typeof current === 'number' 
      ? { name: key, price: current, features: [] }
      : current;

    onChange({
      ...pricing,
      [key]: { ...currentObj, ...updates }
    });
  };

  const toggleExpand = (key: string) => {
    setExpandedTiers(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const addFeature = (key: string) => {
    const current = pricing[key];
    const currentObj: PricingTier = typeof current === 'number' 
      ? { name: key, price: current, features: [] }
      : current;
    
    onChange({
      ...pricing,
      [key]: {
        ...currentObj,
        features: [...(currentObj.features || []), 'New Feature']
      }
    });
  };

  const updateFeature = (key: string, index: number, value: string) => {
    const current = pricing[key];
    const currentObj: PricingTier = typeof current === 'number' 
      ? { name: key, price: current, features: [] }
      : current;
      
    const newFeatures = [...(currentObj.features || [])];
    newFeatures[index] = value;

    onChange({
      ...pricing,
      [key]: { ...currentObj, features: newFeatures }
    });
  };

  const removeFeature = (key: string, index: number) => {
    const current = pricing[key];
    const currentObj: PricingTier = typeof current === 'number' 
      ? { name: key, price: current, features: [] }
      : current;
      
    const newFeatures = (currentObj.features || []).filter((_, i) => i !== index);

    onChange({
      ...pricing,
      [key]: { ...currentObj, features: newFeatures }
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h4 className="text-gray-900 font-bold text-base">Pricing Tiers</h4>
        <div className="flex gap-2">
          <input
            type="text"
            value={newTierKey}
            onChange={(e) => setNewTierKey(e.target.value)}
            placeholder="Tier Name (e.g. Pro)"
            className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-yellow"
          />
          <button
            onClick={handleAddTier}
            disabled={!newTierKey.trim()}
            className="bg-yellow text-navy px-3 py-1.5 rounded-md text-sm font-semibold hover:bg-yellow-hover disabled:opacity-50 flex items-center gap-1"
          >
            <Plus className="w-4 h-4" /> Add Tier
          </button>
        </div>
      </div>

      <div className="grid gap-4">
        {Object.entries(pricing).map(([key, value]) => {
          const tier: PricingTier = typeof value === 'number' 
            ? { name: key, price: value, features: [] }
            : value;
          const isExpanded = expandedTiers.has(key);

          return (
            <div key={key} className="bg-gray-50 rounded-lg border border-gray-200 overflow-hidden">
              {/* Header */}
              <div className="flex items-center justify-between p-3 bg-gray-100/50 cursor-pointer" onClick={() => toggleExpand(key)}>
                <div className="flex items-center gap-3">
                  {isExpanded ? <ChevronDown className="w-4 h-4 text-gray-500" /> : <ChevronRight className="w-4 h-4 text-gray-500" />}
                  <span className="font-semibold text-gray-900">{tier.name || key}</span>
                  <span className="text-sm text-gray-500 bg-white px-2 py-0.5 rounded border border-gray-200 font-mono">${tier.price}</span>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); handleRemoveTier(key); }}
                  className="p-1.5 text-red-500 hover:bg-red-50 rounded transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              {/* Body */}
              {isExpanded && (
                <div className="p-4 space-y-4 border-t border-gray-200 bg-white">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-gray-700 text-xs font-bold mb-1 uppercase">Display Name</label>
                      <input
                        type="text"
                        value={tier.name}
                        onChange={(e) => updateTier(key, { name: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-yellow focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-gray-700 text-xs font-bold mb-1 uppercase">Price ($)</label>
                      <input
                        type="number"
                        value={tier.price}
                        onChange={(e) => updateTier(key, { price: parseFloat(e.target.value) || 0 })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-yellow focus:outline-none"
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-2">
                        <label className="block text-gray-700 text-xs font-bold uppercase">Features</label>
                        <button 
                            onClick={() => addFeature(key)}
                            className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
                        >
                            <Plus className="w-3 h-3" /> Add Feature
                        </button>
                    </div>
                    <div className="space-y-2">
                        {(tier.features || []).map((feature, idx) => (
                            <div key={idx} className="flex gap-2">
                                <input
                                    type="text"
                                    value={feature}
                                    onChange={(e) => updateFeature(key, idx, e.target.value)}
                                    className="flex-1 px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-yellow focus:outline-none"
                                    placeholder="Feature description"
                                />
                                <button
                                    onClick={() => removeFeature(key, idx)}
                                    className="text-gray-400 hover:text-red-500 px-1"
                                >
                                    <X className="w-4 h-4" />
                                </button>
                            </div>
                        ))}
                        {(!tier.features || tier.features.length === 0) && (
                            <p className="text-xs text-gray-400 italic">No features listed.</p>
                        )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default PricingTiersEditor;
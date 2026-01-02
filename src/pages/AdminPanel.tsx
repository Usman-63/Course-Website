import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { LogOut, Loader2, Plus, X } from 'lucide-react';
import AdminLogin from '../components/AdminLogin';
import ModuleEditor from '../components/ModuleEditor';
import LinkEditor from '../components/LinkEditor';
import { 
  isAdminLoggedIn, 
  clearAuthToken, 
  getAdminData, 
  updateCourseData,
  CourseData 
} from '../services/api';

const AdminPanel: React.FC = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [courseData, setCourseData] = useState<CourseData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'modules' | 'links' | 'metadata'>('modules');

  useEffect(() => {
    if (isAdminLoggedIn()) {
      setIsAuthenticated(true);
      loadData();
    } else {
      setIsLoading(false);
    }
  }, []);

  const loadData = async () => {
    try {
      setIsLoading(true);
      const data = await getAdminData();
      setCourseData(data);
    } catch (error) {
      console.error('Failed to load data:', error);
      if (error instanceof Error && error.message === 'Authentication failed') {
        setIsAuthenticated(false);
        clearAuthToken();
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
    loadData();
  };

  const handleLogout = () => {
    clearAuthToken();
    setIsAuthenticated(false);
    setCourseData(null);
  };


  const handleSaveMetadata = async () => {
    if (!courseData) return;
    
    try {
      setIsLoading(true);
      await updateCourseData(courseData);
      alert('Metadata saved successfully!');
    } catch (error) {
      console.error('Failed to save metadata:', error);
      alert('Failed to save metadata');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isAuthenticated) {
    return <AdminLogin onLoginSuccess={handleLoginSuccess} />;
  }

  if (isLoading && !courseData) {
    return (
      <div className="min-h-screen bg-navy flex items-center justify-center">
        <Loader2 className="w-12 h-12 text-yellow animate-spin" />
      </div>
    );
  }

  if (!courseData) {
    return (
      <div className="min-h-screen bg-navy flex items-center justify-center">
        <p className="text-yellow">Failed to load course data</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-navy py-8 px-4">
      <div className="container mx-auto max-w-6xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-4xl font-bold text-yellow">Admin Panel</h1>
          <button
            onClick={handleLogout}
            className="bg-red-500 text-white px-4 py-2 rounded-lg font-semibold flex items-center gap-2 hover:bg-red-600 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-yellow/30">
          <button
            onClick={() => setActiveTab('modules')}
            className={`px-6 py-3 font-semibold transition-colors ${
              activeTab === 'modules'
                ? 'text-yellow border-b-2 border-yellow'
                : 'text-gray-400 hover:text-yellow'
            }`}
          >
            Modules
          </button>
          <button
            onClick={() => setActiveTab('links')}
            className={`px-6 py-3 font-semibold transition-colors ${
              activeTab === 'links'
                ? 'text-yellow border-b-2 border-yellow'
                : 'text-gray-400 hover:text-yellow'
            }`}
          >
            Links
          </button>
          <button
            onClick={() => setActiveTab('metadata')}
            className={`px-6 py-3 font-semibold transition-colors ${
              activeTab === 'metadata'
                ? 'text-yellow border-b-2 border-yellow'
                : 'text-gray-400 hover:text-yellow'
            }`}
          >
            Metadata
          </button>
        </div>

        {/* Content */}
        <div className="bg-navy-light rounded-xl p-6 border-2 border-yellow/30">
          {activeTab === 'modules' && (
            <ModuleEditor
              modules={courseData.modules}
              onUpdate={loadData}
            />
          )}

          {activeTab === 'links' && (
            <LinkEditor
              links={courseData.links}
              onUpdate={loadData}
            />
          )}

          {activeTab === 'metadata' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-bold text-yellow">Course Information</h3>
                <button
                  onClick={handleSaveMetadata}
                  disabled={isLoading}
                  className="bg-yellow text-navy px-4 py-2 rounded-lg font-semibold hover:bg-yellow/90 transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                  <Loader2 className={`w-4 h-4 ${isLoading ? 'animate-spin' : 'hidden'}`} />
                  Save Changes
                </button>
              </div>

              <div className="space-y-6">
                <div>
                  <label className="block text-yellow font-semibold mb-2">Schedule Information</label>
                  <input
                    type="text"
                    value={courseData.metadata.schedule || ''}
                    onChange={(e) => setCourseData({
                      ...courseData,
                      metadata: { ...courseData.metadata, schedule: e.target.value }
                    })}
                    className="w-full px-4 py-2 bg-navy border border-navy-light/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-yellow"
                    placeholder="e.g., Fridays (6 PM – 8 PM: Theory) + Weekends (3 Hours: Collaborative Lab)"
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-4">
                    <label className="block text-yellow font-semibold">Pricing Tiers</label>
                    <button
                      onClick={() => {
                        const pricing = courseData.metadata.pricing || {};
                        const newKey = `tier_${Object.keys(pricing).length + 1}`;
                        setCourseData({
                          ...courseData,
                          metadata: {
                            ...courseData.metadata,
                            pricing: {
                              ...pricing,
                              [newKey]: { name: 'New Tier', price: 0, features: [] }
                            }
                          }
                        });
                      }}
                      className="bg-yellow text-navy px-3 py-1 rounded-lg font-semibold text-sm hover:bg-yellow/90 transition-colors flex items-center gap-1"
                    >
                      <Plus className="w-4 h-4" />
                      Add Tier
                    </button>
                  </div>
                  
                  <div className="space-y-3">
                    {Object.entries(courseData.metadata.pricing || {}).map(([key, value]: [string, any]) => {
                      // Handle legacy format (standard/student as numbers)
                      if (typeof value === 'number') {
                        const tierName = key === 'standard' ? 'Standard' : key === 'student' ? 'Student' : key;
                        return (
                          <div key={key} className="bg-navy-light p-4 rounded-lg space-y-3">
                            <div className="flex gap-3 items-center">
                              <input
                                type="text"
                                value={tierName}
                                onChange={(e) => {
                                  const pricing = { ...courseData.metadata.pricing };
                                  const oldValue = pricing[key];
                                  delete pricing[key];
                                  // Convert to new format if it's still a number
                                  const newValue = typeof oldValue === 'number' 
                                    ? { name: e.target.value, price: oldValue, features: [] }
                                    : { ...oldValue, name: e.target.value };
                                  pricing[e.target.value.toLowerCase().replace(/\s+/g, '_')] = newValue;
                                  setCourseData({
                                    ...courseData,
                                    metadata: {
                                      ...courseData.metadata,
                                      pricing
                                    }
                                  });
                                }}
                                className="flex-1 px-3 py-2 bg-navy border border-navy-light/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-yellow"
                                placeholder="Tier name"
                              />
                              <span className="text-gray-400">$</span>
                              <input
                                type="number"
                                value={value}
                                onChange={(e) => {
                                  const pricing = { ...courseData.metadata.pricing };
                                  // Convert to new format if it's still a number
                                  pricing[key] = typeof value === 'number'
                                    ? { name: tierName, price: parseFloat(e.target.value) || 0, features: [] }
                                    : { ...value, price: parseFloat(e.target.value) || 0 };
                                  setCourseData({
                                    ...courseData,
                                    metadata: {
                                      ...courseData.metadata,
                                      pricing
                                    }
                                  });
                                }}
                                className="w-32 px-3 py-2 bg-navy border border-navy-light/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-yellow"
                                placeholder="0.00"
                              />
                              <button
                                onClick={() => {
                                  const pricing = { ...courseData.metadata.pricing };
                                  delete pricing[key];
                                  setCourseData({
                                    ...courseData,
                                    metadata: {
                                      ...courseData.metadata,
                                      pricing
                                    }
                                  });
                                }}
                                className="text-red-400 hover:text-red-300 p-2"
                                title="Remove tier"
                              >
                                <X className="w-4 h-4" />
                              </button>
                            </div>
                            <div>
                              <label className="block text-gray-400 text-sm mb-2">Features (one per line)</label>
                              <textarea
                                value=""
                                onChange={(e) => {
                                  const features = e.target.value.split('\n').filter(f => f.trim());
                                  const pricing = { ...courseData.metadata.pricing };
                                  // Convert from legacy number format to new object format
                                  pricing[key] = { name: tierName, price: value, features };
                                  setCourseData({
                                    ...courseData,
                                    metadata: {
                                      ...courseData.metadata,
                                      pricing
                                    }
                                  });
                                }}
                                className="w-full px-3 py-2 bg-navy border border-navy-light/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-yellow text-sm"
                                placeholder="Full Access to Live Sessions&#10;Lifetime Recording Access&#10;Private Community Access"
                                rows={4}
                              />
                            </div>
                          </div>
                        );
                      }
                      
                      // Handle new format (object with name, price, and features)
                      const features = value.features || [];
                      const featuresText = features.join('\n');
                      
                      return (
                        <div key={key} className="bg-navy-light p-4 rounded-lg space-y-3">
                          <div className="flex gap-3 items-center">
                            <input
                              type="text"
                              value={value.name || ''}
                              onChange={(e) => {
                                const pricing = { ...courseData.metadata.pricing };
                                pricing[key] = { ...value, name: e.target.value };
                                setCourseData({
                                  ...courseData,
                                  metadata: {
                                    ...courseData.metadata,
                                    pricing
                                  }
                                });
                              }}
                              className="flex-1 px-3 py-2 bg-navy border border-navy-light/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-yellow"
                              placeholder="Tier name (e.g., Standard, Student, Early Bird)"
                            />
                            <span className="text-gray-400">$</span>
                            <input
                              type="number"
                              value={value.price || 0}
                              onChange={(e) => {
                                const pricing = { ...courseData.metadata.pricing };
                                pricing[key] = { ...value, price: parseFloat(e.target.value) || 0 };
                                setCourseData({
                                  ...courseData,
                                  metadata: {
                                    ...courseData.metadata,
                                    pricing
                                  }
                                });
                              }}
                              className="w-32 px-3 py-2 bg-navy border border-navy-light/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-yellow"
                              placeholder="0.00"
                            />
                            <button
                              onClick={() => {
                                const pricing = { ...courseData.metadata.pricing };
                                delete pricing[key];
                                setCourseData({
                                  ...courseData,
                                  metadata: {
                                    ...courseData.metadata,
                                    pricing
                                  }
                                });
                              }}
                              className="text-red-400 hover:text-red-300 p-2"
                              title="Remove tier"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                          <div>
                            <label className="block text-gray-400 text-sm mb-2">Features (one per line)</label>
                            <textarea
                              value={featuresText}
                              onChange={(e) => {
                                const newFeatures = e.target.value.split('\n').filter(f => f.trim());
                                const pricing = { ...courseData.metadata.pricing };
                                pricing[key] = { ...value, features: newFeatures };
                                setCourseData({
                                  ...courseData,
                                  metadata: {
                                    ...courseData.metadata,
                                    pricing
                                  }
                                });
                              }}
                              className="w-full px-3 py-2 bg-navy border border-navy-light/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-yellow text-sm"
                              placeholder="Full Access to Live Sessions&#10;Lifetime Recording Access&#10;Private Community Access"
                              rows={4}
                            />
                          </div>
                        </div>
                      );
                    })}
                    
                    {(!courseData.metadata.pricing || Object.keys(courseData.metadata.pricing).length === 0) && (
                      <p className="text-gray-400 text-sm text-center py-4">No pricing tiers added yet. Click "Add Tier" to create one.</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminPanel;


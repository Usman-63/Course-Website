import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Plus, Edit2, Trash2, X, Save, ChevronUp, ChevronDown } from 'lucide-react';
import { CourseModule, addModule, updateModule, deleteModule } from '../services/api';

interface ModuleEditorProps {
  modules: CourseModule[];
  onUpdate: () => void;
}

const ModuleEditor: React.FC<ModuleEditorProps> = ({ modules, onUpdate }) => {
  const [editingModule, setEditingModule] = useState<CourseModule | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState<Partial<CourseModule>>({
    title: '',
    hours: 0,
    focus: '',
    topics: [],
    order: modules.length + 1,
  });
  const [topicInput, setTopicInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleAddModule = async () => {
    setIsLoading(true);
    try {
      await addModule(formData as Omit<CourseModule, 'id'>);
      setShowAddForm(false);
      setFormData({ title: '', hours: 0, focus: '', topics: [], order: modules.length + 1 });
      onUpdate();
    } catch (error) {
      console.error('Failed to add module:', error);
      alert('Failed to add module');
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateModule = async () => {
    if (!editingModule) return;
    setIsLoading(true);
    try {
      await updateModule(editingModule.id, formData);
      setEditingModule(null);
      onUpdate();
    } catch (error) {
      console.error('Failed to update module:', error);
      alert('Failed to update module');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteModule = async (moduleId: string) => {
    if (!confirm('Are you sure you want to delete this module?')) return;
    setIsLoading(true);
    try {
      await deleteModule(moduleId);
      onUpdate();
    } catch (error) {
      console.error('Failed to delete module:', error);
      alert('Failed to delete module');
    } finally {
      setIsLoading(false);
    }
  };

  const addTopic = () => {
    if (topicInput.trim()) {
      setFormData({
        ...formData,
        topics: [...(formData.topics || []), topicInput.trim()],
      });
      setTopicInput('');
    }
  };

  const removeTopic = (index: number) => {
    setFormData({
      ...formData,
      topics: formData.topics?.filter((_, i) => i !== index),
    });
  };

  const moveTopicUp = (index: number) => {
    if (index === 0) return;
    const newTopics = [...(formData.topics || [])];
    [newTopics[index - 1], newTopics[index]] = [newTopics[index], newTopics[index - 1]];
    setFormData({
      ...formData,
      topics: newTopics,
    });
  };

  const moveTopicDown = (index: number) => {
    if (!formData.topics || index === formData.topics.length - 1) return;
    const newTopics = [...formData.topics];
    [newTopics[index], newTopics[index + 1]] = [newTopics[index + 1], newTopics[index]];
    setFormData({
      ...formData,
      topics: newTopics,
    });
  };

  const startEdit = (module: CourseModule) => {
    setEditingModule(module);
    setFormData(module);
    setShowAddForm(false);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xl font-bold text-yellow">Course Modules</h3>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => {
            setShowAddForm(true);
            setEditingModule(null);
            setFormData({ title: '', hours: 0, focus: '', topics: [], order: modules.length + 1 });
          }}
          className="bg-yellow text-navy px-4 py-2 rounded-lg font-semibold flex items-center gap-2 hover:bg-yellow/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Module
        </motion.button>
      </div>

      {(showAddForm || editingModule) && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-navy-light p-6 rounded-lg border-2 border-yellow/30"
        >
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-lg font-bold text-yellow">
              {editingModule ? 'Edit Module' : 'Add New Module'}
            </h4>
            <button
              onClick={() => {
                setShowAddForm(false);
                setEditingModule(null);
              }}
              className="text-gray-400 hover:text-yellow transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-yellow font-semibold mb-2">Title</label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className="w-full px-4 py-2 bg-navy border border-navy-light/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-yellow"
                placeholder="Module 1: Title"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-yellow font-semibold mb-2">Hours</label>
                <input
                  type="number"
                  value={formData.hours}
                  onChange={(e) => setFormData({ ...formData, hours: parseInt(e.target.value) || 0 })}
                  className="w-full px-4 py-2 bg-navy border border-navy-light/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-yellow"
                />
              </div>
              <div>
                <label className="block text-yellow font-semibold mb-2">Order</label>
                <input
                  type="number"
                  value={formData.order}
                  onChange={(e) => setFormData({ ...formData, order: parseInt(e.target.value) || 0 })}
                  className="w-full px-4 py-2 bg-navy border border-navy-light/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-yellow"
                />
              </div>
            </div>

            <div>
              <label className="block text-yellow font-semibold mb-2">Focus</label>
              <input
                type="text"
                value={formData.focus}
                onChange={(e) => setFormData({ ...formData, focus: e.target.value })}
                className="w-full px-4 py-2 bg-navy border border-navy-light/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-yellow"
                placeholder="Module focus description"
              />
            </div>

            <div>
              <label className="block text-yellow font-semibold mb-2">Topics</label>
              <div className="flex gap-2 mb-2">
                <input
                  type="text"
                  value={topicInput}
                  onChange={(e) => setTopicInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addTopic())}
                  className="flex-1 px-4 py-2 bg-navy border border-navy-light/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-yellow"
                  placeholder="Add a topic"
                />
                <button
                  type="button"
                  onClick={addTopic}
                  className="bg-yellow text-navy px-4 py-2 rounded-lg font-semibold hover:bg-yellow/90"
                >
                  Add
                </button>
              </div>
              <div className="space-y-2">
                {formData.topics?.map((topic, index) => (
                  <div key={index} className="flex items-center gap-2 bg-navy p-2 rounded">
                    <div className="flex flex-col gap-1">
                      <button
                        onClick={() => moveTopicUp(index)}
                        disabled={index === 0}
                        className="text-yellow hover:text-yellow/80 disabled:text-gray-600 disabled:cursor-not-allowed"
                        title="Move up"
                      >
                        <ChevronUp className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => moveTopicDown(index)}
                        disabled={index === (formData.topics?.length || 0) - 1}
                        className="text-yellow hover:text-yellow/80 disabled:text-gray-600 disabled:cursor-not-allowed"
                        title="Move down"
                      >
                        <ChevronDown className="w-4 h-4" />
                      </button>
                    </div>
                    <span className="flex-1 text-gray-300 text-sm">{topic}</span>
                    <button
                      onClick={() => removeTopic(index)}
                      className="text-red-400 hover:text-red-300"
                      title="Remove"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={editingModule ? handleUpdateModule : handleAddModule}
              disabled={isLoading}
              className="w-full bg-yellow text-navy font-bold py-3 rounded-lg hover:bg-yellow/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              <Save className="w-4 h-4" />
              {isLoading ? 'Saving...' : editingModule ? 'Update Module' : 'Add Module'}
            </button>
          </div>
        </motion.div>
      )}

      <div className="space-y-3">
        {modules.map((module) => (
          <motion.div
            key={module.id}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="bg-navy-light p-4 rounded-lg border border-yellow/20"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h4 className="text-yellow font-bold mb-1">{module.title}</h4>
                <p className="text-gray-300 text-sm mb-2">{module.focus}</p>
                <div className="flex gap-4 text-sm text-gray-400">
                  <span>Hours: {module.hours}</span>
                  <span>Order: {module.order}</span>
                </div>
                {module.topics.length > 0 && (
                  <div className="mt-2">
                    <p className="text-gray-400 text-xs mb-1">Topics:</p>
                    <ul className="list-disc list-inside text-gray-300 text-xs space-y-1">
                      {module.topics.slice(0, 3).map((topic, i) => (
                        <li key={i}>{topic}</li>
                      ))}
                      {module.topics.length > 3 && (
                        <li className="text-gray-500">+{module.topics.length - 3} more</li>
                      )}
                    </ul>
                  </div>
                )}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => startEdit(module)}
                  className="p-2 text-yellow hover:bg-yellow/20 rounded transition-colors"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleDeleteModule(module.id)}
                  className="p-2 text-red-400 hover:bg-red-400/20 rounded transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default ModuleEditor;


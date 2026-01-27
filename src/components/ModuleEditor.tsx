import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Plus, Edit2, Trash2, X, Save, ChevronUp, ChevronDown, Eye, EyeOff, Loader2 } from 'lucide-react';
import { CourseModule, addModule, updateModule, deleteModule } from '../services/api';
import { useToast } from './Toast';

interface ModuleEditorProps {
  modules: CourseModule[];
  courseId: string;
  onUpdate: () => void;
}

const ModuleEditor: React.FC<ModuleEditorProps> = ({ modules, courseId, onUpdate }) => {
  const toast = useToast();
  const [editingModule, setEditingModule] = useState<CourseModule | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState<Partial<CourseModule>>({
    title: '',
    hours: 0,
    focus: '',
    topics: [],
    order: modules.length + 1,
    labCount: 0,
    isVisible: true,
  });
  const [topicInput, setTopicInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [loadingModuleId, setLoadingModuleId] = useState<string | null>(null);

  const handleAddModule = async () => {
    setIsLoading(true);
    try {
      await addModule(formData as Omit<CourseModule, 'id'>, courseId);
      setShowAddForm(false);
      setFormData({ title: '', hours: 0, focus: '', topics: [], order: modules.length + 1, labCount: 0, isVisible: true });
      toast.success('Module added successfully');
      onUpdate();
    } catch (error) {
      console.error('Failed to add module:', error);
      const message = error instanceof Error ? error.message : 'Failed to add module';
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateModule = async () => {
    if (!editingModule) return;
    setIsLoading(true);
    try {
      await updateModule(editingModule.id, formData, courseId);
      setEditingModule(null);
      toast.success('Module updated successfully');
      onUpdate();
    } catch (error) {
      console.error('Failed to update module:', error);
      const message = error instanceof Error ? error.message : 'Failed to update module';
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteModule = async (moduleId: string) => {
    if (!window.confirm('Are you sure you want to delete this module?')) return;
    setLoadingModuleId(moduleId);
    try {
      await deleteModule(moduleId, courseId);
      toast.success('Module deleted successfully');
      onUpdate();
    } catch (error) {
      console.error('Failed to delete module:', error);
      toast.error('Failed to delete module');
    } finally {
      setLoadingModuleId(null);
    }
  };

  const toggleVisibility = async (module: CourseModule) => {
    setLoadingModuleId(module.id);
    try {
      await updateModule(module.id, { isVisible: !(module.isVisible !== false) }, courseId);
      onUpdate();
    } catch (error) {
        console.error('Failed to update visibility:', error);
      toast.error('Failed to update visibility');
    } finally {
        setLoadingModuleId(null);
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
        <h3 className="text-xl font-bold text-gray-900">Course Modules</h3>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => {
            setShowAddForm(true);
            setEditingModule(null);
            setFormData({ title: '', hours: 0, focus: '', topics: [], order: modules.length + 1, labCount: 0, isVisible: true });
          }}
          className="bg-yellow text-navy px-4 py-2 rounded-lg font-semibold flex items-center gap-2 hover:bg-yellow-hover transition-colors shadow-sm"
        >
          <Plus className="w-4 h-4" />
          Add Module
        </motion.button>
      </div>

      {(showAddForm || editingModule) && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm"
        >
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-lg font-bold text-gray-900">
              {editingModule ? 'Edit Module' : 'Add New Module'}
            </h4>
            <button
              onClick={() => {
                setShowAddForm(false);
                setEditingModule(null);
              }}
              className="text-gray-400 hover:text-gray-900 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-gray-700 font-semibold mb-2 text-sm">Title</label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-yellow"
                placeholder="Module 1: Title"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-gray-700 font-semibold mb-2 text-sm">Hours</label>
                <input
                  type="number"
                  value={formData.hours}
                  onChange={(e) => setFormData({ ...formData, hours: parseInt(e.target.value) || 0 })}
                  className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-yellow"
                />
              </div>
              <div>
                <label className="block text-gray-700 font-semibold mb-2 text-sm">Order</label>
                <input
                  type="number"
                  value={formData.order}
                  onChange={(e) => setFormData({ ...formData, order: parseInt(e.target.value) || 0 })}
                  className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-yellow"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
                <div>
                <label className="block text-gray-700 font-semibold mb-2 text-sm">Number of Labs</label>
                <input
                    type="number"
                    min="0"
                    value={formData.labCount ?? 0}
                    onChange={(e) => {
                      const value = e.target.value === '' ? 0 : parseInt(e.target.value, 10);
                      setFormData({ ...formData, labCount: Number.isNaN(value) ? 0 : value });
                    }}
                    className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-yellow"
                />
                </div>
                <div className="flex items-center pt-6">
                    <label className="flex items-center gap-2 cursor-pointer text-gray-700 font-semibold text-sm">
                        <input 
                            type="checkbox"
                            checked={formData.isVisible !== false}
                            onChange={(e) => setFormData({ ...formData, isVisible: e.target.checked })}
                            className="w-4 h-4 text-yellow-600 rounded border-gray-300 focus:ring-yellow"
                        />
                        Visible to Students
                    </label>
                </div>
            </div>

            <div>
              <label className="block text-gray-700 font-semibold mb-2 text-sm">Focus</label>
              <input
                type="text"
                value={formData.focus}
                onChange={(e) => setFormData({ ...formData, focus: e.target.value })}
                className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-yellow"
                placeholder="Module focus description"
              />
            </div>

            <div>
              <label className="block text-gray-700 font-semibold mb-2 text-sm">Video Link (Optional)</label>
              <input
                type="url"
                value={formData.videoLink || ''}
                onChange={(e) => setFormData({ ...formData, videoLink: e.target.value })}
                className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-yellow"
                placeholder="https://youtube.com/..."
              />
            </div>

            <div>
              <label className="block text-gray-700 font-semibold mb-2 text-sm">Lab Link (Optional)</label>
              <input
                type="url"
                value={formData.labLink || ''}
                onChange={(e) => setFormData({ ...formData, labLink: e.target.value })}
                className="w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-yellow"
                placeholder="https://drive.google.com/..."
              />
            </div>

            <div>
              <label className="block text-gray-700 font-semibold mb-2 text-sm">Topics</label>
              <div className="flex gap-2 mb-2">
                <input
                  type="text"
                  value={topicInput}
                  onChange={(e) => setTopicInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addTopic())}
                  className="flex-1 px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-yellow"
                  placeholder="Add a topic"
                />
                <button
                  type="button"
                  onClick={addTopic}
                  className="bg-yellow text-navy px-4 py-2 rounded-lg font-semibold hover:bg-yellow-hover transition-colors"
                >
                  Add
                </button>
              </div>
              <div className="space-y-2">
                {formData.topics?.map((topic, index) => (
                  <div key={index} className="flex items-center gap-2 bg-gray-50 p-2 rounded border border-gray-200">
                    <div className="flex flex-col gap-1">
                      <button
                        onClick={() => moveTopicUp(index)}
                        disabled={index === 0}
                        className="text-gray-400 hover:text-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
                        title="Move up"
                      >
                        <ChevronUp className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => moveTopicDown(index)}
                        disabled={index === (formData.topics?.length || 0) - 1}
                        className="text-gray-400 hover:text-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
                        title="Move down"
                      >
                        <ChevronDown className="w-4 h-4" />
                      </button>
                    </div>
                    <span className="flex-1 text-gray-700 text-sm">{topic}</span>
                    <button
                      onClick={() => removeTopic(index)}
                      className="text-red-400 hover:text-red-600"
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
              className="w-full bg-yellow text-navy font-bold py-3 rounded-lg hover:bg-yellow-hover transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
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
            className={`bg-white p-4 rounded-lg border shadow-sm transition-all ${
                module.isVisible === false ? 'border-gray-200 opacity-60 bg-gray-50' : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                    <h4 className="text-gray-900 font-bold">{module.title}</h4>
                    {module.isVisible === false && (
                        <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full flex items-center gap-1">
                            <EyeOff className="w-3 h-3" /> Hidden
                        </span>
                    )}
                </div>
                <p className="text-gray-500 text-sm mb-2">{module.focus}</p>
                <div className="flex gap-4 text-sm text-gray-500">
                  <span>Hours: {module.hours}</span>
                  <span>Order: {module.order}</span>
                </div>
                <div className="flex gap-2 mt-2">
                  {module.videoLink && (
                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded border border-blue-200">
                      📹 Video Linked
                    </span>
                  )}
                  {module.labLink && (
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded border border-green-200">
                      🧪 Lab Linked
                    </span>
                  )}
                </div>
                {module.topics.length > 0 && (
                  <div className="mt-2">
                    <p className="text-gray-500 text-xs mb-1">Topics:</p>
                    <ul className="list-disc list-inside text-gray-600 text-xs space-y-1">
                      {module.topics.slice(0, 3).map((topic, i) => (
                        <li key={i}>{topic}</li>
                      ))}
                      {module.topics.length > 3 && (
                        <li className="text-gray-400">+{module.topics.length - 3} more</li>
                      )}
                    </ul>
                  </div>
                )}
              </div>
              <div className="flex gap-2">
                <button
                    onClick={() => toggleVisibility(module)}
                    disabled={loadingModuleId === module.id}
                    className={`p-2 rounded transition-colors disabled:opacity-50 ${
                        module.isVisible === false 
                        ? 'text-gray-400 hover:bg-gray-100' 
                        : 'text-green-600 hover:bg-green-50'
                    }`}
                    title={module.isVisible === false ? "Show Module" : "Hide Module"}
                >
                    {loadingModuleId === module.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                    ) : module.isVisible === false ? (
                        <EyeOff className="w-4 h-4" />
                    ) : (
                        <Eye className="w-4 h-4" />
                    )}
                </button>
                <button
                  onClick={() => startEdit(module)}
                  disabled={loadingModuleId === module.id}
                  className="p-2 text-blue-600 hover:bg-blue-50 rounded transition-colors disabled:opacity-50"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleDeleteModule(module.id)}
                  disabled={loadingModuleId === module.id}
                  className="p-2 text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
                >
                  {loadingModuleId === module.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                      <Trash2 className="w-4 h-4" />
                  )}
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
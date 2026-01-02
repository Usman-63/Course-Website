import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Plus, Edit2, Trash2, X, Save } from 'lucide-react';
import { CourseLink, addLink, updateLink, deleteLink } from '../services/api';

interface LinkEditorProps {
  links: CourseLink[];
  onUpdate: () => void;
}

const LinkEditor: React.FC<LinkEditorProps> = ({ links, onUpdate }) => {
  const [editingLink, setEditingLink] = useState<CourseLink | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState<Partial<CourseLink>>({
    title: '',
    url: '',
    description: '',
    iconType: 'file',
    order: links.length + 1,
  });
  const [isLoading, setIsLoading] = useState(false);

  const handleAddLink = async () => {
    setIsLoading(true);
    try {
      await addLink(formData as Omit<CourseLink, 'id'>);
      setShowAddForm(false);
      setFormData({ title: '', url: '', description: '', iconType: 'file', order: links.length + 1 });
      onUpdate();
    } catch (error) {
      console.error('Failed to add link:', error);
      alert('Failed to add link');
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateLink = async () => {
    if (!editingLink) return;
    setIsLoading(true);
    try {
      await updateLink(editingLink.id, formData);
      setEditingLink(null);
      onUpdate();
    } catch (error) {
      console.error('Failed to update link:', error);
      alert('Failed to update link');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteLink = async (linkId: string) => {
    if (!confirm('Are you sure you want to delete this link?')) return;
    setIsLoading(true);
    try {
      await deleteLink(linkId);
      onUpdate();
    } catch (error) {
      console.error('Failed to delete link:', error);
      alert('Failed to delete link');
    } finally {
      setIsLoading(false);
    }
  };

  const startEdit = (link: CourseLink) => {
    setEditingLink(link);
    setFormData(link);
    setShowAddForm(false);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xl font-bold text-yellow">Course Links</h3>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => {
            setShowAddForm(true);
            setEditingLink(null);
            setFormData({ title: '', url: '', description: '', iconType: 'file', order: links.length + 1 });
          }}
          className="bg-yellow text-navy px-4 py-2 rounded-lg font-semibold flex items-center gap-2 hover:bg-yellow/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Link
        </motion.button>
      </div>

      {(showAddForm || editingLink) && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-navy-light p-6 rounded-lg border-2 border-yellow/30"
        >
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-lg font-bold text-yellow">
              {editingLink ? 'Edit Link' : 'Add New Link'}
            </h4>
            <button
              onClick={() => {
                setShowAddForm(false);
                setEditingLink(null);
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
                placeholder="Course Syllabus"
              />
            </div>

            <div>
              <label className="block text-yellow font-semibold mb-2">URL</label>
              <input
                type="url"
                value={formData.url}
                onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                className="w-full px-4 py-2 bg-navy border border-navy-light/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-yellow"
                placeholder="https://..."
              />
            </div>

            <div>
              <label className="block text-yellow font-semibold mb-2">Description</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-4 py-2 bg-navy border border-navy-light/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-yellow"
                rows={3}
                placeholder="Link description"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-yellow font-semibold mb-2">Icon Type</label>
                <select
                  value={formData.iconType}
                  onChange={(e) => setFormData({ ...formData, iconType: e.target.value })}
                  className="w-full px-4 py-2 bg-navy border border-navy-light/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-yellow"
                >
                  <option value="file">File</option>
                  <option value="register">Register</option>
                  <option value="wechat">WeChat</option>
                </select>
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

            <button
              onClick={editingLink ? handleUpdateLink : handleAddLink}
              disabled={isLoading}
              className="w-full bg-yellow text-navy font-bold py-3 rounded-lg hover:bg-yellow/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              <Save className="w-4 h-4" />
              {isLoading ? 'Saving...' : editingLink ? 'Update Link' : 'Add Link'}
            </button>
          </div>
        </motion.div>
      )}

      <div className="space-y-3">
        {links.map((link) => (
          <motion.div
            key={link.id}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="bg-navy-light p-4 rounded-lg border border-yellow/20"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h4 className="text-yellow font-bold mb-1">{link.title}</h4>
                {link.description && (
                  <p className="text-gray-300 text-sm mb-2">{link.description}</p>
                )}
                <div className="flex gap-4 text-sm text-gray-400">
                  <span className="truncate max-w-md">{link.url}</span>
                  <span>Order: {link.order}</span>
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => startEdit(link)}
                  className="p-2 text-yellow hover:bg-yellow/20 rounded transition-colors"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleDeleteLink(link.id)}
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

export default LinkEditor;


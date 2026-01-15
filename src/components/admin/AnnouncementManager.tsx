import React, { useState, useEffect } from 'react';
import { db } from '../../services/firebase';
import { collection, addDoc, updateDoc, deleteDoc, doc, onSnapshot, query, orderBy, serverTimestamp } from 'firebase/firestore';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Trash2, Edit2, Megaphone, CheckCircle } from 'lucide-react';

interface Announcement {
  id: string;
  title: string;
  content: string;
  isActive: boolean;
  createdAt: any;
}

const AnnouncementManager: React.FC = () => {
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [isEditing, setIsEditing] = useState(false);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [formData, setFormData] = useState({ title: '', content: '', isActive: true });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const q = query(collection(db, 'announcements'), orderBy('createdAt', 'desc'));
    const unsubscribe = onSnapshot(q, (snapshot) => {
      const data = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      })) as Announcement[];
      setAnnouncements(data);
    });
    return unsubscribe;
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (currentId) {
        await updateDoc(doc(db, 'announcements', currentId), {
          title: formData.title,
          content: formData.content,
          isActive: formData.isActive,
          updatedAt: serverTimestamp()
        });
      } else {
        await addDoc(collection(db, 'announcements'), {
          title: formData.title,
          content: formData.content,
          isActive: formData.isActive,
          createdAt: serverTimestamp()
        });
      }
      resetForm();
    } catch (error) {
      console.error("Error saving announcement:", error);
    }
    setLoading(false);
  };

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this announcement?')) {
      await deleteDoc(doc(db, 'announcements', id));
    }
  };

  const startEdit = (announcement: Announcement) => {
    setCurrentId(announcement.id);
    setFormData({
      title: announcement.title,
      content: announcement.content,
      isActive: announcement.isActive
    });
    setIsEditing(true);
  };

  const resetForm = () => {
    setIsEditing(false);
    setCurrentId(null);
    setFormData({ title: '', content: '', isActive: true });
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Megaphone className="text-yellow-600" /> Announcements
        </h3>
        {!isEditing && (
          <button
            onClick={() => setIsEditing(true)}
            className="bg-yellow text-navy px-4 py-2 rounded-lg font-bold flex items-center gap-2 hover:bg-yellow-hover transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" /> New Announcement
          </button>
        )}
      </div>

      <AnimatePresence>
        {isEditing && (
          <motion.form
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            onSubmit={handleSubmit}
            className="bg-white p-6 rounded-xl border border-gray-200 space-y-4 shadow-sm"
          >
            <div>
              <label className="block text-gray-500 text-sm mb-1">Title</label>
              <input
                type="text"
                required
                value={formData.title}
                onChange={e => setFormData({ ...formData, title: e.target.value })}
                className="w-full bg-white border border-gray-300 rounded-lg p-3 text-gray-900 focus:border-yellow outline-none focus:ring-1 focus:ring-yellow transition-all"
                placeholder="e.g., New Module Released!"
              />
            </div>
            <div>
              <label className="block text-gray-500 text-sm mb-1">Content</label>
              <textarea
                required
                rows={4}
                value={formData.content}
                onChange={e => setFormData({ ...formData, content: e.target.value })}
                className="w-full bg-white border border-gray-300 rounded-lg p-3 text-gray-900 focus:border-yellow outline-none focus:ring-1 focus:ring-yellow transition-all"
                placeholder="Write your announcement here..."
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="isActive"
                checked={formData.isActive}
                onChange={e => setFormData({ ...formData, isActive: e.target.checked })}
                className="w-4 h-4 rounded border-gray-300 text-yellow focus:ring-yellow"
              />
              <label htmlFor="isActive" className="text-gray-700">Publish Immediately</label>
            </div>
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={resetForm}
                className="px-4 py-2 text-gray-500 hover:text-gray-900 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="bg-yellow text-navy px-6 py-2 rounded-lg font-bold hover:bg-yellow-hover transition-colors disabled:opacity-50 shadow-sm"
              >
                {loading ? 'Saving...' : 'Save Announcement'}
              </button>
            </div>
          </motion.form>
        )}
      </AnimatePresence>

      <div className="grid gap-4">
        {announcements.map((item) => (
          <motion.div
            key={item.id}
            layout
            className="bg-white p-5 rounded-xl border border-gray-200 flex justify-between items-start group hover:border-gray-300 transition-all shadow-sm"
          >
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h4 className="text-lg font-bold text-gray-900">{item.title}</h4>
                {item.isActive ? (
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full flex items-center gap-1 border border-green-200">
                    <CheckCircle className="w-3 h-3" /> Active
                  </span>
                ) : (
                  <span className="text-xs bg-gray-100 text-gray-500 px-2 py-1 rounded-full border border-gray-200">Draft</span>
                )}
              </div>
              <p className="text-gray-600 text-sm whitespace-pre-wrap">{item.content}</p>
              <p className="text-xs text-gray-400 mt-2">
                Posted: {item.createdAt?.toDate().toLocaleDateString()}
              </p>
            </div>
            <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={() => startEdit(item)}
                className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
              >
                <Edit2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => handleDelete(item.id)}
                className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </motion.div>
        ))}
        {announcements.length === 0 && !isEditing && (
          <div className="text-center py-10 text-gray-500">
            No announcements yet. Create one to notify your students.
          </div>
        )}
      </div>
    </div>
  );
};

export default AnnouncementManager;

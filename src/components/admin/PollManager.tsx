import React, { useState, useEffect } from 'react';
import { db } from '../../services/firebase';
import { collection, addDoc, updateDoc, deleteDoc, doc, onSnapshot, query, orderBy, serverTimestamp } from 'firebase/firestore';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Trash2, Edit2, BarChart2, X, CheckCircle, Download, Users } from 'lucide-react';

interface PollOption {
  id: string;
  text: string;
  votes: number;
}

interface VoteRecord {
  uid: string;
  name: string;
  optionId: string;
  timestamp: string;
}

interface Poll {
  id: string;
  question: string;
  options: PollOption[];
  isActive: boolean;
  totalVotes: number;
  createdAt: any;
  votes?: VoteRecord[];
}

const PollManager: React.FC = () => {
  const [polls, setPolls] = useState<Poll[]>([]);
  const [isEditing, setIsEditing] = useState(false);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [question, setQuestion] = useState('');
  const [options, setOptions] = useState<string[]>(['', '']); // Start with 2 empty options
  const [isActive, setIsActive] = useState(true);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const q = query(collection(db, 'polls'), orderBy('createdAt', 'desc'));
    const unsubscribe = onSnapshot(q, (snapshot) => {
      const data = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      })) as Poll[];
      setPolls(data);
    });
    return unsubscribe;
  }, []);

  const handleAddOption = () => {
    setOptions([...options, '']);
  };

  const handleOptionChange = (index: number, value: string) => {
    const newOptions = [...options];
    newOptions[index] = value;
    setOptions(newOptions);
  };

  const handleRemoveOption = (index: number) => {
    if (options.length > 2) {
      const newOptions = options.filter((_, i) => i !== index);
      setOptions(newOptions);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    const validOptions = options.filter(opt => opt.trim() !== '');
    if (validOptions.length < 2) {
      alert("Please provide at least 2 valid options");
      setLoading(false);
      return;
    }

    try {
      if (currentId) {
        // Logic to update existing poll
        // For now, we'll just update meta-data to avoid complex vote merging logic in this turn
        await updateDoc(doc(db, 'polls', currentId), {
          question,
          isActive,
          // Not updating options here to prevent vote loss. 
          // A full edit feature would need more complex logic.
        });
      } else {
        // New Poll
        const newOptions: PollOption[] = validOptions.map(text => ({
          id: Math.random().toString(36).substr(2, 9),
          text,
          votes: 0
        }));

        await addDoc(collection(db, 'polls'), {
          question,
          options: newOptions,
          isActive,
          totalVotes: 0,
          createdAt: serverTimestamp(),
          votes: []
        });
      }
      resetForm();
    } catch (error) {
      console.error("Error saving poll:", error);
    }
    setLoading(false);
  };

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this poll?')) {
      await deleteDoc(doc(db, 'polls', id));
    }
  };

  const startEdit = (poll: Poll) => {
    setCurrentId(poll.id);
    setQuestion(poll.question);
    // For now, we only allow editing the question and status to preserve vote integrity
    // setOptions(poll.options.map(o => o.text)); 
    setIsActive(poll.isActive);
    setIsEditing(true);
  };

  const resetForm = () => {
    setIsEditing(false);
    setCurrentId(null);
    setQuestion('');
    setOptions(['', '']);
    setIsActive(true);
  };

    const downloadCSV = (poll: Poll) => {
    if (!poll.votes || poll.votes.length === 0) {
      alert("No votes to export");
      return;
    }
    
    const headers = "User Name,User ID,Option,Timestamp\n";
    const rows = poll.votes.map(v => {
      const optionText = poll.options.find(o => o.id === v.optionId)?.text || 'Unknown';
      return `"${v.name}","${v.uid}","${optionText}","${v.timestamp}"`;
    }).join("\n");
    
    const csvContent = "data:text/csv;charset=utf-8," + headers + rows;
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `poll_results_${poll.id}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <BarChart2 className="text-yellow-600" /> Polls
        </h3>
        {!isEditing && (
          <button
            onClick={() => setIsEditing(true)}
            className="bg-yellow text-navy px-4 py-2 rounded-lg font-bold flex items-center gap-2 hover:bg-yellow-hover transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" /> New Poll
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
              <label className="block text-gray-500 text-sm mb-1">Question</label>
              <input
                type="text"
                required
                value={question}
                onChange={e => setQuestion(e.target.value)}
                className="w-full bg-white border border-gray-300 rounded-lg p-3 text-gray-900 focus:border-yellow outline-none focus:ring-1 focus:ring-yellow transition-all"
                placeholder="e.g., What topic should we cover next?"
              />
            </div>

            {!currentId && (
              <div>
                <label className="block text-gray-500 text-sm mb-2">Options</label>
                <div className="space-y-2">
                  {options.map((opt, idx) => (
                    <div key={idx} className="flex gap-2">
                      <input
                        type="text"
                        required
                        value={opt}
                        onChange={e => handleOptionChange(idx, e.target.value)}
                        className="w-full bg-white border border-gray-300 rounded-lg p-2 text-gray-900 focus:border-yellow outline-none focus:ring-1 focus:ring-yellow transition-all"
                        placeholder={`Option ${idx + 1}`}
                      />
                      {options.length > 2 && (
                        <button
                          type="button"
                          onClick={() => handleRemoveOption(idx)}
                          className="text-red-500 hover:text-red-700"
                        >
                          <X className="w-5 h-5" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={handleAddOption}
                  className="text-yellow-600 text-sm mt-2 hover:underline flex items-center gap-1"
                >
                  <Plus className="w-3 h-3" /> Add Option
                </button>
              </div>
            )}

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="isPollActive"
                checked={isActive}
                onChange={e => setIsActive(e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 text-yellow focus:ring-yellow"
              />
              <label htmlFor="isPollActive" className="text-gray-700">Active (Accepting Votes)</label>
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
                {loading ? 'Saving...' : currentId ? 'Update Poll' : 'Create Poll'}
              </button>
            </div>
            {currentId && (
              <p className="text-xs text-gray-400 text-right">
                Note: Editing options is disabled to preserve existing votes.
              </p>
            )}
          </motion.form>
        )}
      </AnimatePresence>

      <div className="grid gap-4">
        {polls.map((poll) => (
          <motion.div
            key={poll.id}
            layout
            className="bg-white p-5 rounded-xl border border-gray-200 group hover:border-gray-300 transition-all shadow-sm"
          >
            <div className="flex justify-between items-start mb-4">
              <div>
                <h4 className="text-lg font-bold text-gray-900 mb-1">{poll.question}</h4>
                <div className="flex items-center gap-3">
                  {poll.isActive ? (
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full flex items-center gap-1 border border-green-200">
                      <CheckCircle className="w-3 h-3" /> Active
                    </span>
                  ) : (
                    <span className="text-xs bg-gray-100 text-gray-500 px-2 py-1 rounded-full border border-gray-200">Closed</span>
                  )}
                  <span className="text-xs text-gray-500">{poll.totalVotes} votes total</span>
                </div>
              </div>
              <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => downloadCSV(poll)}
                  className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                  title="Download CSV Results"
                >
                  <Download className="w-4 h-4" />
                </button>
                <button
                  onClick={() => startEdit(poll)}
                  className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleDelete(poll.id)}
                  className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="space-y-2 mb-4">
              {poll.options.map((opt) => {
                const percentage = poll.totalVotes > 0 ? Math.round((opt.votes / poll.totalVotes) * 100) : 0;
                return (
                  <div key={opt.id} className="relative h-8 bg-gray-100 rounded-lg overflow-hidden border border-gray-200">
                    <div 
                      className="absolute top-0 left-0 h-full bg-yellow/20 transition-all duration-500"
                      style={{ width: `${percentage}%` }}
                    />
                    <div className="absolute inset-0 flex items-center justify-between px-3">
                      <span className="text-sm text-gray-700 font-medium">{opt.text}</span>
                      <span className="text-xs font-bold text-yellow-700">{percentage}% ({opt.votes})</span>
                    </div>
                  </div>
                );
              })}
            </div>
            
            {/* Detailed Voter List */}
            {poll.votes && poll.votes.length > 0 && (
              <div className="mt-4 pt-4 border-t border-gray-100">
                <div className="flex items-center gap-2 text-gray-400 mb-2">
                   <Users className="w-4 h-4" />
                   <span className="text-xs font-bold uppercase">Recent Voters</span>
                </div>
                <div className="space-y-1 max-h-32 overflow-y-auto pr-2 custom-scrollbar">
                  {poll.votes.slice(0, 10).map((vote, i) => {
                     const optionText = poll.options.find(o => o.id === vote.optionId)?.text || 'Unknown';
                     return (
                       <div key={i} className="flex justify-between text-xs text-gray-500">
                         <span>{vote.name}</span>
                         <span className="text-yellow-600 font-medium">{optionText}</span>
                       </div>
                     );
                  })}
                  {poll.votes.length > 10 && (
                    <div className="text-center text-xs text-gray-400 italic pt-1">
                      ...and {poll.votes.length - 10} more. Download CSV for full list.
                    </div>
                  )}
                </div>
              </div>
            )}
          </motion.div>
        ))}
         {polls.length === 0 && !isEditing && (
          <div className="text-center py-10 text-gray-500">
            No polls created yet.
          </div>
        )}
      </div>
    </div>
  );
};

export default PollManager;
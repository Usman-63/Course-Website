import { useState, useEffect } from 'react';
import { Calendar, Users, Plus, Trash2, CheckCircle } from 'lucide-react';
import { ClassSession, classService } from '../../services/classService';
import { StudentOperations } from '../../services/api';
import { useToast } from '../Toast';
import ClassAttendanceSheet from './ClassAttendanceSheet';

interface AttendanceManagerProps {
  students: StudentOperations[];
  onUpdate: () => Promise<void>;
}

export default function AttendanceManager({ students, onUpdate }: AttendanceManagerProps) {
  const toast = useToast();
  const [classes, setClasses] = useState<ClassSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newClass, setNewClass] = useState({ date: '', topic: '', description: '' });
  const [selectedClass, setSelectedClass] = useState<ClassSession | null>(null);

  useEffect(() => {
    loadClasses();
  }, []);

  const loadClasses = async () => {
    try {
      const data = await classService.getAll();
      // Sort by date descending
      setClasses(data.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()));
    } catch (error) {
      console.error('Failed to load classes:', error);
      // Don't toast on initial load error if just empty
    } finally {
      setLoading(false);
    }
  };

  const handleAddClass = async () => {
    if (!newClass.date || !newClass.topic) return;
    try {
      await classService.add(newClass);
      toast.success('Class added');
      setShowAddForm(false);
      setNewClass({ date: '', topic: '', description: '' });
      loadClasses();
    } catch (error) {
      toast.error('Failed to add class');
    }
  };

  const handleDeleteClass = async (id: string) => {
    if (!confirm('Are you sure?')) return;
    try {
      await classService.delete(id);
      toast.success('Class deleted');
      loadClasses();
    } catch (error) {
      toast.error('Failed to delete class');
    }
  };

  const getAttendanceCount = (classId: string) => {
    return students.filter(s => {
        try {
            const att = typeof s.Attendance === 'string' ? JSON.parse(s.Attendance) : s.Attendance;
            // The key used in JSON is the classId (UUID)
            return att && att[classId];
        } catch { return false; }
    }).length;
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <Calendar className="text-yellow-600" /> Class Schedule
        </h3>
        <button
          onClick={() => setShowAddForm(true)}
          className="bg-yellow text-navy px-4 py-2 rounded-lg font-bold flex items-center gap-2 hover:bg-yellow-hover shadow-sm"
        >
          <Plus className="w-4 h-4" /> Add Class
        </button>
      </div>

      {showAddForm && (
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4 animate-in slide-in-from-top-2">
          <h4 className="font-bold text-gray-900">New Class Session</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input
              type="date"
              value={newClass.date}
              onChange={e => setNewClass({...newClass, date: e.target.value})}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow focus:border-transparent outline-none"
            />
            <input
              type="text"
              placeholder="Topic (e.g. React Hooks)"
              value={newClass.topic}
              onChange={e => setNewClass({...newClass, topic: e.target.value})}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow focus:border-transparent outline-none"
            />
          </div>
          <input
            type="text"
            placeholder="Description (Optional)"
            value={newClass.description}
            onChange={e => setNewClass({...newClass, description: e.target.value})}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow focus:border-transparent outline-none"
          />
          <div className="flex justify-end gap-2">
            <button onClick={() => setShowAddForm(false)} className="px-4 py-2 text-gray-500 hover:bg-gray-100 rounded-lg">Cancel</button>
            <button onClick={handleAddClass} className="px-6 py-2 bg-yellow text-navy rounded-lg font-bold hover:bg-yellow-hover">Save Class</button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-center py-10 text-gray-500">Loading classes...</div>
      ) : classes.length === 0 ? (
        <div className="text-center py-10 bg-gray-50 rounded-xl border border-dashed border-gray-300">
            <Calendar className="w-10 h-10 text-gray-400 mx-auto mb-2" />
            <p className="text-gray-500">No classes scheduled yet.</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {classes.map(cls => {
                const count = getAttendanceCount(cls.id);
                return (
                <div key={cls.id} className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm hover:border-gray-300 transition-all group">
                    <div className="flex justify-between items-start mb-3">
                    <div>
                        <span className="text-xs font-mono text-gray-500 bg-gray-100 px-2 py-1 rounded border border-gray-200">{cls.date}</span>
                        <h4 className="font-bold text-gray-900 mt-2 text-lg">{cls.topic}</h4>
                        {cls.description && <p className="text-sm text-gray-500 mt-1">{cls.description}</p>}
                    </div>
                    <button onClick={() => handleDeleteClass(cls.id)} className="text-gray-300 hover:text-red-500 p-1">
                        <Trash2 className="w-4 h-4" />
                    </button>
                    </div>
                    
                    <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-100">
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                        <Users className="w-4 h-4" />
                        <span className="font-medium">{count}</span>
                        <span className="text-gray-400">Present</span>
                    </div>
                    <button
                        onClick={() => setSelectedClass(cls)}
                        className="text-sm font-semibold text-blue-600 hover:text-blue-700 hover:underline flex items-center gap-1 bg-blue-50 px-3 py-1.5 rounded-lg border border-blue-100"
                    >
                        <CheckCircle className="w-4 h-4" /> Mark
                    </button>
                    </div>
                </div>
                );
            })}
        </div>
      )}

      {selectedClass && (
        <ClassAttendanceSheet
          classSession={selectedClass}
          students={students}
          isOpen={!!selectedClass}
          onClose={() => setSelectedClass(null)}
          onSave={async () => {
             await onUpdate();
             setSelectedClass(null);
          }}
        />
      )}
    </div>
  );
}

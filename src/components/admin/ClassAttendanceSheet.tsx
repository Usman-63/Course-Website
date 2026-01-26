'use client';

import { useState, useEffect, Fragment } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { X, Save, Search, CheckSquare, Square, Loader2 } from 'lucide-react';
import { ClassSession, classService } from '../../services/classService';
import { UserWithAdminData } from '../../services/api';
import { useToast } from '../Toast';

interface ClassAttendanceSheetProps {
  classSession: ClassSession;
  students: UserWithAdminData[];
  isOpen: boolean;
  onClose: () => void;
  onSave: () => Promise<void>;
}

export default function ClassAttendanceSheet({ classSession, students, isOpen, onClose, onSave }: ClassAttendanceSheetProps) {
  const toast = useToast();
  const [presentEmails, setPresentEmails] = useState<Set<string>>(new Set());
  const [searchTerm, setSearchTerm] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      // Initialize present emails from current data
      const initialPresent = new Set<string>();
      students.forEach(s => {
        try {
          const att = typeof s.Attendance === 'string' ? JSON.parse(s.Attendance) : s.Attendance;
          if (att && att[classSession.id]) {
            initialPresent.add(s['Email Address']);
          }
        } catch {}
      });
      setPresentEmails(initialPresent);
    } else {
      // Reset when dialog closes to prevent stale state
      setPresentEmails(new Set());
    }
  }, [isOpen, students, classSession.id]);

  const toggleStudent = (email: string) => {
    const newSet = new Set(presentEmails);
    if (newSet.has(email)) {
      newSet.delete(email);
    } else {
      newSet.add(email);
    }
    setPresentEmails(newSet);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await classService.markAttendance(classSession.id, Array.from(presentEmails));
      toast.success('Attendance updated');
      await onSave();
      onClose();
    } catch (error) {
      toast.error('Failed to save attendance');
    } finally {
      setSaving(false);
    }
  };

  const filteredStudents = students.filter(s => {
      const name = s.Name || s.name || '';
      const email = s['Email Address'] || '';
      const search = searchTerm.toLowerCase();
      return name.toLowerCase().includes(search) || email.toLowerCase().includes(search);
  });

  return (
    <Transition.Root show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <div className="fixed inset-0 bg-gray-900/50 backdrop-blur-sm" />
        <div className="fixed inset-0 overflow-hidden">
          <div className="absolute inset-0 overflow-hidden">
            <div className="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10">
              <Transition.Child
                as={Fragment}
                enter="transform transition ease-in-out duration-300 sm:duration-500"
                enterFrom="translate-x-full"
                enterTo="translate-x-0"
                leave="transform transition ease-in-out duration-300 sm:duration-500"
                leaveFrom="translate-x-0"
                leaveTo="translate-x-full"
              >
                <Dialog.Panel className="pointer-events-auto w-screen max-w-md">
                  <div className="flex h-full flex-col bg-white shadow-xl border-l border-gray-200">
                    <div className="px-4 py-6 bg-gray-50 border-b border-gray-200">
                      <div className="flex items-start justify-between">
                        <div>
                          <Dialog.Title className="text-lg font-bold text-gray-900">
                            Mark Attendance
                          </Dialog.Title>
                          <p className="text-sm text-gray-500 mt-1">{classSession.topic} ({classSession.date})</p>
                        </div>
                        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
                          <X className="w-6 h-6" />
                        </button>
                      </div>
                      
                      <div className="mt-4 relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                          type="text"
                          placeholder="Search student..."
                          value={searchTerm}
                          onChange={e => setSearchTerm(e.target.value)}
                          className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-yellow focus:border-transparent outline-none"
                        />
                      </div>
                      
                      <div className="mt-3 flex justify-between items-center text-sm">
                        <span className="font-medium text-gray-700">
                            Present: <span className="text-green-600">{presentEmails.size}</span> / {students.length}
                        </span>
                        <button 
                            onClick={() => {
                                if (presentEmails.size === students.filter(s => s['Email Address']).length) {
                                    setPresentEmails(new Set());
                                } else {
                                    setPresentEmails(new Set(students.filter(s => s['Email Address']).map(s => s['Email Address'])));
                                }
                            }}
                            className="text-blue-600 hover:underline"
                        >
                            {presentEmails.size > 0 && presentEmails.size >= students.filter(s => s['Email Address']).length ? 'Unmark All' : 'Mark All'}
                        </button>
                      </div>
                    </div>

                    <div className="flex-1 overflow-y-auto p-4 space-y-2">
                        {filteredStudents.map((student, index) => {
                            const email = student['Email Address'];
                            const hasEmail = !!email;
                            const isPresent = hasEmail && presentEmails.has(email);
                            const name = student.Name || student.name || 'Unknown';
                            
                            return (
                                <div 
                                    key={`${email}-${index}`}
                                    onClick={() => hasEmail && toggleStudent(email)}
                                    className={`flex items-center justify-between p-3 rounded-lg border transition-colors ${
                                        !hasEmail 
                                            ? 'opacity-50 cursor-not-allowed bg-gray-50 border-gray-200' 
                                            : (isPresent ? 'bg-green-50 border-green-200 cursor-pointer' : 'bg-white border-gray-200 hover:bg-gray-50 cursor-pointer')
                                    }`}
                                    title={!hasEmail ? "Set an email first to mark attendance" : ""}
                                >
                                    <div className="flex flex-col">
                                        <span className={`font-medium ${isPresent ? 'text-gray-900' : 'text-gray-600'}`}>{name}</span>
                                        <span className="text-xs text-gray-400">{email || 'No Email'}</span>
                                    </div>
                                    {!hasEmail ? (
                                        <Square className="w-5 h-5 text-gray-200" />
                                    ) : isPresent ? (
                                        <CheckSquare className="w-5 h-5 text-green-600" />
                                    ) : (
                                        <Square className="w-5 h-5 text-gray-300" />
                                    )}
                                </div>
                            );
                        })}
                    </div>

                    <div className="p-4 border-t border-gray-200 bg-gray-50">
                      <button
                        onClick={handleSave}
                        disabled={saving}
                        className="w-full bg-yellow text-navy font-bold py-3 rounded-xl hover:bg-yellow-hover disabled:opacity-50 flex items-center justify-center gap-2"
                      >
                        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                        Save Attendance
                      </button>
                    </div>
                  </div>
                </Dialog.Panel>
              </Transition.Child>
            </div>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  );
}

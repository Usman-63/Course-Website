import React, { Fragment, useState, useEffect } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { X, Save, CheckSquare, Square, AlertCircle, Loader2, TrendingUp, FileText, Users, DollarSign, MessageSquare } from 'lucide-react';
import { UserWithAdminData, updateUserAdminData } from '../../services/api';

interface StudentEditSheetProps {
  isOpen: boolean;
  onClose: () => void;
  student: UserWithAdminData | null;
  onSave: (uid: string, updates: Partial<UserWithAdminData>) => Promise<void>;
  totalLabs: number;
  classMap: Map<string, string>; // Map class ID to topic
}

const StudentEditSheet: React.FC<StudentEditSheetProps> = ({ 
  isOpen, 
  onClose, 
  student, 
  onSave, 
  totalLabs,
  classMap
}) => {
  const [formData, setFormData] = useState<Partial<UserWithAdminData>>({});
  const [isSaving, setIsSaving] = useState(false);
  const [lastStudentId, setLastStudentId] = useState<string | null>(null);

  useEffect(() => {
    // Only reset formData when opening with a different student
    const currentId = student?._id;
    if (student && currentId && currentId !== lastStudentId) {
      // Parse attendance if it's a string
      let attendance = student.attendance || {};
      if (typeof attendance === 'string') {
        try {
          attendance = JSON.parse(attendance);
        } catch {
          attendance = {};
        }
      }

      setFormData({
        Name: student.Name || student.name || '',
        attendance: attendance || {},
        'Teacher Evaluation': student['Teacher Evaluation'] || student.teacherEvaluation || '',
        'Payment Status': student['Payment Status'] || student.paymentStatus || '',
        'Payment Comment': student['Payment Comment'] || student.paymentComment || '',
        ...Object.fromEntries(
          Array.from({ length: totalLabs }, (_, i) => [
            `Assignment ${i + 1} Grade`,
            '' // Will be populated from assignmentGrades if needed
          ])
        )
      });
      
      setLastStudentId(currentId);
    }
  }, [student, totalLabs, lastStudentId]);

  const handleSave = async () => {
    if (!student?._id) return;
    
    setIsSaving(true);
    try {
      await onSave(student._id, formData);
      // Reset lastStudentId so formData resets on next open
      setLastStudentId(null);
      onClose();
    } catch (error) {
      console.error('Failed to save:', error);
      // Don't reset lastStudentId on error so user can retry
    } finally {
      setIsSaving(false);
    }
  };

  const toggleAttendance = (className: string) => {
    const currentAttendance = (formData.attendance as Record<string, boolean>) || {};
    setFormData({
      ...formData,
      attendance: {
        ...currentAttendance,
        [className]: !currentAttendance[className]
      }
    });
  };

  if (!student) return null;

  return (
    <Transition.Root show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-in-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in-out duration-300"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-900/50 backdrop-blur-sm transition-opacity" />
        </Transition.Child>

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
                <Dialog.Panel className="pointer-events-auto w-screen max-w-2xl">
                  <div className="flex h-full flex-col overflow-y-scroll bg-white shadow-2xl border-l border-gray-200">
                    
                    {/* Header */}
                    <div className="px-4 py-6 sm:px-6 border-b border-gray-200 bg-white sticky top-0 z-10">
                      <div className="flex items-start justify-between">
                        <div>
                          <Dialog.Title className="text-xl font-semibold leading-6 text-gray-900">
                            Edit Student Record
                          </Dialog.Title>
                          <div className="mt-1 flex flex-col">
                            <span className="text-yellow-600 font-medium text-lg">{student.Name || student.name || 'Unknown Name'}</span>
                            <span className="text-gray-500 text-sm">{student['Email Address']}</span>
                          </div>
                        </div>
                        <div className="ml-3 flex h-7 items-center">
                          <button
                            type="button"
                            className="rounded-md text-gray-400 hover:text-gray-600 focus:outline-none transition-colors"
                            onClick={onClose}
                          >
                            <span className="sr-only">Close panel</span>
                            <X className="h-6 w-6" aria-hidden="true" />
                          </button>
                        </div>
                      </div>
                    </div>

                    {/* Content */}
                    <div className="relative flex-1 px-4 py-6 sm:px-6 space-y-8">
                      
                      {/* Section: Student Info */}
                      <section>
                        <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center gap-2">
                          <Users className="text-yellow-600 w-5 h-5" />
                          Student Info
                        </h3>
                        <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
                          <div>
                            <label className="block text-gray-600 text-sm font-medium mb-1.5">
                              Student Name
                            </label>
                            <input
                              type="text"
                              value={formData.Name || ''}
                              onChange={(e) => setFormData({ ...formData, Name: e.target.value })}
                              className="w-full px-4 py-2.5 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:border-transparent transition-all"
                              placeholder="Full Name"
                            />
                          </div>
                        </div>
                      </section>

                      {/* Section: Attendance */}
                      <section>
                        <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center gap-2">
                          <CheckSquare className="text-yellow-600 w-5 h-5" />
                          Attendance Record
                        </h3>
                        <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {Object.keys((formData.attendance as Record<string, boolean>) || {}).length > 0 ? (
                              Object.keys((formData.attendance as Record<string, boolean>)).map((classId) => {
                                const isPresent = (formData.attendance as Record<string, boolean>)[classId];
                                const classTopic = classMap.get(classId) || classId; // Use topic if available, fallback to ID
                                return (
                                  <div 
                                    key={classId}
                                    onClick={() => toggleAttendance(classId)}
                                    className={`
                                      flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-all
                                      ${isPresent 
                                        ? 'bg-green-50 border-green-200 hover:bg-green-100' 
                                        : 'bg-white border-gray-200 hover:bg-gray-100'
                                      }
                                    `}
                                  >
                                    <span className={`text-sm font-medium ${isPresent ? 'text-green-700' : 'text-gray-600'}`}>
                                      {classTopic}
                                    </span>
                                    {isPresent ? (
                                      <CheckSquare className="w-5 h-5 text-green-600" />
                                    ) : (
                                      <Square className="w-5 h-5 text-gray-400" />
                                    )}
                                  </div>
                                );
                              })
                            ) : (
                              <div className="col-span-full flex flex-col items-center justify-center p-6 text-gray-500 bg-white rounded-lg border border-dashed border-gray-300">
                                <AlertCircle className="w-8 h-8 mb-2 opacity-50" />
                                <p>No attendance classes defined yet.</p>
                              </div>
                            )}
                          </div>
                        </div>
                      </section>

                      {/* Section: Grades */}
                      <section>
                        <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center gap-2">
                          <TrendingUp className="text-yellow-600 w-5 h-5" />
                          Assignment Grades
                        </h3>
                        <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            {Array.from({ length: totalLabs }, (_, i) => {
                              const assignmentNum = i + 1;
                              const gradeKey = `Assignment ${assignmentNum} Grade`;
                              return (
                                <div key={i}>
                                  <label className="block text-gray-600 text-sm font-medium mb-1.5">
                                    Assignment {assignmentNum}
                                  </label>
                                  <input
                                    type="text"
                                    value={formData[gradeKey] || ''}
                                    onChange={(e) => setFormData({ ...formData, [gradeKey]: e.target.value })}
                                    className="w-full px-4 py-2.5 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:border-transparent transition-all"
                                    placeholder="Grade (e.g. 95)"
                                  />
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </section>

                      {/* Section: Payment Status */}
                      <section>
                        <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center gap-2">
                          <DollarSign className="text-yellow-600 w-5 h-5" />
                          Payment Status
                        </h3>
                        <div className="bg-gray-50 p-4 rounded-xl border border-gray-200 space-y-4">
                          <div>
                            <label className="block text-gray-600 text-sm font-medium mb-1.5">
                              Payment Status
                            </label>
                            <select
                              value={formData['Payment Status'] || ''}
                              onChange={(e) => setFormData({ ...formData, 'Payment Status': e.target.value })}
                              className="w-full px-4 py-2.5 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:border-transparent transition-all"
                            >
                              <option value="">-- Select Status --</option>
                              <option value="Paid">Paid</option>
                              <option value="Unpaid">Unpaid</option>
                            </select>
                          </div>
                          <div>
                            <label className="block text-gray-600 text-sm font-medium mb-1.5 flex items-center gap-2">
                              <MessageSquare className="w-4 h-4" />
                              Payment Comment
                            </label>
                            <textarea
                              value={formData['Payment Comment'] || ''}
                              onChange={(e) => setFormData({ ...formData, 'Payment Comment': e.target.value })}
                              className="w-full px-4 py-3 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:border-transparent transition-all min-h-[100px] leading-relaxed"
                              placeholder="Add notes about payment status, reason for change, etc..."
                            />
                          </div>
                        </div>
                      </section>

                      {/* Section: Evaluation */}
                      <section>
                        <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center gap-2">
                          <FileText className="text-yellow-600 w-5 h-5" />
                          Teacher Evaluation
                        </h3>
                        <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
                          <textarea
                            value={formData['Teacher Evaluation'] || ''}
                            onChange={(e) => setFormData({ ...formData, 'Teacher Evaluation': e.target.value })}
                            className="w-full px-4 py-3 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:border-transparent transition-all min-h-[150px] leading-relaxed"
                            placeholder="Enter detailed evaluation and feedback for the student..."
                          />
                        </div>
                      </section>
                    </div>

                    {/* Footer */}
                    <div className="flex shrink-0 justify-end gap-3 px-4 py-4 border-t border-gray-200 bg-white sticky bottom-0 z-10">
                      <button
                        type="button"
                        className="rounded-xl bg-white px-6 py-3 text-sm font-semibold text-gray-700 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 transition-all"
                        onClick={onClose}
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={isSaving}
                        className="rounded-xl bg-yellow text-navy px-8 py-3 text-sm font-bold shadow-sm hover:bg-yellow-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-yellow transition-all disabled:opacity-50 flex items-center gap-2"
                        onClick={handleSave}
                      >
                        {isSaving ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Saving...
                          </>
                        ) : (
                          <>
                            <Save className="w-4 h-4" />
                            Save Changes
                          </>
                        )}
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
};

export default StudentEditSheet;
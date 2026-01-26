import { useState, useEffect } from 'react';
import AttendanceManager from '../../components/admin/AttendanceManager';
import { getUsersWithAdminData, UserWithAdminData } from '../../services/api';

export default function Attendance() {
  const [users, setUsers] = useState<UserWithAdminData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const response = await getUsersWithAdminData();
        setUsers(response.students);
      } catch (error) {
        console.error('Failed to fetch users:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchUsers();
  }, []);

  const handleUpdate = async () => {
    // Refresh users after attendance update
    try {
      const response = await getUsersWithAdminData();
      setUsers(response.students);
    } catch (error) {
      console.error('Failed to refresh users:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Attendance Management</h2>
        <p className="text-gray-500 mt-1">Mark and track student attendance for class sessions</p>
      </div>
      <AttendanceManager 
        students={users as any} 
        onUpdate={handleUpdate}
      />
    </div>
  );
}

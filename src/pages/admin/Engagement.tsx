import React, { useState } from 'react';
import AnnouncementManager from '../../components/admin/AnnouncementManager';
import PollManager from '../../components/admin/PollManager';

const Engagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'announcements' | 'polls'>('announcements');

  return (
    <div className="space-y-6">
      <div className="flex gap-4 border-b border-gray-300 pb-1">
        <button
          onClick={() => setActiveTab('announcements')}
          className={`px-4 py-2 text-sm font-semibold transition-colors border-b-2 ${
            activeTab === 'announcements'
              ? 'border-primary text-primary'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          }`}
        >
          Announcements
        </button>
        <button
          onClick={() => setActiveTab('polls')}
          className={`px-4 py-2 text-sm font-semibold transition-colors border-b-2 ${
            activeTab === 'polls'
              ? 'border-primary text-primary'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          }`}
        >
          Polls
        </button>
      </div>

      {activeTab === 'announcements' && <AnnouncementManager />}
      {activeTab === 'polls' && <PollManager />}
    </div>
  );
};

export default Engagement;
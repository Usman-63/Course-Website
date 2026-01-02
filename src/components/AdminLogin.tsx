import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Lock, Loader2 } from 'lucide-react';
import { adminLogin, setAuthToken } from '../services/api';

interface AdminLoginProps {
  onLoginSuccess: () => void;
}

const AdminLogin: React.FC<AdminLoginProps> = ({ onLoginSuccess }) => {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      // Call backend API to verify password
      const result = await adminLogin(password);
      
      if (result.success) {
        // Set token (using password as token for simple auth)
        setAuthToken(password);
        onLoginSuccess();
      } else {
        setError(result.error || 'Invalid password');
        setIsLoading(false);
      }
    } catch (err) {
      setError('Login failed. Please check your connection and try again.');
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-navy flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-navy-light rounded-xl shadow-2xl p-8 w-full max-w-md border-2 border-yellow/30"
      >
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-yellow rounded-full flex items-center justify-center mx-auto mb-4">
            <Lock className="w-8 h-8 text-navy" />
          </div>
          <h2 className="text-3xl font-bold text-yellow mb-2">Admin Login</h2>
          <p className="text-gray-300">Enter password to access admin panel</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="password" className="block text-yellow font-semibold mb-2">
              Password
            </label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 bg-navy border border-navy-light/50 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow focus:border-transparent transition-all"
              placeholder="Enter admin password"
              required
              disabled={isLoading}
            />
          </div>

          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm"
            >
              {error}
            </motion.div>
          )}

          <motion.button
            type="submit"
            disabled={isLoading}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="w-full bg-yellow text-navy font-bold py-4 px-6 rounded-lg hover:bg-yellow/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Logging in...
              </>
            ) : (
              'Login'
            )}
          </motion.button>
        </form>
      </motion.div>
    </div>
  );
};

export default AdminLogin;


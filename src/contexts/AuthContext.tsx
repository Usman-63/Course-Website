import React, { createContext, useContext, useEffect, useState } from 'react';
import { auth, db } from '../services/firebase';
import { onAuthStateChanged, User } from 'firebase/auth';
import { doc, onSnapshot } from 'firebase/firestore';

interface UserProfile {
  role?: string;
  isActive?: boolean;
  [key: string]: any;
}

interface AuthContextType {
  currentUser: User | null;
  userProfile: UserProfile | null;
  loading: boolean;
  user: User | null; // For compatibility
}

const AuthContext = createContext<AuthContextType>({ 
  currentUser: null, 
  userProfile: null,
  loading: true, 
  user: null 
});

export const useAuth = () => useContext(AuthContext);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!auth) {
      console.warn("Firebase Auth is not initialized. Check environment variables.");
      setLoading(false);
      return;
    }

    const unsubscribe = onAuthStateChanged(auth, (user) => {
      setCurrentUser(user);
      if (!user) {
        setUserProfile(null);
        setLoading(false);
      }
    });

    return unsubscribe;
  }, []);

  useEffect(() => {
    let unsubscribeProfile: (() => void) | undefined;

    if (currentUser && db) {
      setLoading(true);
      const userRef = doc(db, 'users', currentUser.uid);
      unsubscribeProfile = onSnapshot(userRef, (doc) => {
        if (doc.exists()) {
          setUserProfile(doc.data() as UserProfile);
        } else {
          setUserProfile(null);
        }
        setLoading(false);
      }, (error) => {
        console.error("Error fetching user profile:", error);
        setLoading(false);
      });
    } else {
      setUserProfile(null);
      // Don't set loading to false here if we want to wait for auth init
      // But since the first effect handles init, we might be fine.
      // Actually, we should check if this is the initial load.
    }

    return () => {
      if (unsubscribeProfile) {
        unsubscribeProfile();
      }
    };
  }, [currentUser]);

  const value = {
    currentUser,
    userProfile,
    user: currentUser, // Alias for compatibility
    loading
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
};

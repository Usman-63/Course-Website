import { useState, Fragment, useEffect } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { Dialog, Transition, Menu } from '@headlessui/react';
import { 
  LayoutDashboard, 
  BookOpen, 
  Users, 
  TableProperties, 
  Megaphone, 
  LogOut, 
  Menu as MenuIcon, 
  X,
  Loader2,
  ArrowLeft
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { clearAuthToken, isAdminLoggedIn, getFirebaseToken } from '../services/api';
import { auth } from '../services/firebase';
import { signOut, signInWithCustomToken } from 'firebase/auth';

const navigation = [
  { name: 'Dashboard', href: '/admin', icon: LayoutDashboard },
  { name: 'Course Content', href: '/admin/content', icon: BookOpen },
  { name: 'Students', href: '/admin/students', icon: Users }, // CRM
  { name: 'Operations', href: '/admin/operations', icon: TableProperties }, // Operations
  { name: 'Engagement', href: '/admin/engagement', icon: Megaphone },
];

export default function AdminLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);
  const location = useLocation();
  const navigate = useNavigate();
  const { userProfile } = useAuth();

  useEffect(() => {
    const initAdmin = async () => {
      if (!isAdminLoggedIn()) {
        navigate('/admin/login');
        return;
      }

      // Ensure Firebase is authenticated
      if (!auth.currentUser) {
        try {
          const firebaseToken = await getFirebaseToken();
          if (firebaseToken) {
            await signInWithCustomToken(auth, firebaseToken);
          } else {
            console.warn("Could not get Firebase token. Service account might be missing.");
            setAuthError('Firebase Admin SDK not configured on backend. Real-time features (Announcements/Polls) may not work.');
          }
        } catch (err: any) {
          console.error("Firebase Auth Error:", err);
          // Don't block access if Firebase fails, but show error
          setAuthError('Failed to authenticate with Firebase: ' + err.message);
        }
      }
      
      setIsLoading(false);
    };
    
    initAdmin();
  }, [navigate]);

  const handleLogout = async () => {
    try {
      clearAuthToken();
      await signOut(auth);
      navigate('/admin/login');
    } catch (error) {
      console.error("Failed to log out", error);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-navy flex items-center justify-center">
        <Loader2 className="w-12 h-12 text-yellow animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 font-sans flex">
      <Transition.Root show={sidebarOpen} as={Fragment}>
        <Dialog as="div" className="relative z-50 lg:hidden" onClose={setSidebarOpen}>
          <Transition.Child
            as={Fragment}
            enter="transition-opacity ease-linear duration-300"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="transition-opacity ease-linear duration-300"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 bg-gray-900/80" />
          </Transition.Child>

          <div className="fixed inset-0 flex">
            <Transition.Child
              as={Fragment}
              enter="transition ease-in-out duration-300 transform"
              enterFrom="-translate-x-full"
              enterTo="translate-x-0"
              leave="transition ease-in-out duration-300 transform"
              leaveFrom="translate-x-0"
              leaveTo="-translate-x-full"
            >
              <Dialog.Panel className="relative mr-16 flex w-full max-w-xs flex-1">
                <div className="flex grow flex-col gap-y-5 overflow-y-auto bg-black px-6 pb-4">
                  <div className="flex h-16 shrink-0 items-center gap-2 mt-4">
                     <div className="w-8 h-8 bg-white rounded-lg flex items-center justify-center">
                        <span className="text-black font-bold text-lg">S</span>
                      </div>
                      <span className="text-white font-display font-bold text-xl">Smansys</span>
                  </div>
                  <nav className="flex flex-1 flex-col">
                    <ul role="list" className="flex flex-1 flex-col gap-y-4">
                      <li>
                        <ul role="list" className="-mx-2 space-y-1">
                          {navigation.map((item) => (
                            <li key={item.name}>
                              <Link
                                to={item.href}
                                className={`
                                  group flex gap-x-3 rounded-r-full p-3 text-sm leading-6 font-medium transition-all
                                  ${location.pathname === item.href
                                    ? 'bg-white text-black translate-x-2 shadow-lg'
                                    : 'text-gray-400 hover:text-white hover:bg-white/10'}
                                `}
                              >
                                <item.icon className={`h-5 w-5 shrink-0 ${location.pathname === item.href ? 'text-black' : 'text-gray-400 group-hover:text-white'}`} aria-hidden="true" />
                                {item.name}
                              </Link>
                            </li>
                          ))}
                        </ul>
                      </li>
                      <li className="mt-auto">
                        <button
                          onClick={handleLogout}
                          className="group -mx-2 flex gap-x-3 rounded-md p-3 text-sm font-semibold leading-6 text-gray-400 hover:bg-white/10 hover:text-white w-full bg-white text-black"
                        >
                          <span className="flex-1 text-left font-bold text-black">Log Out</span>
                          <LogOut className="h-5 w-5 shrink-0 text-black" aria-hidden="true" />
                        </button>
                      </li>
                    </ul>
                  </nav>
                </div>
                <div className="absolute left-full top-0 flex w-16 justify-center pt-5">
                  <button type="button" className="-m-2.5 p-2.5" onClick={() => setSidebarOpen(false)}>
                    <span className="sr-only">Close sidebar</span>
                    <X className="h-6 w-6 text-white" aria-hidden="true" />
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </Dialog>
      </Transition.Root>

      {/* Static sidebar for desktop */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:z-50 lg:flex lg:w-72 lg:flex-col">
        <div className="flex grow flex-col gap-y-5 overflow-y-auto bg-black px-6 pb-4 shadow-xl">
          <div className="flex h-16 shrink-0 items-center gap-3 mt-6 mb-4">
            <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center shadow-lg">
              <span className="text-black font-bold text-xl">S</span>
            </div>
            <span className="text-white font-display font-bold text-2xl tracking-tight">Smansys</span>
          </div>
          <nav className="flex flex-1 flex-col">
            <ul role="list" className="flex flex-1 flex-col gap-y-7">
              <li>
                <ul role="list" className="-mx-2 space-y-3">
                  {navigation.map((item) => (
                    <li key={item.name}>
                      <Link
                        to={item.href}
                        className={`
                          group flex gap-x-3 rounded-r-full mr-4 p-3 text-sm leading-6 font-medium transition-all duration-200
                          ${location.pathname === item.href
                            ? 'bg-gray-100 text-black shadow-lg translate-x-2'
                            : 'text-gray-400 hover:text-white hover:bg-white/10'}
                        `}
                      >
                        <item.icon className={`h-5 w-5 shrink-0 ${location.pathname === item.href ? 'text-black' : 'text-gray-400 group-hover:text-white'}`} aria-hidden="true" />
                        {item.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </li>
              
              <li className="mt-auto mb-4">
                <button
                  onClick={handleLogout}
                  className="group flex items-center gap-x-3 rounded-xl px-4 py-3 text-sm font-bold leading-6 text-black bg-white hover:bg-gray-200 w-full shadow-lg transition-all"
                >
                  <span className="flex-1 text-left">Log Out</span>
                  <LogOut className="h-5 w-5 shrink-0" aria-hidden="true" />
                </button>
              </li>
            </ul>
          </nav>
        </div>
      </div>

      <div className="lg:pl-72 flex-1 flex flex-col min-h-screen bg-gray-100">
        {/* Header */}
        <div className="sticky top-0 z-40 flex h-20 shrink-0 items-center gap-x-4 bg-gray-100 px-4 sm:gap-x-6 sm:px-6 lg:px-8">
          <button type="button" className="-m-2.5 p-2.5 text-gray-700 lg:hidden" onClick={() => setSidebarOpen(true)}>
            <span className="sr-only">Open sidebar</span>
            <MenuIcon className="h-6 w-6" aria-hidden="true" />
          </button>

          <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6 items-center">
            {/* Back Button */}
            <div className="flex flex-1 items-center gap-4">
                <button onClick={() => navigate(-1)} className="p-2 bg-white rounded-full shadow-sm border border-gray-100 text-gray-500 hover:text-gray-700 hover:bg-gray-50 transition-all">
                  <ArrowLeft className="w-5 h-5" />
                </button>
            </div>

            {/* Right Icons */}
            <div className="flex items-center gap-x-3 lg:gap-x-4">
              <div className="hidden lg:block lg:h-8 lg:w-px lg:bg-gray-200" aria-hidden="true" />
              
              <Menu as="div" className="relative">
                <Menu.Button className="-m-1.5 flex items-center p-1.5">
                  <span className="sr-only">Open user menu</span>
                  <div className="h-10 w-10 rounded-full bg-gray-200 overflow-hidden border-2 border-white shadow-sm">
                     <img src={`https://ui-avatars.com/api/?name=${userProfile?.name || 'Admin'}&background=random`} alt="" className="h-full w-full object-cover" />
                  </div>
                </Menu.Button>
                <Transition
                  as={Fragment}
                  enter="transition ease-out duration-100"
                  enterFrom="transform opacity-0 scale-95"
                  enterTo="transform opacity-100 scale-100"
                  leave="transition ease-in duration-75"
                  leaveFrom="transform opacity-100 scale-100"
                  leaveTo="transform opacity-0 scale-95"
                >
                  <Menu.Items className="absolute right-0 z-10 mt-2.5 w-32 origin-top-right rounded-md bg-white py-2 shadow-lg ring-1 ring-gray-900/5 focus:outline-none">
                    <Menu.Item>
                      {({ active }) => (
                        <button
                          onClick={handleLogout}
                          className={`
                            ${active ? 'bg-gray-50' : ''}
                            block px-3 py-1 text-sm leading-6 text-gray-900 w-full text-left
                          `}
                        >
                          Sign out
                        </button>
                      )}
                    </Menu.Item>
                  </Menu.Items>
                </Transition>
              </Menu>
            </div>
          </div>
        </div>

        <main className="py-6 px-4 sm:px-6 lg:px-8 flex-1">
          {authError && (
            <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative" role="alert">
              <strong className="font-bold">Error: </strong>
              <span className="block sm:inline">{authError}</span>
            </div>
          )}
          <Outlet />
        </main>
      </div>
    </div>
  );
}
import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  HomeIcon,
  BookOpenIcon,
  MegaphoneIcon,
  PresentationChartBarIcon,
  MicrophoneIcon,
  PencilIcon,
  PhotoIcon,
  SpeakerWaveIcon,
  UserCircleIcon,
  CommandLineIcon,
  BuildingOfficeIcon,
  ShieldCheckIcon,
  PuzzlePieceIcon,
  CpuChipIcon,
} from '@heroicons/react/24/outline';

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Story Generator', href: '/story-generator', icon: BookOpenIcon },
  { name: 'Social Campaign', href: '/social-campaign', icon: MegaphoneIcon },
  { name: 'Presentation Builder', href: '/presentation-builder', icon: PresentationChartBarIcon },
  { name: 'Podcast Generator', href: '/podcast-generator', icon: MicrophoneIcon },
  { name: 'Writing Assistant', href: '/writing-assistant', icon: PencilIcon },
  { name: 'Media Generator', href: '/media-generator', icon: PhotoIcon },
  { name: 'Voice Chat', href: '/voice-chat', icon: SpeakerWaveIcon },
  { name: 'Avatar Companion', href: '/avatar-companion', icon: UserCircleIcon },
  { name: 'Game Builder', href: '/game-builder', icon: CommandLineIcon },
];

const platformNavigation = [
  { name: 'Organizations', href: '/organizations', icon: BuildingOfficeIcon },
  { name: 'Marketplace', href: '/marketplace', icon: PuzzlePieceIcon },
  { name: 'Security', href: '/security', icon: ShieldCheckIcon },
  { name: 'Telemetry', href: '/telemetry', icon: CpuChipIcon },
];

const Sidebar: React.FC = () => {
  return (
    <div className="w-64 h-screen bg-white shadow-sm border-r border-gray-200 overflow-y-auto">
      <nav className="mt-8 px-4">
        <ul className="space-y-2">
          {navigation.map((item) => (
            <li key={item.name}>
              <NavLink
                to={item.href}
                end={item.href === '/'}
                className={({ isActive }) =>
                  `flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
                    isActive
                      ? 'bg-primary-50 text-primary-700 border-r-2 border-primary-600'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  }`
                }
              >
                <item.icon className="mr-3 h-5 w-5" />
                {item.name}
              </NavLink>
            </li>
          ))}
        </ul>

        <div className="mt-6 pt-6 border-t border-gray-100">
          <p className="px-4 mb-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
            Platform
          </p>
          <ul className="space-y-2">
            {platformNavigation.map((item) => (
              <li key={item.name}>
                <NavLink
                  to={item.href}
                  className={({ isActive }) =>
                    `flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
                      isActive
                        ? 'bg-slate-50 text-slate-700 border-r-2 border-slate-600'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }`
                  }
                >
                  <item.icon className="mr-3 h-5 w-5" />
                  {item.name}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      </nav>
    </div>
  );
};

export default Sidebar;